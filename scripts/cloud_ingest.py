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
import logging
import os
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv, find_dotenv
from qdrant_client import QdrantClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import COLLECTION, QDRANT_API_KEY, QDRANT_URL  # noqa: E402

load_dotenv(find_dotenv(usecwd=True))

log = logging.getLogger(__name__)

# Source must NOT fall back to QDRANT_URL — that's the target now that .env
# points at the cloud. Default is the local compose Qdrant.
SOURCE_URL = os.getenv("SOURCE_QDRANT_URL", "http://localhost:6333")
SOURCE_API_KEY = os.getenv("SOURCE_QDRANT_API_KEY") or None

_TIMEOUT = httpx.Timeout(connect=30, read=None, write=None, pool=None)


def _auth(api_key: str | None) -> dict[str, str]:
    return {"api-key": api_key} if api_key else {}


def download_snapshot(url: str, api_key: str | None, collection: str, name: str) -> Path:
    """Stream the snapshot file off the source server to a temp file."""
    tmp = Path(tempfile.mkstemp(suffix=".snapshot")[1])
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
    return tmp


def upload_snapshot(url: str, api_key: str | None, collection: str, path: Path) -> None:
    """POST the snapshot to the target's snapshots/upload endpoint — replaces
    the collection's data wholesale (and creates it if missing)."""
    size = path.stat().st_size
    log.info("  Uploading %.0f MB snapshot → %s (this replaces the collection) …",
             size / 2**20, url)
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
        tmp = download_snapshot(args.source_url, args.source_api_key, args.collection, snap.name)
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
