#!/usr/bin/env python3
"""
Parse the EDRDG originals (JMdict_e_NG + KANJIDIC2 XML) into embeddable
chunks and a kanji lookup table.

Inputs  (data/raw/):
    JMdict_e_NG_examp.xml  – JMdict "Next Generation" XML, Tatoeba examples
                            embedded (synced daily by scripts/download_edrdg.py)
    kanjidic2.xml          – KANJIDIC2 XML (same source kanjidic2.json was
                            converted from)

Outputs (data/processed/):
    chunks.json      – list of word+example chunks ready for embedding
    kanji_table.json – dict keyed by kanji literal with meanings/readings/strokes

Both XML files carry their DOCTYPE internal subset — all ~270 <!ENTITY>
definitions (POS tags like &n; → "noun (common) (futsuumeishi)", dialect
codes, etc.) live there and ElementTree resolves them automatically.
Stripping the DOCTYPE would break parsing, so the files are parsed as-is
with iterparse (streaming — 74 MB / ~219k entries never fully in memory).

Usage:
    python scripts/build_chunks.py
"""

import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordfreq import tokenize, zipf_frequency  # noqa: E402

from app.config import PROC_DIR, RAW_DIR  # noqa: E402
from app.query_rewrite import gloss_keys  # noqa: E402

log = logging.getLogger(__name__)

JMDICT_XML = "JMdict_e_NG_examp.xml"
KANJIDIC_XML = "kanjidic2.xml"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# jmdict-simplified's `common` flag derives from exactly this tier-1 set —
# verified empirically against jmdict.json (reproduces 22,637 flags ±3 daily
# drift): tier-2 markers (news2/ichi2/gai2) never produce `common` on their
# own, and nfNN bands are a separate ranking that feeds freq_band instead.
COMMON_PRI = frozenset({"news1", "ichi1", "spec1", "spec2", "gai1"})
COMMON_PRI2 = frozenset({"news2", "ichi2", "gai2"})
_NF_RE = re.compile(r"nf(\d{2})")

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


