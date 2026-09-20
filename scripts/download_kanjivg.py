#!/usr/bin/env python3
"""
Download KanjiVG stroke-order SVGs (GitHub releases) into data/kanjivg/.

Picks the newest stable (non-draft, non-prerelease) release — tag rYYYYMMDD
is the version marker; a re-run on the same tag AND filter scope skips.
Extracts only standard kanji/<hex>.svg files (the -Kaisho/-VtLst/etc. variants
are skipped — they're alternate glyph styles and stroke-order variants of the
same codepoint, not extra kanji, limited to KANJIDIC2 codepoints when data/raw/kanjidic2.xml
exists. Writes kanjivg.meta.json with release tag, publish time, sha256,
filter scope and SVG count — the same provenance-sidecar convention as
download_edrdg.py.

Usage:
    python scripts/download_kanjivg.py
"""

import hashlib
import io
import json
import logging
import os
import re
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import httpx
from dotenv import dotenv_values, find_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import KANJIVG_DIR, RAW_DIR  # noqa: E402

_ENV = dotenv_values(find_dotenv(usecwd=True))  # project-root .env as a dict

log = logging.getLogger(__name__)

RELEASES_API = "https://api.github.com/repos/KanjiVG/kanjivg/releases"
ASSET_SUFFIX = "-all.zip"  # -main is a subset, -stripped drops stroke metadata
MAX_ATTEMPTS, RETRY_DELAY = 3, 5  # seconds × attempt
META_PATH = KANJIVG_DIR / "kanjivg.meta.json"
_HEX_SVG_RE = re.compile(r"^kanji/([0-9a-f]{5,6})\.svg$")


class Release(NamedTuple):
    tag: str          # e.g. r20250816 — the version marker
    published_at: str
    asset_name: str
    url: str


def _github_token() -> str | None:
    """Process env wins (export GITHUB_TOKEN=...), .env file is the fallback —
    dotenv_values() only reads the file, so an exported var would otherwise
    be silently ignored."""
    return os.environ.get("GITHUB_TOKEN") or _ENV.get("GITHUB_TOKEN")


def github_headers() -> dict[str, str]:
    """Authenticate with GITHUB_TOKEN when available — unauthenticated API
    calls are limited to 60 req/hr per IP."""
    headers = {"Accept": "application/vnd.github+json"}
    if token := _github_token():
        headers["Authorization"] = f"Bearer {token}"
    return headers


def latest_release() -> Release:
    """Newest stable release carrying an -all.zip asset. The /releases list is
    ordered newest-first; drafts and prereleases are skipped explicitly rather
    than relying on the /latest shortcut."""
    log.info("Fetching KanjiVG releases from GitHub…")
    resp = httpx.get(RELEASES_API, headers=github_headers(), params={"per_page": 20}, timeout=30)
    resp.raise_for_status()
    for rel in resp.json():
        if rel["draft"] or rel["prerelease"]:
            log.info("  Skipping %s (draft=%s, prerelease=%s)",
                     rel["tag_name"], rel["draft"], rel["prerelease"])
            continue
        for a in rel["assets"]:
            if a["name"].endswith(ASSET_SUFFIX):
                log.info("  Release %s (%s) → %s", rel["tag_name"], rel["published_at"], a["name"])
                return Release(rel["tag_name"], rel["published_at"], a["name"],
                               a["browser_download_url"])
        log.warning("  %s has no %s asset — trying next release", rel["tag_name"], ASSET_SUFFIX)
    raise RuntimeError(f"no stable release with a {ASSET_SUFFIX} asset")


def load_wanted_codepoints() -> set[str] | None:
    """Codepoints to keep, from KANJIDIC2 when present; None means 'all
    standard SVGs' (no filtering)."""
    kd = RAW_DIR / "kanjidic2.xml"
    if not kd.exists():
        log.info("  kanjidic2.xml not found — extracting all standard SVGs")
        return None
    import xml.etree.ElementTree as ET

    return {
        f"{ord(literal):05x}"
        for _ev, char in ET.iterparse(kd, events=("end",))
        if char.tag == "character" and (literal := char.findtext("literal"))
    }


