#!/usr/bin/env python3
"""
Parse raw JMdict + KANJIDIC2 JSON into embeddable chunks and a kanji lookup table.

Inputs  (data/raw/):
    jmdict.json     – JMdict English with example sentences
    kanjidic2.json  – KANJIDIC2 English meanings + readings

Outputs (data/processed/):
    chunks.json      – list of word+example chunks ready for embedding
    kanji_table.json – dict keyed by kanji literal with meanings/readings/strokes

Usage:
    python scripts/build_chunks.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import PROC_DIR, RAW_DIR  # noqa: E402

# Unicode ranges covering CJK kanji
_CJK_RANGES = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Extension A
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0x20000, 0x2A6DF), # CJK Extension B
]


def is_kanji(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def load_json(name: str) -> dict:
    path = RAW_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing: {path}\nRun  python scripts/download_data.py  first."
        )
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Loading {path.name}  ({size_mb:.0f} MB) …", flush=True)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── JMdict parsing ────────────────────────────────────────────────────────────

def build_word_chunks(
    jmdict: dict,
) -> tuple[list[dict], dict[str, list[str]]]:
    """
    Convert JMdict words into flat dicts suitable for embedding + Qdrant storage.

    Each chunk contains:
        id, kanji_form, reading, meanings[], example_sentences[], text, is_common

    Also returns kanji_to_ids: maps each kanji character → list of word IDs
    that use it (for the common-words-per-kanji index).
    """
    chunks: list[dict] = []
    kanji_to_ids: dict[str, list[str]] = defaultdict(list)

    words: list[dict] = jmdict.get("words", [])
    print(f"  {len(words):,} words in JMdict …")

    skipped = 0
    for word in words:
        word_id: str = word["id"]

        # ── Primary kanji form ────────────────────────────────────────────────
        kanji_forms: list[dict] = word.get("kanji", [])
        primary_kanji: str | None = None
        for k in kanji_forms:
            if k.get("common"):
                primary_kanji = k["text"]
                break
        if primary_kanji is None and kanji_forms:
            primary_kanji = kanji_forms[0]["text"]

        # ── Primary kana reading ──────────────────────────────────────────────
        kana_forms: list[dict] = word.get("kana", [])
        primary_kana: str | None = None
        for k in kana_forms:
            if k.get("common"):
                primary_kana = k["text"]
                break
        if primary_kana is None and kana_forms:
            primary_kana = kana_forms[0]["text"]
        if primary_kana is None:
            skipped += 1
            continue  # can't embed a word with no kana

        meanings: list[str] = []
        example_sentences: list[dict] = []
        for sense in word.get("sense", []):
            for gloss in sense.get("gloss", []):
                if gloss.get("lang") == "eng":
                    meanings.append(gloss["text"])
            for ex in sense.get("examples", []):
                sentences = ex.get("sentences", [])
                jpn = next((s["text"] for s in sentences if s.get("lang") == "jpn"), None)
                eng = next((s["text"] for s in sentences if s.get("lang") == "eng"), None)
                if jpn and eng:
                    example_sentences.append({"japanese": jpn, "english": eng})

        if not meanings:
            skipped += 1
            continue

        # ── Embed text: reading + meanings + example translations ─────────────
        display = primary_kanji or primary_kana
        meaning_str = ", ".join(meanings[:3])
        embed_parts = [f"{display} [{primary_kana}]: {meaning_str}"]
        for ex in example_sentences[:2]:
            embed_parts.append(ex["english"])
        text = ". ".join(embed_parts)

        is_common = any(k.get("common") for k in kanji_forms) or any(
            k.get("common") for k in kana_forms
        )

        chunks.append(
            {
                "id": word_id,
                "kanji_form": primary_kanji,
                "reading": primary_kana,
                "meanings": meanings[:10],
                "example_sentences": example_sentences[:5],
                "text": text,
                "is_common": is_common,
            }
        )

        # Build kanji → word_id index
        if primary_kanji:
            for ch in primary_kanji:
                if is_kanji(ch):
                    kanji_to_ids[ch].append(word_id)

    print(f"  → {len(chunks):,} chunks built  ({skipped:,} skipped – no kana or no meaning)")
    return chunks, dict(kanji_to_ids)


# ── KANJIDIC2 parsing ─────────────────────────────────────────────────────────

def build_kanji_table(
    kanjidic: dict,
    kanji_to_ids: dict[str, list[str]],
    id_to_chunk: dict[str, dict],
) -> dict[str, dict]:
    """
    Build a flat lookup table:  kanji_literal → details dict.

    Includes English meanings, on/kun'yomi, stroke count, JLPT level,
    and up to 10 common words that use this kanji.
    """
    characters: list[dict] = kanjidic.get("characters", [])
    print(f"  {len(characters):,} kanji characters …")

    table: dict[str, dict] = {}
    for char in characters:
        literal: str = char.get("literal", "")
        if not literal:
            continue

        misc: dict = char.get("misc", {})
        stroke_counts: list[int] = misc.get("strokeCounts", [])

        on_yomi: list[str] = []
        kun_yomi: list[str] = []
        meanings: list[str] = []

        rm = char.get("readingMeaning")
        if rm:
            for group in rm.get("groups", []):
                for reading in group.get("readings", []):
                    t = reading.get("type", "")
                    v = reading.get("value", "")
                    if t == "ja_on":
                        on_yomi.append(v)
                    elif t == "ja_kun":
                        kun_yomi.append(v)
                for meaning in group.get("meanings", []):
                    if meaning.get("lang") == "en":
                        meanings.append(meaning["value"])

        # ── Common words using this kanji ─────────────────────────────────────
        word_ids = kanji_to_ids.get(literal, [])
        common_words: list[dict] = []

        # Prefer common-flagged words
        for wid in word_ids[:30]:
            chunk = id_to_chunk.get(wid)
            if chunk and chunk.get("is_common"):
                common_words.append(
                    {
                        "kanji_form": chunk["kanji_form"],
                        "reading": chunk["reading"],
                        "meanings": chunk["meanings"][:3],
                    }
                )
            if len(common_words) >= 10:
                break

        # Fall back to any word if no common ones
        if not common_words:
            for wid in word_ids[:5]:
                chunk = id_to_chunk.get(wid)
                if chunk:
                    common_words.append(
                        {
                            "kanji_form": chunk["kanji_form"],
                            "reading": chunk["reading"],
                            "meanings": chunk["meanings"][:3],
                        }
                    )

        codepoint_hex = f"{ord(literal):05x}"
        freq_val = misc.get("frequency") or misc.get("freq")

        table[literal] = {
            "literal": literal,
            "codepoint_hex": codepoint_hex,
            "meanings": meanings,
            "on_yomi": on_yomi,
            "kun_yomi": kun_yomi,
            "stroke_count": stroke_counts[0] if stroke_counts else None,
            "grade": misc.get("grade"),
            "freq": freq_val,
            "jlpt_level": misc.get("jlptLevel"),
            "common_words": common_words,
        }

    print(f"  → {len(table):,} kanji entries built")
    return table


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Step 1: Load raw data ===")
    jmdict = load_json("jmdict.json")
    kanjidic = load_json("kanjidic2.json")

    print("\n=== Step 2: Build word chunks ===")
    chunks, kanji_to_ids = build_word_chunks(jmdict)
    id_to_chunk = {c["id"]: c for c in chunks}

    print("\n=== Step 3: Build kanji table ===")
    kanji_table = build_kanji_table(kanjidic, kanji_to_ids, id_to_chunk)

    print("\n=== Step 4: Save outputs ===")
    chunks_path = PROC_DIR / "chunks.json"
    kanji_path = PROC_DIR / "kanji_table.json"

    print(f"  Writing {chunks_path.name} …", flush=True)
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, separators=(",", ":"))

    print(f"  Writing {kanji_path.name} …", flush=True)
    with open(kanji_path, "w", encoding="utf-8") as f:
        json.dump(kanji_table, f, ensure_ascii=False, separators=(",", ":"))

    total_examples = sum(len(c["example_sentences"]) for c in chunks)
    print(
        f"\n✓ Done.\n"
        f"  chunks.json      {chunks_path.stat().st_size / (1024*1024):.1f} MB  "
        f"({len(chunks):,} chunks, {total_examples:,} example sentences)\n"
        f"  kanji_table.json {kanji_path.stat().st_size / (1024*1024):.1f} MB  "
        f"({len(kanji_table):,} kanji characters)"
    )


if __name__ == "__main__":
    main()
