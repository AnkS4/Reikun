#!/usr/bin/env python3
"""Build the Spanish language pack's chunks from the wiktextract extraction.

Reads the verified self-run extract (data/work/es/es-selfrun.jsonl — official
es-Wiktionary Content File Export → scripts/filter_namespaces.py →
`wiktwords --edition es`) and writes data/processed/es/chunks.json in the same
schema as the Japanese chunks (scripts/build_chunks.py), so scripts/ingest.py
consumes it unchanged:  `QDRANT_COLLECTION=es_words python scripts/ingest.py --lang es`.

Lemma selection: wiktextract emits one entry per wiki page — including every
inflected surface (hablo/hablas/habló …) as its own form-of entry. Lemmas are
the entries that are NOT entirely form-of senses; each lemma carries the
inflected surfaces in `infl_forms` (the exact-match arm) so a typed
conjugation ("hablas") resolves to the lemma without ingesting 580k
form-of points.

Usage:
    uv run python scripts/build_chunks_es.py            # full run
    uv run python scripts/build_chunks_es.py --limit 5000
"""

import argparse
import gzip
import hashlib
import json
import logging
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from wordfreq import zipf_frequency

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import CHUNKS_SCHEMA, proc_dir, raw_dir
from app.query_rewrite import gloss_keys

log = logging.getLogger(__name__)

SELF_RUN_PATH = raw_dir("ja").parent.parent / "work" / "es" / "es-selfrun.jsonl"
OUT_DIR = proc_dir("es")
# The English-Wiktionary slice (scripts/filter_lang.py output): the same
# Spanish words with ENGLISH glosses — the layer English→Spanish search needs
# (JMdict's whole point: Japanese words explained in English; the es edition
# only explains them in Spanish).
EN_RAW_PATH = raw_dir("ja").parent.parent / "raw" / "en" / "raw-wiktextract-es.jsonl.gz"

# A sense whose glosses read like a form-of definition ("plural of casa") is
# the fallback signal when wiktextract's form-of tag is absent.
_FORM_OF_GLOSS = re.compile(
    r"^(plural|singular|feminine|masculine|neuter|combining|gerund|past|present|"
    r"inflection|inflected|abbreviated|contraction|alternative|misspelling|"
    r"superlative|comparative|participle|vocative|accusative|genitive|dative)\b[^;]*\bof\b",
    re.IGNORECASE,
)
_ORIGIN_PREFIX = "ES:Palabras provenientes del "
_FORM_METADATA = {"inflection-template", "table-tags"}
_VERB_FORMS = {
    "indicative", "subjunctive", "conditional", "imperative",
    "infinitive", "gerund", "participle",
}


def _is_form_of(sense: dict) -> bool:
    tags = set(sense.get("tags") or [])
    if "form-of" in tags:
        return True
    glosses = sense.get("glosses") or sense.get("raw_glosses") or []
    return bool(glosses) and all(_FORM_OF_GLOSS.match(g) for g in glosses)


def _stable_id(word: str, pos: str) -> int:
    """u63-safe stable id from word+pos — Qdrant point ids are u64; the JMdict
    pack uses ent_seq ints, so this mirrors that with a hash."""
    digest = hashlib.md5(f"{word}#{pos}".encode()).digest()
    return int.from_bytes(digest[:8], "big") >> 1


def _clean_glosses(sense: dict, cap: int = 3) -> list[str]:
    out: list[str] = []
    for g in (sense.get("glosses") or sense.get("raw_glosses") or [])[:cap]:
        g = g.strip()
        if g and g not in out:
            out.append(g)
    return out


def _gloss_key_set(glosses: list[str]) -> list[str]:
    """Normalised exact-match keys for a gloss list — the ja pipeline's
    `gloss_keys` contract. Each semicolon-separated fragment is treated as
    its own gloss, so "to talk; to speak" yields "talk"/"speak" keys instead
    of one long phrase. Only English glosses feed this: native definitions
    would let "red social" match an English "red" query."""
    keys: set[str] = set()
    for gloss in glosses:
        for part in gloss.split(";"):
            keys.update(gloss_keys(part))
    return sorted(keys)[:20]


def _form_entries(forms: list[dict]):
    """Real forms only; Wiktionary tables also emit template markers and empty cells."""
    for item in forms:
        surface = (item.get("form") or "").strip()
        tags = item.get("tags") or []
        if any(ch.isalpha() for ch in surface) and not _FORM_METADATA.intersection(tags):
            yield surface, tags


