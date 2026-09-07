#!/usr/bin/env python3
"""
Download JMdict (with examples) and KANJIDIC2 JSON from the jmdict-simplified
GitHub releases into data/raw/.

Usage:
    python scripts/download_data.py

The script always fetches the *latest* release via the GitHub API, so the data
stays up-to-date without hard-coded version strings.
Files downloaded:
    data/raw/jmdict.json     – JMdict English + example sentences
    data/raw/kanjidic2.json  – KANJIDIC2 English
    data/kanjivg/*.svg       – KanjiVG stroke-order diagrams (offline)
"""

import io
import json
import sys
import tarfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import KANJIVG_DIR, RAW_DIR  # noqa: E402

GITHUB_API = "https://api.github.com/repos/scriptin/jmdict-simplified/releases/latest"
KANJIVG_TARBALL = "https://github.com/KanjiVG/kanjivg/archive/refs/heads/master.tar.gz"

# Prefix → canonical output filename
WANTED: dict[str, str] = {
    "jmdict-examples-eng": "jmdict.json",
    "kanjidic2-en": "kanjidic2.json",
}


def fetch_release_assets() -> list[dict]:
    print("Fetching latest jmdict-simplified release info from GitHub…")
    resp = httpx.get(
        GITHUB_API,
        headers={"Accept": "application/vnd.github+json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print(f"  Release tag: {data['tag_name']}")
    return data["assets"]


def download_and_extract(url: str, label: str) -> bytes:
    """Stream-download a .tgz file and return the raw bytes of the JSON inside."""
    print(f"  Downloading {label} …", flush=True)
    chunks_downloaded = 0
    parts: list[bytes] = []
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        for chunk in r.iter_bytes(chunk_size=1024 * 1024):
            parts.append(chunk)
            chunks_downloaded += len(chunk)
            if total:
                pct = chunks_downloaded * 100 // total
                mb = chunks_downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                print(f"\r    {pct:3d}%  {mb:.1f} / {total_mb:.1f} MB", end="", flush=True)
    print()  # newline after progress bar

    content = b"".join(parts)
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tf:
        for member in tf.getmembers():
            if member.name.endswith(".json"):
                f = tf.extractfile(member)
                if f:
                    return f.read()
    raise RuntimeError(f"No JSON file found inside archive from {url}")


def wanted_kanji_codepoints() -> set[str] | None:
    """Return the set of codepoint-hex filenames needed for KANJIDIC2 kanji."""
    kanjidic_path = RAW_DIR / "kanjidic2.json"
    if not kanjidic_path.exists():
        return None
    with open(kanjidic_path, encoding="utf-8") as f:
        data = json.load(f)
    return {f"{ord(ch['literal']):05x}" for ch in data.get("characters", [])}


def download_kanjivg() -> None:
    """Download the KanjiVG repo tarball and extract stroke-order SVGs locally."""
    if KANJIVG_DIR.exists() and any(KANJIVG_DIR.glob("*.svg")):
        count = len(list(KANJIVG_DIR.glob("*.svg")))
        print(f"  Skipping KanjiVG (already exists, {count:,} SVGs)")
        return

    wanted = wanted_kanji_codepoints()
    KANJIVG_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading KanjiVG stroke-order diagrams…", flush=True)
    parts: list[bytes] = []
    downloaded = 0
    with httpx.stream("GET", KANJIVG_TARBALL, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        for chunk in r.iter_bytes(chunk_size=1024 * 1024):
            parts.append(chunk)
            downloaded += len(chunk)
            print(f"\r    {downloaded / (1024 * 1024):.1f} MB", end="", flush=True)
    print()

    saved = 0
    with tarfile.open(fileobj=io.BytesIO(b"".join(parts)), mode="r:gz") as tf:
        for member in tf:
            name = Path(member.name).name
            if "/kanji/" not in member.name or not name.endswith(".svg"):
                continue
            if wanted is not None and name[:-4] not in wanted:
                continue
            f = tf.extractfile(member)
            if f:
                (KANJIVG_DIR / name).write_bytes(f.read())
                saved += 1
    print(f"  Saved {saved:,} stroke-order SVGs → {KANJIVG_DIR}")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    assets = fetch_release_assets()

    # Map each wanted prefix to the matching GitHub release asset
    found: dict[str, dict] = {}
    for asset in assets:
        name: str = asset["name"]
        for prefix in WANTED:
            if name.startswith(prefix) and name.endswith(".tgz"):
                found[prefix] = asset

    missing = set(WANTED) - set(found)
    if missing:
        raise RuntimeError(f"Could not find release assets for: {missing}")

    for prefix, out_name in WANTED.items():
        out_path = RAW_DIR / out_name
        if out_path.exists():
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"  Skipping {out_name} (already exists, {size_mb:.1f} MB)")
            continue

        asset = found[prefix]
        asset_mb = asset["size"] / (1024 * 1024)
        print(f"Downloading {prefix} ({asset['name']}, {asset_mb:.1f} MB compressed)…")
        json_bytes = download_and_extract(asset["browser_download_url"], prefix)
        out_path.write_bytes(json_bytes)
        print(f"  Saved → {out_path}  ({out_path.stat().st_size / (1024*1024):.1f} MB)")

    download_kanjivg()

    print("\nAll files ready in data/raw/:")
    for f in RAW_DIR.glob("*.json"):
        print(f"  {f.name}  ({f.stat().st_size / (1024*1024):.1f} MB)")


if __name__ == "__main__":
    main()
