#!/usr/bin/env python3
"""
Sync supplementary dictionary files from the EDRDG archive via rsync
(ftp.edrdg.org::nihongo/) into data/raw/.

Requires the `rsync` binary (e.g. `apt-get install -y rsync` in the image).
Chosen over FTP because these files regenerate daily upstream and rsync
does delta transfer — only the changed bytes move on repeat runs. The
local .gz cache is therefore kept between runs (never deleted) so rsync
has something to diff against; there's no "skip if already downloaded
today" logic anymore, since an up-to-date file just syncs near-instantly.

Each synced file gets a <name>.xml.meta.json sidecar recording the
upstream generation date (parsed from the file header — the true version
marker, since sync time can lag it if the file hasn't changed), sync
timestamp, and sha256.

Usage:
    python scripts/download_edrdg.py
"""

import gzip
import hashlib
import json
import logging
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import RAW_DIR  # noqa: E402

log = logging.getLogger(__name__)

RSYNC_HOST = "ftp.edrdg.org"
RSYNC_MODULE = "nihongo"
MAX_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds, multiplied by attempt number


class RemoteSpec(NamedTuple):
    remote: str  # filename in the rsync module
    out_name: str  # local filename for the decompressed content
    closing: bytes  # expected end-of-content marker (integrity check)


WANTED: list[RemoteSpec] = [
    RemoteSpec("JMdict_e_NG_examp.gz", "JMdict_e_NG_examp.xml", b"</JMdict>"),
    RemoteSpec("kanjidic2.xml.gz", "kanjidic2.xml", b"</kanjidic2>"),
]

_GEN_DATE_RE = re.compile(r'created[=:]\s*"?(\d{4}-\d{2}-\d{2})')
_HEAD_BYTES = 512 * 1024  # header window searched for the generation date
_TAIL_BYTES = 4096        # enough to hold the closing tag plus trailing whitespace


def check_rsync_available() -> None:
    if shutil.which("rsync") is None:
        raise RuntimeError(
            "rsync not found on PATH — install it (e.g. `apt-get install -y rsync`). "
            "EDRDG recommends rsync for these files since they regenerate daily."
        )


def rsync_fetch(spec: RemoteSpec, dest: Path) -> None:
    """Sync one file into `dest`, retrying transient failures with backoff.
    `dest` is never deleted between runs — rsync needs it to diff against."""
    source = f"{RSYNC_HOST}::{RSYNC_MODULE}/{spec.remote}"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        log.info("  rsync %s → %s (attempt %d/%d)", source, dest, attempt, MAX_ATTEMPTS)
        try:
            result = subprocess.run(
                # --contimeout bounds the daemon connect, --timeout bounds I/O
                # stalls — without them a hung connection blocks forever.
                ["rsync", "-az", "--stats", "--contimeout=30", "--timeout=300",
                 source, str(dest)],
                capture_output=True,
                text=True,
            )
            returncode, err = result.returncode, result.stderr.strip()
        except OSError as exc:  # e.g. rsync binary vanished mid-run
            result = None
            returncode, err = -1, str(exc)

        if returncode == 0:
            log.debug("  rsync stats:\n%s", result.stdout.strip())
            return
        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(
                f"rsync failed after {MAX_ATTEMPTS} attempts (exit {returncode}): {err}"
            )
        delay = RETRY_DELAY * attempt
        log.warning(
            "  rsync attempt %d failed (exit %d); retrying in %ds\n%s",
            attempt, returncode, delay, err,
        )
        time.sleep(delay)


def generation_date(head: bytes) -> str | None:
    """Upstream export date stamped in the file header — the true version
    marker for reproducibility, distinct from when we happened to sync."""
    m = _GEN_DATE_RE.search(head.decode("utf-8", errors="replace"))
    return m.group(1) if m else None


def _meta_path(out_path: Path) -> Path:
    return out_path.with_suffix(out_path.suffix + ".meta.json")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat(timespec="seconds")


def write_meta(out_path: Path, spec: RemoteSpec, head: bytes, sha256: str, gz_mtime: float) -> None:
    gen_date = generation_date(head)
    if gen_date is None:
        log.warning("  %s: no generation date found in header — check _GEN_DATE_RE", spec.remote)
    meta = {
        "remote_file": spec.remote,
        "synced_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "remote_mtime": _iso(gz_mtime),
        "generation_date_from_header": gen_date,
        "sha256": sha256,
    }
    _meta_path(out_path).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _unchanged(out_path: Path, gz_mtime: float) -> bool:
    """True when the .gz rsync left behind is the one already decompressed —
    rsync -a preserves the upstream mtime, and the sidecar recorded it."""
    meta_path = _meta_path(out_path)
    if not (out_path.exists() and meta_path.exists()):
        return False
    try:
        return json.loads(meta_path.read_text(encoding="utf-8")).get("remote_mtime") == _iso(gz_mtime)
    except (OSError, ValueError):
        return False


def _decompress(gz_path: Path, out_path: Path, closing: bytes) -> tuple[bytes, str]:
    """Stream .gz → out_path in 1 MB blocks, hashing as it goes and keeping
    only the head (for the generation date) and the tail (integrity check) —
    never the whole ~70 MB file, let alone a second `rstrip()` copy of it.
    Writes to a temp file so a failed check can't leave a truncated XML that
    build_chunks would then choke on."""
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    digest, head, tail = hashlib.sha256(), b"", b""
    with gzip.open(gz_path, "rb") as src, tmp.open("wb") as dst:
        while block := src.read(1 << 20):
            digest.update(block)
            dst.write(block)
            if len(head) < _HEAD_BYTES:
                head += block[: _HEAD_BYTES - len(head)]
            tail = (tail + block)[-_TAIL_BYTES:]
    if not tail.rstrip().endswith(closing):
        tmp.unlink(missing_ok=True)
        raise ValueError(
            f"{gz_path.name}: decompressed content doesn't end with {closing!r} — "
            "truncated or corrupt transfer"
        )
    tmp.replace(out_path)
    return head, digest.hexdigest()


def sync_one(spec: RemoteSpec) -> bool:
    """Sync one file; True when upstream moved and a fresh XML was written."""
    gz_path = RAW_DIR / spec.remote
    out_path = RAW_DIR / spec.out_name

    rsync_fetch(spec, gz_path)
    gz_mtime = gz_path.stat().st_mtime
    if _unchanged(out_path, gz_mtime):
        log.info("  %s unchanged upstream — keeping %s", spec.remote, out_path.name)
        return False

    head, sha256 = _decompress(gz_path, out_path, spec.closing)
    write_meta(out_path, spec, head, sha256, gz_mtime)
    log.info("  Saved → %s (%.1f MB)", out_path, out_path.stat().st_size / (1024 * 1024))
    return True


def main() -> bool:
    """Sync all WANTED files; returns True when at least one XML changed —
    startup.py's refresh path uses that to skip an unnecessary rebuild."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    check_rsync_available()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Two independent remote files — sync them concurrently. Materialize the
    # results before any() so a short-circuit can't swallow a raised sync.
    with ThreadPoolExecutor(max_workers=len(WANTED)) as pool:
        changed = any(list(pool.map(sync_one, WANTED)))

    log.info("Done. Files in %s:", RAW_DIR)
    for f in sorted(RAW_DIR.glob("*.xml")):
        log.info("  %s  (%.1f MB)", f.name, f.stat().st_size / (1024 * 1024))
    return changed


if __name__ == "__main__":
    main()