def _verb_rows(forms: list[dict], *, seen: set[tuple[str, tuple[str, ...]]] | None = None):
    if seen is None:
        seen = set()
    for surface, tags in _form_entries(forms):
        key = surface, tuple(sorted(tags))
        if _VERB_FORMS.intersection(tags) and key not in seen:
            seen.add(key)
            yield {"form": " ".join(tags), "surface": surface, "kana": None}


def _chunk(entry: dict) -> dict:
    word = entry["word"]
    pos = entry.get("pos") or ""
    senses = entry.get("senses") or []

    sense_rows = []
    all_glosses: list[str] = []
    for s in senses:
        glosses = _clean_glosses(s)
        if not glosses:
            continue
        sense_rows.append({"glosses": glosses, "pos": [pos] if pos else []})
        for g in glosses:
            if g.lower() not in {a.lower() for a in all_glosses}:
                all_glosses.append(g)
    meanings = all_glosses[:6]
    text = f"{word}: {'; '.join(meanings)}"
    ipa = next((s.get("ipa") for s in (entry.get("sounds") or []) if s.get("ipa")), None)
    chunk = {
        "id": _stable_id(word, pos),
        "kanji_form": None,
        "reading": word,
        "meanings": meanings,
        # English exact-match keys are filled by _merge_en; native gloss
        # tokens would pollute the English arm ("red social" -> "red").
        "gloss_keys": [],
        "primary_gloss_keys": [],
        "head_gloss_keys": [],
        "example_sentences": [],
        "text": text,
        "sparse_text": f"{word}: {'; '.join(all_glosses[:12])}",
        "is_common": False,
        "commonness": 0.0,
        "wf_score": round(max(zipf_frequency(word, "es"), 0.0), 3),
        "senses": sense_rows[:12],
        "pos": pos,
        "ipa": ipa,
    }

    etymology = list(dict.fromkeys(t.strip() for t in entry.get("etymology_texts", []) if t.strip()))
    if etymology:
        chunk["etymology_es"] = etymology
    # The native extract's source categories belong to this very entry.
    # Etymology links also point to cognates and should not become facets.
    origins = sorted({
        c.removeprefix(_ORIGIN_PREFIX).strip()
        for c in entry.get("categories", []) if c.startswith(_ORIGIN_PREFIX)
    } - {""})
    if origins:
        chunk["origin_languages"] = origins

    forms = entry.get("forms") or []
    surfaces = sorted({surface for surface, _ in _form_entries(forms)} - {word})
    if surfaces:
        chunk["infl_forms"] = surfaces
    if pos == "verb":
        rows = list(_verb_rows(forms))
        if rows:
            chunk["inflected_forms"] = rows
    return chunk