def iter_elements(path: Path, tag: str):
    """Yield each <tag> element, streaming so the tree never fills memory."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing: {path}\nRun  python scripts/download_edrdg.py  first."
        )
    size_mb = path.stat().st_size / (1024 * 1024)
    log.info("Streaming %s  (%.0f MB) …", path.name, size_mb)
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == tag:
            yield elem
            elem.clear()


# ── JMdict parsing ────────────────────────────────────────────────────────────

def _pri_tags(elem, tag: str) -> set[str]:
    return {p.text or "" for p in elem.findall(tag)}


def _commonness(pris: set[str], freq_band: int | None) -> float:
    """Real-valued frequency prior for the FormulaQuery — the max of three
    signals: 1.0 for tier-1 common markers, 0.5 for tier-2-only markers
    (news2/ichi2/gai2 — genuinely common but second-tier), and an nf
    gradient of 0.75 (nf01, top-500) down to ~0.02 (nf48)."""
    score = 0.0
    if pris & COMMON_PRI:
        score = 1.0
    elif pris & COMMON_PRI2:
        score = 0.5
    if freq_band is not None:
        score = max(score, round(0.75 * (49 - freq_band) / 48, 4))
    return score


def _wf_score(kanji: str | None, kana: str | None, kana_pref: bool) -> float:
    """Corpus word frequency as a Zipf value (~0–7: 7 = "the"-tier, 3 = rare).

    The canonical-ranking prior. Unlike JMdict's own signals it is continuous
    and covers every surface form, which is what separates near-synonyms that
    both carry tier-1 pri markers and the same nf band (仕事 5.68 / 作業 4.91)
    and what ranks katakana loanwords correctly in both directions — canonical
    ones score high (ゲーム 5.62, ドア 4.58), translations of convenience low
    (キャット 3.14, ファイア 3.59). JMdict's nfNN bands express neither.

    Scored on the form the word is actually written in: the kanji form, or the
    kana form when there is no kanji or JMdict tags the entry &uk; ("usually
    written using kana alone" — ありがとう 5.70, not 有難う 3.2). Never the max
    of both: a one-mora reading collides with a far more frequent particle and
    would hand rare single-kanji entries a huge score (屁/へ 6.08, 戸/と 7.21).
    """
    form = kana if (kana_pref or not kanji) else kanji
    if not form:
        return 0.0
    # wordfreq has no phrase frequencies: for multi-token input it returns
    # roughly the average of the tokens, so 犬の顔 (4.94) lands next to 犬 (5.10)
    # and 口にする (5.19) above 食べる (4.92). A phrase is strictly rarer than
    # its rarest token, so charge one Zipf decade (10×) per extra token — still
    # far more conservative than the ~9 decades independence would imply.
    tokens = tokenize(form, "ja")
    return round(zipf_frequency(form, "ja") - max(0, len(tokens) - 1), 3)


def _entry_to_chunk(entry: ET.Element) -> dict | None:
    word_id = entry.findtext("ent_seq")

    kanji_forms: list[str] = []
    readings: list[str] = []
    reading_restrictions: dict[str, list[str]] = {}
    pris: set[str] = set()
    primary_kanji: str | None = None
    primary_kana: str | None = None

    for k in entry.findall("k_ele"):
        keb = k.findtext("keb")
        if not keb:
            continue
        kanji_forms.append(keb)
        k_pris = _pri_tags(k, "ke_pri")
        pris |= k_pris
        if primary_kanji is None and k_pris & COMMON_PRI:
            primary_kanji = keb
    if primary_kanji is None and kanji_forms:
        primary_kanji = kanji_forms[0]

    for r in entry.findall("r_ele"):
        reb = r.findtext("reb")
        if not reb:
            continue
        readings.append(reb)
        r_pris = _pri_tags(r, "re_pri")
        pris |= r_pris
        if primary_kana is None and r_pris & COMMON_PRI:
            primary_kana = reb
        # r_ele↔k_ele pairing (what jmdict-simplified called appliesToKanji):
        # re_nokanji = reading-only (empty list); re_restr = applies only to
        # the listed keb. Sense-level stagk/stagr pairing is dropped, as it
        # was in the JSON→chunk flattening.
        if r.find("re_nokanji") is not None:
            reading_restrictions[reb] = []
        elif (restr := [x.text for x in r.findall("re_restr") if x.text]):
            reading_restrictions[reb] = restr
    if primary_kana is None and readings:
        primary_kana = readings[0]
    if primary_kana is None:
        return None  # can't embed a word with no kana

    is_common = bool(pris & COMMON_PRI)
    nf_bands = [int(m[1]) for p in pris if (m := _NF_RE.fullmatch(p))]
    freq_band = min(nf_bands) if nf_bands else None

    meanings: list[str] = []
    primary_meanings: list[str] = []
    example_sentences: list[dict] = []
    related: list[dict] = []
    seen_xref: set[tuple] = set()
    kana_pref = False
    for i, sense in enumerate(entry.findall("sense")):
        # &uk; — "word usually written using kana alone"; the entity resolves to
        # that text, so match on it rather than the entity name. First sense
        # only: 犬 carries &uk; on a minor "snitch" sense, and honouring that
        # would score the entry as いぬ (3.53) instead of 犬 (5.10).
        if i == 0:
            kana_pref = any(
                m.text and "kana alone" in m.text for m in sense.findall("misc"))
        for gloss in sense.findall("gloss"):
            if gloss.get(XML_LANG, "eng") == "eng" and gloss.text:
                meanings.append(gloss.text)
                if i == 0:
                    primary_meanings.append(gloss.text)
        for ex in sense.findall("example"):
            jpn = eng = None
            for s in ex.findall("ex_sent"):
                lang = s.get(XML_LANG, "eng")
                if lang == "jpn" and jpn is None:
                    jpn = s.text
                elif lang == "eng" and eng is None:
                    eng = s.text
            if jpn and eng:
                example_sentences.append({"japanese": jpn, "english": eng})
        for x in sense.findall("xref"):
            key = (x.get("seq") or "", x.text or "")
            if key in seen_xref:
                continue
            seen_xref.add(key)
            related.append({"seq": key[0], "text": key[1]})

    if not meanings:
        return None

    lsource = [
        {"lang": ls.get(XML_LANG, "eng"), "text": ls.text or ""}
        for ls in entry.findall("lsource")
    ]
    notes = [i.text for i in entry.findall("info") if i.text]

    # Display text: primary headword + reading + glosses. The dense
    # vector is built from glosses only at ingest time. Example sentences
    # stay payload-only.
    display = primary_kanji or primary_kana
    kept = meanings
    text = f"{display} [{primary_kana}]: {', '.join(kept[:3])}"
    # BM25 index text: every variant form + reading, not just the primaries —
    # the `ja` route is BM25-only, so a hiragana query like しまうま can only
    # hit if the kana itself is indexed (it isn't the primary reading here,
    # シマウマ is). Variants are dictionary identity, not example-sentence noise.
    sparse_text = f"{' '.join(kanji_forms + readings)}: {', '.join(kept)}"

    chunk = {
        "id": word_id,
        "kanji_form": primary_kanji,
        "reading": primary_kana,
        "meanings": kept,
        # Normalised glosses for exact-match filtering (see
        # app.query_rewrite.gloss_keys).
        "gloss_keys": sorted({k for m in kept for k in gloss_keys(m)}),
        # Gloss keys of the FIRST sense only — "is this English word what the
        # entry primarily means?". Without it, a frequency prior is actively
        # harmful: 足 ("leg") lists "money" as a minor sense and would beat
        # お金 on frequency alone; 委員長 lists "chair" and beats 椅子.
        "primary_gloss_keys": sorted({k for m in primary_meanings for k in gloss_keys(m)}),
        "example_sentences": example_sentences[:5],
        "text": text,
        "sparse_text": sparse_text,
        "is_common": is_common,
        "commonness": _commonness(pris, freq_band),
        # Corpus frequency prior for ranking — see _wf_score. JMdict's own
        # commonness/freq_band stay above for display and ingest filtering, but
        # they are too coarse to rank with (500-word nf buckets, binary pri).
        "wf_score": _wf_score(primary_kanji, primary_kana, kana_pref),
    }
    # Optional payload fields — written only when present to keep chunks.json lean.
    if freq_band is not None:
        chunk["freq_band"] = freq_band
    if len(kanji_forms) > 1:
        chunk["kanji_forms"] = kanji_forms
    if len(readings) > 1:
        chunk["readings"] = readings
    if reading_restrictions:
        chunk["reading_restrictions"] = reading_restrictions
    if related:
        chunk["related"] = related
    if lsource:
        chunk["lsource"] = lsource
    if notes:
        chunk["notes"] = notes
    return chunk


def build_word_chunks() -> tuple[list[dict], dict[str, list[str]]]:
    """
    Convert JMdict entries into flat dicts suitable for embedding + Qdrant
    storage. Also returns kanji_to_ids: maps each kanji character → list of
    word IDs that use it (for the common-words-per-kanji index).
    """
    chunks: list[dict] = []
    kanji_to_ids: dict[str, list[str]] = defaultdict(list)

    total = skipped = 0
    for entry in iter_elements(RAW_DIR / JMDICT_XML, "entry"):
        total += 1
        chunk = _entry_to_chunk(entry)
        if chunk is None:
            skipped += 1
            continue
        chunks.append(chunk)
        if chunk["kanji_form"]:
            for ch in chunk["kanji_form"]:
                if is_kanji(ch):
                    kanji_to_ids[ch].append(chunk["id"])

    log.info(
        "  → %s chunks built from %s entries  (%s skipped – no meaning)",
        f"{len(chunks):,}", f"{total:,}", f"{skipped:,}",
    )
    return chunks, dict(kanji_to_ids)


# ── KANJIDIC2 parsing ─────────────────────────────────────────────────────────

def _int_or_none(text: str | None) -> int | None:
    return int(text) if text else None


def build_kanji_table(
    kanji_to_ids: dict[str, list[str]],
    id_to_chunk: dict[str, dict],
) -> dict[str, dict]:
    """
    Build a flat lookup table:  kanji_literal → details dict.

    Same output schema as the JSON pipeline produced: English meanings
    (m_lang absent = English), on/kun'yomi, stroke count, grade, frequency,
    JLPT level, and up to 10 common words that use the kanji.
    """
    table: dict[str, dict] = {}
    total = 0
    for char in iter_elements(RAW_DIR / KANJIDIC_XML, "character"):
        total += 1
        literal = char.findtext("literal")
        if not literal:
            continue

        misc = char.find("misc")
        stroke_count = grade = freq = jlpt = None
        if misc is not None:
            stroke_count = _int_or_none(misc.findtext("stroke_count"))
            grade = _int_or_none(misc.findtext("grade"))
            freq = _int_or_none(misc.findtext("freq"))
            jlpt = _int_or_none(misc.findtext("jlpt"))

        on_yomi: list[str] = []
        kun_yomi: list[str] = []
        meanings: list[str] = []
        rm = char.find("reading_meaning")
        if rm is not None:
            for group in rm.findall("rmgroup"):
                for reading in group.findall("reading"):
                    t, v = reading.get("r_type"), reading.text
                    if t == "ja_on":
                        on_yomi.append(v)
                    elif t == "ja_kun":
                        kun_yomi.append(v)
                for meaning in group.findall("meaning"):
                    if meaning.get("m_lang", "en") == "en" and meaning.text:
                        meanings.append(meaning.text)

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
                        "meanings": chunk["meanings"],
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
                            "meanings": chunk["meanings"],
                        }
                    )

        table[literal] = {
            "literal": literal,
            "codepoint_hex": f"{ord(literal):05x}",
            "meanings": meanings,
            "on_yomi": on_yomi,
            "kun_yomi": kun_yomi,
            "stroke_count": stroke_count,
            "grade": grade,
            "freq": freq,
            "jlpt_level": jlpt,
            "common_words": common_words,
        }

    log.info("  → %s kanji entries built (of %s characters)", f"{len(table):,}", f"{total:,}")
    return table


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=== Step 1: Build word chunks from %s ===", JMDICT_XML)
    chunks, kanji_to_ids = build_word_chunks()
    id_to_chunk = {c["id"]: c for c in chunks}

    log.info("=== Step 2: Build kanji table from %s ===", KANJIDIC_XML)
    kanji_table = build_kanji_table(kanji_to_ids, id_to_chunk)

    log.info("=== Step 3: Save outputs ===")
    chunks_path = PROC_DIR / "chunks.json"
    kanji_path = PROC_DIR / "kanji_table.json"

    log.info("  Writing %s …", chunks_path.name)
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, separators=(",", ":"))

    log.info("  Writing %s …", kanji_path.name)
    with open(kanji_path, "w", encoding="utf-8") as f:
        json.dump(kanji_table, f, ensure_ascii=False, separators=(",", ":"))

    total_examples = sum(len(c["example_sentences"]) for c in chunks)
    log.info(
        "Done.\n  chunks.json      %.1f MB  (%s chunks, %s example sentences)\n"
        "  kanji_table.json %.1f MB  (%s kanji characters)",
        chunks_path.stat().st_size / (1024 * 1024), f"{len(chunks):,}", f"{total_examples:,}",
        kanji_path.stat().st_size / (1024 * 1024), f"{len(kanji_table):,}",
    )


if __name__ == "__main__":
    main()
