#!/usr/bin/env python3
"""Join official Tatoeba Spanish-English exports and match examples to lemmas.

Inputs (weekly exports) belong in data/raw/es/: Spanish/English detailed
sentences, Spanish-English links and the Spanish user-language table. Every
stored pair includes both sentence IDs and author names so the UI can attribute
the CC BY 2.0 FR material and link back to its source.

Matching uses native Wiktionary lemmas and attested forms only. It does not
predict morphology. Output is capped at two compact, linked examples per entry.
"""

from __future__ import annotations

import bz2
import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from wordfreq import zipf_frequency

log = logging.getLogger(__name__)

TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_CONTENT_POS = {"adj", "adv", "intj", "noun", "phrase", "proverb", "verb"}
MAX_EXAMPLES = 2
MIN_CHARS = 15
MAX_CHARS = 220


def _normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold().strip()


def _rows(path: Path) -> Iterable[list[str]]:
    with bz2.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            yield line.rstrip("\n").split("\t")


def _detailed_index(path: Path, wanted: set[int] | None = None) -> dict[int, dict[str, str]]:
    rows: dict[int, dict[str, str]] = {}
    for row in _rows(path):
        if len(row) < 4:
            continue
        try:
            sentence_id = int(row[0])
        except ValueError:
            continue
        if wanted is not None and sentence_id not in wanted:
            continue
        rows[sentence_id] = {
            "lang": row[1],
            "text": row[2].strip(),
            "author": "" if row[3] in ("", r"\N") else row[3],
        }
    return rows


def _surface_index(chunks: list[dict]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    singles: dict[str, list[tuple[float, str, int]]] = defaultdict(list)
    phrases: dict[str, list[tuple[float, str, int]]] = defaultdict(list)
    for chunk in chunks:
        if chunk.get("pos") not in _CONTENT_POS:
            continue
        point_id = int(chunk["id"])
        word = str(chunk.get("reading") or "")
        # A lemma surface is always a sound anchor. An inflection is only used
        # when it is not *more* frequent than the lemma: "como" must not attach
        # an "as soon as" sentence to the verb comer, nor "es" a random sentence
        # to ser. wordfreq is the same prior the pack uses for ranking.
        lemma_frequency = float(chunk.get("wf_score") or 0.0)
        for raw in {word, *(chunk.get("infl_forms") or [])}:
            surface = _normalise(str(raw))
            if len(surface) < 3:
                continue
            if surface != _normalise(word) and zipf_frequency(surface, "es") > lemma_frequency + 0.5:
                continue
            (phrases if " " in surface else singles)[surface].append((lemma_frequency, word, point_id))

    def ranked(index: dict[str, list[tuple[float, str, int]]]) -> dict[str, list[int]]:
        return {
            surface: list(dict.fromkeys(
                point for _, _, point in sorted(rows, key=lambda row: (-row[0], row[1], row[2]))
            ))[:3]
            for surface, rows in index.items()
        }

    return ranked(singles), ranked(phrases)


def _candidate_score(spanish: str, english: str, spanish_author: str, english_author: str) -> int:
    # Prefer compact, complete pairs with both contributors identified.
    return abs(len(spanish) - 70) + abs(len(english) - 55) + (100 if not spanish_author or not english_author else 0)


def build_examples(chunks: list[dict], raw_dir: Path) -> dict[int, list[dict]]:
    spa_links = raw_dir / "spa-eng_links.tsv.bz2"
    spa_detailed = raw_dir / "spa_sentences_detailed.tsv.bz2"
    eng_detailed = raw_dir / "eng_sentences_detailed.tsv.bz2"
    for source in (spa_links, spa_detailed, eng_detailed):
        if not source.is_file():
            raise FileNotFoundError(f"Missing official Tatoeba export: {source}")

    links: list[tuple[int, int]] = []
    spa_ids: set[int] = set()
    eng_ids: set[int] = set()
    seen: set[tuple[int, int]] = set()
    for row in _rows(spa_links):
        if len(row) < 2:
            continue
        try:
            spa_id, eng_id = int(row[0]), int(row[1])
        except ValueError:
            continue
        pair = spa_id, eng_id
        if pair not in seen:
            seen.add(pair)
            links.append(pair)
            spa_ids.add(spa_id)
            eng_ids.add(eng_id)

    spanish = _detailed_index(spa_detailed, spa_ids)
    english = _detailed_index(eng_detailed, eng_ids)
    singles, phrases = _surface_index(chunks)
    ranked_examples: dict[int, list[tuple[int, int, dict]]] = defaultdict(list)
    usable = matched = 0

    for spa_id, eng_id in links:
        spa = spanish.get(spa_id)
        eng = english.get(eng_id)
        if not spa or not eng or spa["lang"] != "spa" or eng["lang"] != "eng":
            continue
        spanish_text, english_text = spa["text"], eng["text"]
        if not MIN_CHARS <= len(spanish_text) <= MAX_CHARS:
            continue
        if not MIN_CHARS <= len(english_text) <= MAX_CHARS:
            continue
        usable += 1
        example = {
            "spanish": spanish_text,
            "english": english_text,
            "spanish_id": spa_id,
            "english_id": eng_id,
            "spanish_author": spa["author"],
            "english_author": eng["author"],
            "license": "CC BY 2.0 FR",
        }
        score = _candidate_score(spanish_text, english_text, spa["author"], eng["author"])
        tokens = [_normalise(token) for token in TOKEN.findall(spanish_text)]
        matched_ids: set[int] = set()
        for i, token in enumerate(tokens):
            matched_ids.update(singles.get(token, ()))
            for size in range(2, min(5, len(tokens) - i) + 1):
                matched_ids.update(phrases.get(" ".join(tokens[i:i + size]), ()))
        if matched_ids:
            matched += 1
        for point_id in matched_ids:
            bucket = ranked_examples[point_id]
            existing = next(
                (idx for idx, (_, existing_id, _) in enumerate(bucket) if existing_id == spa_id), None
            )
            if existing is not None:
                if bucket[existing][0] <= score:
                    continue
                bucket.pop(existing)
            bucket.append((score, spa_id, example))
            bucket.sort(key=lambda item: (item[0], item[1]))
            del bucket[MAX_EXAMPLES:]

    output = {
        point_id: [example for _, _, example in rows]
        for point_id, rows in ranked_examples.items() if rows
    }
    log.info(
        "Tatoeba: %s usable linked pairs; %s matched; %s headwords with up to %s examples",
        f"{usable:,}", f"{matched:,}", f"{len(output):,}", MAX_EXAMPLES,
    )
    return output


def attach_tatoeba_examples(chunks: list[dict], raw_dir: Path) -> int:
    by_id = build_examples(chunks, raw_dir)
    for chunk in chunks:
        examples = by_id.get(int(chunk["id"]))
        if examples:
            chunk["examples_es"] = examples
        else:
            chunk.pop("examples_es", None)
    return len(by_id)