def _load_en_glosses() -> dict[tuple[str, str], dict]:
    """(word.lower(), pos) → best English-Wiktionary entry (the lemma-shaped
    one with the most senses), from the raw en-edition Spanish slice."""
    index: dict[tuple[str, str], tuple[int, dict]] = {}
    if not EN_RAW_PATH.exists():
        log.warning("No en-gloss slice at %s — chunks stay native-Spanish only.", EN_RAW_PATH)
        return {}
    with gzip.open(EN_RAW_PATH, "rt", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("lang_code") != "es":
                continue
            senses = entry.get("senses") or []
            key = (entry["word"].lower(), entry.get("pos") or "")
            rank = (len(senses), 0 if (senses and _is_form_of(senses[0])) else 1)
            if key not in index or rank > index[key][0]:
                index[key] = (rank, entry)
    log.info("en-gloss index: %s (word, pos) keys", f"{len(index):,}")
    return index


def _merge_en(chunk: dict, en_entry: dict | None) -> None:
    """Fold English glosses + en-edition forms into a native-Spanish chunk.

    `meanings` become the English glosses (what the dense model embeds — it
    only ever sees English queries, exactly like Japanese/JMdict) with the
    native definitions preserved in `definitions_es` for display.
    """
    if not en_entry:
        chunk["definitions_es"] = chunk["meanings"]
        return
    en_senses = en_entry.get("senses") or []
    en_glosses: list[str] = []
    for s in en_senses:
        for g in (s.get("glosses") or s.get("raw_glosses") or []):
            g = g.strip()
            if g and g.lower() not in {x.lower() for x in en_glosses}:
                en_glosses.append(g)
            if len(en_glosses) >= 6:
                break
        if len(en_glosses) >= 6:
            break
    chunk["definitions_es"] = chunk["meanings"]
    if en_glosses:
        chunk["meanings"] = en_glosses
        chunk["gloss_keys"] = _gloss_key_set(en_glosses)
        chunk["primary_gloss_keys"] = _gloss_key_set(en_glosses[:1])
        chunk["head_gloss_keys"] = chunk["primary_gloss_keys"]
        chunk["text"] = f"{chunk['reading']}: {'; '.join(en_glosses)}"
        # The BM25 sparse index serves BOTH directions: the English tokens
        # join the native ones (Spanish queries keep matching the native
        # text; English queries gain their gloss tokens).
        chunk["sparse_text"] = f"{chunk['sparse_text']} {'; '.join(en_glosses)}"
    # Preserve the native table (including compound tenses). English
    # Wiktionary supplements it with tagged negative commands, clitic forms
    # and the simple infinitive, and supplies a fallback when no native
    # paradigm was extracted. Both editions feed surface lookup.
    en_forms = en_entry.get("forms") or []
    en_surfaces = {surface for surface, _ in _form_entries(en_forms)} - {chunk["reading"]}
    if en_surfaces:
        chunk["infl_forms"] = sorted(set(chunk.get("infl_forms") or []) | en_surfaces)
    if chunk.get("pos") == "verb" and en_forms:
        rows = chunk.get("inflected_forms", [])
        keys = {(row["surface"], tuple(sorted(row["form"].split()))) for row in rows}
        moods = {tag for _, tags in keys for tag in tags}
        if {"indicative", "subjunctive"} <= moods:
            en_forms = [
                f for f in en_forms
                if {"combined-form", "negative"}.intersection(f.get("tags") or [])
                or (f.get("form") == chunk["reading"] and "infinitive" in (f.get("tags") or []))
            ]
        combined = rows + list(_verb_rows(en_forms, seen=keys))
        if combined:
            chunk["inflected_forms"] = combined


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Build Spanish chunks from the wiktextract self-run.")
    parser.add_argument("--limit", type=int, default=None, help="cap entries (testing)")
    args = parser.parse_args()

    src = Path(SELF_RUN_PATH)
    if not src.exists():
        raise FileNotFoundError(
            f"Missing: {src}\nRe-run the extraction: see local/research/sister-sites/spanish-sister-site-plan.md"
        )

    t0 = time.time()
    seen: dict[tuple[str, str], tuple[int, dict]] = {}
    scanned = form_of = 0
    with src.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("lang_code") != "es" or entry.get("pos") in (None, "suffix", "prefix", "infix"):
                continue
            scanned += 1
            senses = entry.get("senses") or []
            if not senses or all(_is_form_of(s) for s in senses):
                form_of += 1
                continue
            key = (entry["word"], entry.get("pos") or "")
            rank = (len(senses), bool(entry.get("sounds")))
            if key not in seen or rank > seen[key][0]:
                seen[key] = (rank, entry)

    chunks = [_chunk(e) for _, e in seen.values()]
    en_index = _load_en_glosses()
    if en_index:
        merged = 0
        for c in chunks:
            en_entry = en_index.get((c["reading"].lower(), c["pos"]))
            if en_entry:
                _merge_en(c, en_entry[1])
                merged += 1
        log.info("English glosses merged into %s of %s chunks", f"{merged:,}", f"{len(chunks):,}")
    chunks.sort(key=lambda c: (-c["wf_score"], c["reading"]))
    if args.limit:
        chunks = chunks[: args.limit]

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chunks.json").write_text(
        json.dumps(chunks, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out_dir / "chunks.meta.json").write_text(json.dumps({
        "schema": CHUNKS_SCHEMA,
        "entries": len(chunks),
        "source": "eswiktionary content export 2026-11-01 via wiktextract --edition es",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
    }, indent=2) + "\n", encoding="utf-8")

    log.info("Scanned %s es entries (%s form-of skipped) → %s lemma chunks in %.0fs",
             f"{scanned:,}", f"{form_of:,}", f"{len(chunks):,}", time.time() - t0)
    by_pos: dict[str, int] = defaultdict(int)
    for c in chunks:
        by_pos[c["pos"]] += 1
    log.info("POS: %s", dict(sorted(by_pos.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
