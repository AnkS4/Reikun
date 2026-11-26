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

log = logging.getLogger(__name__)

SELF_RUN_PATH = raw_dir("ja").parent.parent / "work" / "es" / "es-selfrun.jsonl"
OUT_DIR = proc_dir("es")

# A sense whose glosses read like a form-of definition ("plural of casa") is
# the fallback signal when wiktextract's form-of tag is absent.
_FORM_OF_GLOSS = re.compile(
    r"^(plural|singular|feminine|masculine|neuter|combining|gerund|past|present|"
    r"inflection|inflected|abbreviated|contraction|alternative|misspelling|"
    r"superlative|comparative|participle|vocative|accusative|genitive|dative)\b[^;]*\bof\b",
    re.IGNORECASE,
)


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
    gloss_keys = list({t.lower() for g in all_glosses for t in g.split()})[:20]
    primary = sense_rows[0]["glosses"] if sense_rows else []
    primary_keys = list({t.lower() for g in primary for t in g.split()})[:20]

    text = f"{word}: {'; '.join(meanings)}"
    chunk = {
        "id": _stable_id(word, pos),
        "kanji_form": None,
        "reading": word,
        "meanings": meanings,
        "gloss_keys": gloss_keys,
        "primary_gloss_keys": primary_keys,
        "head_gloss_keys": primary[:1],
        "example_sentences": [],
        "text": text,
        "sparse_text": f"{word}: {'; '.join(all_glosses[:12])}",
        "is_common": False,
        "commonness": 0.0,
        "wf_score": round(max(zipf_frequency(word, "es"), 0.0), 3),
        "senses": sense_rows[:12],
        "pos": pos,
    }

    forms = entry.get("forms") or []
    surfaces = sorted({f["form"] for f in forms if f.get("form")} - {word})
    if surfaces:
        chunk["infl_forms"] = surfaces
        if pos == "verb":
            chunk["inflected_forms"] = [
                {"form": " ".join(f.get("tags") or []) or "inflected form",
                 "surface": f["form"], "kana": None}
                for f in forms
                if f.get("form") and f["form"] != word
            ][:200]
    return chunk


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
