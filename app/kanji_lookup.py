"""Deterministic kanji lookups (KANJIDIC2 table + KanjiVG stroke order) — no LLM involved.

Both are served from committed JSON under data/processed/ (kanji_table.json,
strokes.json) and shipped in the image — no network access at request time.
"""

import json
import logging
import random
import re
from collections.abc import Collection
from functools import lru_cache

from app.config import PROC_DIR

log = logging.getLogger(__name__)

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
    if within is None:
        return random.choice(_common_kanji())
    allowed = within if isinstance(within, (set, frozenset, dict)) else set(within)  # O(1) membership
    pool = tuple(c for c in _common_kanji() if c in allowed)
    return random.choice(pool or _common_kanji())


# KANJIDIC2's jlpt field is the *former* 4-level test scale (4 most elementary
# → 1 most advanced); the file's own DTD notes old level 2 now straddles N2–N3,
# so both modern levels map to it.
_JLPT_TO_OLD: dict[str, tuple[int, ...]] = {"N5": (4,), "N4": (3,), "N3": (2,), "N2": (2,), "N1": (1,)}


@lru_cache(maxsize=5)
def jlpt_kanji(level: str) -> frozenset[str]:
    """Kanji at JLPT `level` ("N5"…"N1"); empty frozenset for an unknown level."""
    old = _JLPT_TO_OLD.get(level.upper())
    return frozenset(c for c, d in _load_kanji_table().items() if d.get("jlpt_level") in (old or ()))


def lookup_kanji(char: str) -> dict | None:
    """
    Full details for one kanji, or None if not in KANJIDIC2.

    Keys: literal, codepoint_hex, meanings, on_yomi, kun_yomi, stroke_count,
    grade, freq, jlpt_level, common_words (up to 10 dicts).
    """
    return _load_kanji_table().get(char)


# ── Stroke order ─────────────────────────────────────────────────────────────
# KanjiVG ships one SVG per kanji (~27 MB for the 6.4k KANJIDIC2 overlap), of
# which the frontend only draws the stroke paths and number labels. Those are
# extracted once by scripts/download_kanjivg.py into strokes.json (~9 MB,
# committed) — the radical/element metadata that makes up most of each SVG is
# never served, and ~half the kanji in kanji_table have no diagram at all, so
# a per-request fetch would mostly be paying for 404s.

STROKES_PATH = PROC_DIR / "strokes.json"

_STROKE_PATH = re.compile(r'<path id="kvg:[0-9a-f]+-s(\d+)"[^>]*\bd="([^"]+)"')
_STROKE_NUMBER = re.compile(r'<text transform="matrix\(1 0 0 1 ([\d.]+) ([\d.]+)\)">([^<]+)</text>')
_VIEWBOX = re.compile(r'<svg[^>]*\bviewBox="([^"]+)"')


def parse_stroke_svg(svg: str) -> dict:
    """
    One KanjiVG SVG → {view_box, strokes: [d…] in draw order, numbers: [{x, y, value}]}.

    Extracted by attribute rather than served as markup — the JSON is
    sanitized by construction (no raw SVG ever crosses the wire), so the
    frontend builds its own SVG nodes instead of injecting innerHTML.
    """
    strokes = sorted(((int(n), d) for n, d in _STROKE_PATH.findall(svg)), key=lambda t: t[0])
    return {
        "view_box": m.group(1) if (m := _VIEWBOX.search(svg)) else "0 0 109 109",
        "strokes": [d for _, d in strokes],
        "numbers": [{"x": float(x), "y": float(y), "value": int(v)} for x, y, v in _STROKE_NUMBER.findall(svg)],
    }


@lru_cache(maxsize=1)
def _load_strokes() -> dict[str, dict]:
    if not STROKES_PATH.exists():
        log.warning("%s missing — stroke order disabled; run scripts/download_kanjivg.py", STROKES_PATH.name)
        return {}
    return json.loads(STROKES_PATH.read_text(encoding="utf-8"))


def stroke_data(char: str) -> dict | None:
    """Pre-extracted KanjiVG stroke data for `char`, or None when it has no diagram."""
    return _load_strokes().get(char)
