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


def generation_date(content: bytes) -> str | None:
    """Upstream export date stamped in the file header — the true version
    marker for reproducibility, distinct from when we happened to sync."""
    head = content[: 512 * 1024].decode("utf-8", errors="replace")
    m = _GEN_DATE_RE.search(head)
    return m.group(1) if m else None


def write_meta(out_path: Path, spec: RemoteSpec, content: bytes, gz_mtime: float) -> None:
    gen_date = generation_date(content)
    if gen_date is None:
        log.warning("  %s: no generation date found in header — check _GEN_DATE_RE", spec.remote)
    meta = {
        "remote_file": spec.remote,
        "synced_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "remote_mtime": datetime.fromtimestamp(gz_mtime, tz=UTC).isoformat(timespec="seconds"),
        "generation_date_from_header": gen_date,
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    meta_path = out_path.with_suffix(out_path.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def sync_one(spec: RemoteSpec) -> None:
    gz_path = RAW_DIR / spec.remote
    out_path = RAW_DIR / spec.out_name

    rsync_fetch(spec, gz_path)
    content = gzip.decompress(gz_path.read_bytes())

    if not content.rstrip().endswith(spec.closing):
        raise ValueError(
            f"{spec.remote}: decompressed content doesn't end with {spec.closing!r} — "
            "truncated or corrupt transfer"
        )

    out_path.write_bytes(content)
    write_meta(out_path, spec, content, gz_path.stat().st_mtime)
    log.info("  Saved → %s (%.1f MB)", out_path, out_path.stat().st_size / (1024 * 1024))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    check_rsync_available()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for spec in WANTED:
        sync_one(spec)

    log.info("Done. Files in %s:", RAW_DIR)
    for f in sorted(RAW_DIR.glob("*.xml")):
        log.info("  %s  (%.1f MB)", f.name, f.stat().st_size / (1024 * 1024))


if __name__ == "__main__":
    main()
