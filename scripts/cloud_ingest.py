#!/usr/bin/env python3
"""Copy a populated Qdrant collection to a remote cluster via snapshot upload.

Much faster than scripts/ingest.py for a remote target: the source Qdrant
already holds the fully-embedded collection, so this is snapshot → download →
upload — a file transfer (~1-2 GB), not an hour of re-embedding. The upload
endpoint overwrites the target collection in place (or creates it).

Defaults: source = local docker Qdrant (http://localhost:6333), target =
QDRANT_URL/QDRANT_API_KEY from .env (e.g. Qdrant Cloud).

Usage:
    uv run python scripts/cloud_ingest.py               # local → QDRANT_URL
    uv run python scripts/cloud_ingest.py --force       # overwrite non-empty target
    uv run python scripts/cloud_ingest.py --keep-snapshot   # keep server-side + temp file
"""

import argparse
import hashlib
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx
from qdrant_client import QdrantClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import COLLECTION, QDRANT_API_KEY, QDRANT_URL  # noqa: E402

log = logging.getLogger(__name__)

# Source must NOT fall back to QDRANT_URL — that's the target now that .env
# points at the cloud. Default is the local compose Qdrant. (.env is already
# loaded by app.config on import.)
SOURCE_URL = os.getenv("SOURCE_QDRANT_URL", "http://localhost:6333")
SOURCE_API_KEY = os.getenv("SOURCE_QDRANT_API_KEY") or None

# 10-min stall ceiling per socket read/write — unlimited would hang forever
# on a connection that stalls without closing; a progressing 1–2 GB transfer
# never trips a per-op timeout.
_TIMEOUT = httpx.Timeout(connect=30, read=600, write=600, pool=None)
MAX_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds, multiplied by attempt number


def _auth(api_key: str | None) -> dict[str, str]:
    return {"api-key": api_key} if api_key else {}


def _verify_snapshot(path: Path, expected_size: int | None, expected_sha256: str | None) -> None:
    """Integrity check on the downloaded file — the source reports a size and
    sha256 for every snapshot it creates, so verify before uploading rather
    than replacing the target collection with a truncated transfer."""
    if expected_size is not None and path.stat().st_size != expected_size:
        raise ValueError(f"snapshot truncated: {path.stat().st_size:,} B != {expected_size:,} B")
    if expected_sha256:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                digest.update(block)
        if digest.hexdigest() != expected_sha256:
            raise ValueError(f"snapshot sha256 {digest.hexdigest()} != reported {expected_sha256}")


def download_snapshot(url: str, api_key: str | None, collection: str, name: str,
                      *, expected_size: int | None = None,
                      expected_sha256: str | None = None) -> Path:
    """Stream the snapshot file off the source server to a temp file, retrying
    the whole transfer — for a 1–2 GB snapshot a mid-download blip is the
    costliest place in the pipeline to restart."""
    tmp = Path(tempfile.mkstemp(suffix=".snapshot")[1])
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with httpx.stream("GET", f"{url}/collections/{collection}/snapshots/{name}",
                                  headers=_auth(api_key), timeout=_TIMEOUT) as r:
                    r.raise_for_status()
                    done = 0
                    with tmp.open("wb") as f:
                        for chunk in r.iter_bytes(chunk_size=8 * 1024 * 1024):
                            f.write(chunk)
                            done += len(chunk)
                            print(f"\r    {done / 2**20:.0f} MB downloaded", end="", flush=True)
                print()
                _verify_snapshot(tmp, expected_size, expected_sha256)
                return tmp
            except Exception as exc:
                if attempt == MAX_ATTEMPTS:
                    raise
                delay = RETRY_DELAY * attempt
                log.warning("  download attempt %d failed (%s); retrying in %ds",
                            attempt, exc, delay)
                time.sleep(delay)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp  # unreachable — loop returns or raises


def upload_snapshot(url: str, api_key: str | None, collection: str, path: Path) -> None:
    """POST the snapshot to the target's snapshots/upload endpoint — replaces
    the collection's data wholesale (and creates it if missing), so a retry
    after a partial upload is the recovery path, not a hazard."""
    size = path.stat().st_size
    log.info("  Uploading %.0f MB snapshot → %s (this replaces the collection) …",
             size / 2**20, url)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with path.open("rb") as f:
                resp = httpx.post(
                    f"{url}/collections/{collection}/snapshots/upload",
                    params={"wait": "true"},
                    headers=_auth(api_key),
                    files={"snapshot": (path.name, f)},
                    timeout=_TIMEOUT,
                )
            resp.raise_for_status()
            if resp.json().get("status") != "ok":
                raise RuntimeError(f"snapshot upload rejected: {resp.text[:300]}")
            return
        except Exception as exc:
            if attempt == MAX_ATTEMPTS:
                raise
            delay = RETRY_DELAY * attempt
            log.warning("  upload attempt %d failed (%s); retrying in %ds",
                        attempt, exc, delay)
            time.sleep(delay)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source-url", default=SOURCE_URL, help="source Qdrant (default: %(default)s)")
    p.add_argument("--source-api-key", default=SOURCE_API_KEY)
    p.add_argument("--target-url", default=QDRANT_URL, help="target Qdrant (default: QDRANT_URL from .env)")
    p.add_argument("--target-api-key", default=QDRANT_API_KEY)
    p.add_argument("--collection", default=COLLECTION)
    p.add_argument("--force", action="store_true", help="overwrite a non-empty target collection")
    p.add_argument("--keep-snapshot", action="store_true", help="don't delete the source snapshot + temp file")
    args = p.parse_args()

    if args.source_url.rstrip("/") == args.target_url.rstrip("/"):
        sys.exit("source and target are the same cluster — nothing to copy")

    source = QdrantClient(url=args.source_url, api_key=args.source_api_key, timeout=60)
    target = QdrantClient(url=args.target_url, api_key=args.target_api_key, timeout=60)

    if not source.collection_exists(args.collection):
        sys.exit(f"source has no '{args.collection}' — ingest locally first")
    src_count = source.count(args.collection).count
    log.info("Source %s: %s points in '%s'", args.source_url, f"{src_count:,}", args.collection)

    if target.collection_exists(args.collection) and (n := target.count(args.collection).count) > 0:
        if not args.force:
            sys.exit(f"target '{args.collection}' already holds {n:,} points — pass --force to overwrite")
        log.warning("Target '%s' holds %s points — will be replaced", args.collection, f"{n:,}")

    log.info("Creating snapshot on source …")
    snap = source.create_snapshot(args.collection, wait=True)
    assert snap is not None

    tmp = None
    try:
        log.info("Downloading snapshot %s …", snap.name)
        tmp = download_snapshot(args.source_url, args.source_api_key, args.collection, snap.name,
                                expected_size=getattr(snap, "size", None),
                                expected_sha256=getattr(snap, "checksum", None))
        upload_snapshot(args.target_url, args.target_api_key, args.collection, tmp)
    finally:
        if tmp and not args.keep_snapshot:
            tmp.unlink(missing_ok=True)
        if not args.keep_snapshot:
            source.delete_snapshot(args.collection, snap.name, wait=True)

    dst_count = target.count(args.collection).count
    status = target.get_collection(args.collection).status
    log.info("Done — target now holds %s points (source: %s), status=%s",
             f"{dst_count:,}", f"{src_count:,}", status)
    if dst_count != src_count:
        sys.exit(f"point-count mismatch: {dst_count:,} != {src_count:,}")


if __name__ == "__main__":
    main()
