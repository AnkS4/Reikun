"""
Headword index: every written form of a JMdict entry → its candidate entries.

Backed by a marisa BytesTrie (`data/processed/headword_index.marisa`, ~26 MB)
that is mmap'd at runtime and built either by scripts/build_chunks.py (from
chunks) or by app.retrieval as a fallback (from a Qdrant payload scroll).
Both builders feed the same `add_entry` / `build_trie` so the on-disk format
and the dedup rules can't drift apart.

Deliberately light — json + marisa_trie only — so the build script can import
it without pulling in Sudachi, Qdrant or fastembed.
"""

import json
from pathlib import Path

import marisa_trie

PAYLOAD_FIELDS = ("kanji_form", "reading", "meanings", "kanji_forms", "readings", "is_common")


class TrieIndex:
    """form → candidate list, served from an mmap'd marisa BytesTrie.

    ~3µs lookups with only the touched pages resident (~30MB) — the in-memory
    dict this replaced held ~340MB, and its 70MB JSON source spiked to ~600MB
    while parsing, OOM-killing 512MB hosts at boot."""

    __slots__ = ("_t",)

    def __init__(self, path: Path | str) -> None:
        self._t = marisa_trie.BytesTrie()
        self._t.mmap(str(path))

    def get(self, form: str) -> list[dict] | None:
        if r := self._t.get(form):
            return json.loads(r[0])
        return None

    def __contains__(self, form: str) -> bool:
        return form in self._t

    def __getitem__(self, form: str) -> list[dict]:
        if (cands := self.get(form)) is None:
            raise KeyError(form)
        return cands


def add_entry(index: dict[str, list[dict]], pay: dict) -> None:
    """Index one entry (a chunk or a Qdrant payload — same keys) under every
    written form. A form shared by several entries (東 belongs to ひがし,
    あずま, トン…) keeps them all as a candidate list in ingest order — the
    morphological analyzer's contextual reading picks the right one; a JMdict
    popularity rank can't be trusted to."""
    entry = {
        "kanji_form": pay.get("kanji_form"),
        "reading": pay.get("reading", ""),
        # 5 senses, not 3: minor senses get picked contextually often enough
        # (吹かす "to rev an engine" is sense #4) that a 3-cap cut them out of
        # the segment tooltip entirely.
        "meanings": (pay.get("meanings") or [])[:5],
        "is_common": bool(pay.get("is_common")),
    }
    pair = (entry["kanji_form"], entry["reading"])
    for key in (pay.get("kanji_form"), pay.get("reading"), *(pay.get("kanji_forms") or []), *(pay.get("readings") or [])):
        if key:
            cands = index.setdefault(key, [])
            if all((c["kanji_form"], c["reading"]) != pair for c in cands):
                cands.append(entry)


def build_trie(index: dict[str, list[dict]], path: Path | str) -> None:
    """Pack form → candidates into a BytesTrie and save it to `path`."""
    items = [(k, json.dumps(v, ensure_ascii=False, separators=(",", ":")).encode())
             for k, v in index.items()]
    marisa_trie.BytesTrie(items).save(str(path))
