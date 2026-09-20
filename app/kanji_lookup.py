"""Deterministic kanji lookups (KANJIDIC2 table + KanjiVG stroke order) — no LLM involved."""

import json
import random
from collections.abc import Collection
from functools import cache, lru_cache
from pathlib import Path

import httpx

from app.config import KANJIVG_DIR, PROC_DIR

KANJIVG_RAW_URL = "https://raw.githubusercontent.com/KanjiVG/kanjivg/master/kanji"
_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF), (0x20000, 0x2A6DF))


def is_kanji(char: str) -> bool:
    return len(char) == 1 and any(lo <= ord(char) <= hi for lo, hi in _CJK_RANGES)


def kanji_in(text: str) -> list[str]:
    """Unique kanji in `text`, in order of first appearance."""
    return list(dict.fromkeys(ch for ch in text if is_kanji(ch)))


@lru_cache(maxsize=1)
def _load_kanji_table() -> dict[str, dict]:
    path = PROC_DIR / "kanji_table.json"
    if not path.exists():
        raise FileNotFoundError(f"kanji_table.json not found at {path}.\nRun  python scripts/build_chunks.py  first.")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _common_kanji() -> tuple[str, ...]:
    """Kanji with a KANJIDIC2 frequency rank — the ~2500 most common."""
    return tuple(c for c, d in _load_kanji_table().items() if d.get("freq"))


def random_kanji(within: Collection[str] | None = None) -> str:
    """Uniform pick from the frequency-ranked kanji, optionally restricted to `within`."""
    pool = _common_kanji() if within is None else tuple(c for c in _common_kanji() if c in within)
    return random.choice(pool or _common_kanji())


def lookup_kanji(char: str) -> dict | None:
    """
    Full details for one kanji, or None if not in KANJIDIC2.

    Keys: literal, codepoint_hex, meanings, on_yomi, kun_yomi, stroke_count,
    grade, freq, jlpt_level, common_words (up to 10 dicts).
    """
    return _load_kanji_table().get(char)


@cache
def get_stroke_diagram(char: str) -> Path | None:
    """
    Local path to the kanji's KanjiVG stroke-order SVG, or None.

    SVGs live offline under data/kanjivg/ (populated by scripts/download_kanjivg.py).
    A missing file is fetched once and cached on disk.
    """
    svg_path = KANJIVG_DIR / f"{ord(char):05x}.svg"
    if svg_path.exists():
        return svg_path
    try:
        resp = httpx.get(f"{KANJIVG_RAW_URL}/{svg_path.name}", timeout=10)
        resp.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
        if resp.content.lstrip().startswith(b"<"):
            KANJIVG_DIR.mkdir(parents=True, exist_ok=True)
            svg_path.write_bytes(resp.content)
            return svg_path
    except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError):
        # Expected cases: 404 (kanji not in KanjiVG), network issues, timeouts
        pass
    except httpx.HTTPError:
        # Catch any other httpx errors as a safety net
        pass
    return None


@cache
def stroke_svg(char: str) -> str | None:
    """Inline-able SVG markup (XML prolog stripped, whitespace collapsed)."""
    path = get_stroke_diagram(char)
    if not path:
        return None
    svg = path.read_text(encoding="utf-8")
    return " ".join(svg[svg.find("<svg"):].split())
