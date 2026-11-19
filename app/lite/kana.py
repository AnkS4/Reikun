"""Static kana tables for /lite/kana — single-sourced from ``kana.json``
at the repo root (the ``i18n/``-style shared file the SPA imports at build
time). This module loads it at import time and re-exports it; edit
``kana.json``, never this file."""

import json
from pathlib import Path

# app/lite/kana.py -> repo root locally, /app in the container image
# (Dockerfile copies kana.json next to app/).
_ROOT = Path(__file__).resolve().parents[2]
_DATA = json.loads((_ROOT / "kana.json").read_text(encoding="utf-8"))

HIRAGANA = _DATA["hiragana"]
KATAKANA = _DATA["katakana"]
ROMAJI_TO_DEVANAGARI = _DATA["romajiToDevanagari"]


def kana_meta_label(romaji: str, lang: str) -> str:
    """The kana chart's meta label for one cell — Devanagari under hi/mr,
    Latin romaji otherwise (same phonetic content, the chart's own script)."""
    if lang in ("hi", "mr"):
        return ROMAJI_TO_DEVANAGARI.get(romaji, romaji)
    return romaji