def already_current(tag: str, wanted: set[str] | None) -> bool:
    """Skip when the meta sidecar records this tag, the SAME filter scope
    (all vs. KANJIDIC2-limited), and SVGs are on disk. Filter scope must
    match too, or a run that adds/removes kanjidic2.xml after the first
    download would wrongly skip and leave stale/incomplete SVGs behind."""
    if not META_PATH.exists():
        return False
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    count = len(list(KANJIVG_DIR.glob("*.svg")))
    same_tag = meta.get("release_tag") == tag
    same_scope = meta.get("filtered") == (wanted is not None)
    if same_tag and same_scope and count:
        log.info("  Skipping KanjiVG (already at %s, %s SVGs)", tag, f"{count:,}")
        return True
    return False


def download_zip(url: str) -> bytes:
    """Download with retry/backoff and a progress line."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            log.info("  Downloading (attempt %d/%d)", attempt, MAX_ATTEMPTS)
            parts, done = [], 0
            with httpx.stream("GET", url, headers=github_headers(), follow_redirects=True, timeout=300) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                for chunk in r.iter_bytes(chunk_size=1024 * 1024):
                    parts.append(chunk)
                    done += len(chunk)
                    total_mb = f" / {total / 2**20:.1f}" if total else ""
                    print(f"\r    {done / 2**20:.1f}{total_mb} MB", end="", flush=True)
            print()
            return b"".join(parts)
        except (httpx.HTTPError, OSError) as exc:
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"download failed after {MAX_ATTEMPTS} attempts: {exc}") from exc
            log.warning("  attempt %d failed (%s); retrying in %ds", attempt, exc, RETRY_DELAY * attempt)
            time.sleep(RETRY_DELAY * attempt)
    raise AssertionError("unreachable")


def extract_svgs(blob: bytes, wanted: set[str] | None) -> int:
    """Verify the zip and extract standard per-codepoint SVGs. Clears any
    previously extracted SVGs first, so a narrowed or widened filter (or a
    changed release) never leaves stale files mixed in with the new set."""
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        if bad := zf.testzip():  # integrity check — same role as `closing` in EDRDG
            raise ValueError(f"corrupt zip — first bad member: {bad}")
        KANJIVG_DIR.mkdir(parents=True, exist_ok=True)
        for stale in KANJIVG_DIR.glob("*.svg"):
            stale.unlink()
        saved = 0
        for m in zf.infolist():
            if (mm := _HEX_SVG_RE.match(m.filename)) and (wanted is None or mm[1] in wanted):
                (KANJIVG_DIR / Path(m.filename).name).write_bytes(zf.read(m))
                saved += 1
    if not saved:
        raise RuntimeError("extracted 0 SVGs — check the member-name filter")
    return saved


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if not _github_token():
        log.warning("  No GITHUB_TOKEN set — unauthenticated GitHub API calls are limited to 60/hr")

    rel = latest_release()
    wanted = load_wanted_codepoints()
    if already_current(rel.tag, wanted):
        return

    blob = download_zip(rel.url)
    saved = extract_svgs(blob, wanted)

    # Write atomically so a crash mid-write can't leave a corrupt sidecar
    # that the next run's json.loads() would choke on.
    tmp = META_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({
        "remote_file": rel.asset_name,
        "release_tag": rel.tag,
        "published_at": rel.published_at,
        "synced_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "svg_count": saved,
        "filtered": wanted is not None,
        "licence": "CC BY-SA 3.0 — https://kanjivg.tagaini.net/",
    }, indent=2) + "\n", encoding="utf-8")
    tmp.replace(META_PATH)
    log.info("  Saved %s SVGs → %s", f"{saved:,}", KANJIVG_DIR)


if __name__ == "__main__":
    main()
