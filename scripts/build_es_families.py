"""Build a static etymology-link family index for the Spanish pack.

The Spanish Wiktionary export records, for many entries, the words an editor
linked as its etymological ancestors (`etymology_links`). Grouping descendants
by the ancestor they link to yields real word families — e.g. `matador`,
`matarropa` and `matabuey` under *matar* — which is a different relationship
from the existing Etymology section's flat source-language facets.

This reads the **existing** extract; it never re-runs the Wiktionary extraction.
Both the ancestor and each member must be an entry we actually ship in
`es_words`, so every family link has a dictionary page behind it. Grammatical
labels ("átono", "pronombre reflexivo"), affixes ("-mente"), function words
and language names make huge, meaningless buckets — they are filtered out.

Usage:
    uv run python scripts/build_es_families.py
    uv run python scripts/build_es_families.py --limit 200 --out /tmp/families.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import mmap
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger("build_es_families")
ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data/raw/es/es-extract.jsonl.gz"
CHUNKS = ROOT / "data/processed/es/chunks.json"
OUTPUT = ROOT / "data/processed/es/families.json"

# Words that are grammatical categories, affixes, function words or origin
# languages rather than real family ancestors. Without this the top "families"
# are thousands of unrelated reflexive verbs under "pronombre reflexivo".
_STOPWORDS = frozenset(
    """
    a al ala como con contra del de desde el en ene entre er es esa ese esa
    esta este estos ex fuera hay hacia la las le lo los más me menos mi mis
    no nos o os para por que se ser si sin sobre so su sus tan te ti todo
    un una uno unos ya y
    átono sufijo prefijo aféresis apócope adjetivo sustantivo verbo interjección
    reflexivo locución proverbio extranjerismo latín griego
    """.split()
) | {
    # Multi-word grammatical labels — .split() above would only ban the parts.
    "pronombre reflexivo", "sufijo flexivo", "participio activo",
    "participio pasivo", "nombre propio",
}
_WORD_RE = re.compile(r"^[^\W\d_]+(?:[-'][^\W\d_]+)*$", re.UNICODE)
# Surnames, places and acronym entries link to common ancestors too, but they
# are not useful members of a learner's word family.
_NOISE_GLOSS_RE = re.compile(r"^(Apellido|País|Ciudad|Pueblo|Localidad|Provincia|Siglas|Topónimo)\b", re.I)


def load_readings(path: Path) -> dict[str, str]:
    """lowercased surface → canonical surface, from the built chunks."""
    readings: dict[str, str] = {}
    with path.open("rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        for match in re.finditer(rb'"reading"\s*:\s*"([^"]*)"', mm):
            # Chunks are normally UTF-8, but an ensure_ascii export escapes
            # accents — decode the JSON string rather than trusting the bytes.
            word = json.loads('"' + match.group(1).decode("utf-8") + '"')
            if word:
                readings.setdefault(word.lower(), word)
    return readings


def _first_gloss(entry: dict) -> str:
    for sense in entry.get("senses") or []:
        for gloss in sense.get("glosses") or []:
            if isinstance(gloss, str) and gloss.strip():
                return gloss.strip()[:100]
    return ""


def _ancestor(value: object, readings: dict[str, str]) -> str | None:
    if not isinstance(value, str):
        return None
    ancestor = value.split("#", 1)[0].strip()
    key = ancestor.lower()
    if key in _STOPWORDS or key not in readings or ancestor.startswith("-"):
        return None
    canonical = readings[key]
    if canonical.isupper() and len(canonical) > 2:  # acronyms (PAN, VIH, …)
        return None
    return canonical


def build(source: Path, chunks: Path, *, limit: int, min_members: int, max_members: int) -> list[dict]:
    readings = load_readings(chunks)
    links: dict[str, set[str]] = defaultdict(set)
    glosses: dict[str, str] = {}
    with gzip.open(source, "rt", encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            if entry.get("lang_code") != "es":
                continue
            word = (entry.get("word") or "").strip()
            if not word:
                continue
            glosses.setdefault(word.lower(), _first_gloss(entry))
            for link in entry.get("etymology_links") or []:
                if not isinstance(link, list) or not link:
                    continue
                ancestor = _ancestor(link[0], readings)
                if ancestor and ancestor.lower() != word.lower():
                    links[ancestor.lower()].add(word)

    families = []
    for key, descendants in links.items():
        ancestor = readings[key]
        members = []
        for word in sorted(descendants):
            low = word.lower()
            gloss = glosses.get(low, "")
            if low == key or low not in readings or not _WORD_RE.fullmatch(word) or len(word) < 3:
                continue
            if _NOISE_GLOSS_RE.match(gloss):
                continue
            members.append({"word": readings[low], "gloss": gloss})
        if min_members <= len(members) <= max_members:
            families.append({"word": ancestor, "members": members})
    families.sort(key=lambda family: (-len(family["members"]), family["word"].lower()))
    log.info("%d raw ancestors → %d usable families", len(links), len(families))
    return families[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--chunks", type=Path, default=CHUNKS)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--limit", type=int, default=120)
    parser.add_argument("--min-members", type=int, default=4)
    parser.add_argument("--max-members", type=int, default=40)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    families = build(
        args.source, args.chunks,
        limit=args.limit, min_members=args.min_members, max_members=args.max_members,
    )
    payload = {
        "schema": 1,
        "source": "Spanish Wiktionary etymology_links (es-extract.jsonl.gz) ∩ es_words",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "families": families,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log.info("wrote %d families to %s", len(families), args.out)


if __name__ == "__main__":
    main()
