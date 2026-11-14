"""Borrowed-words browse: entries whose payload ``lsource`` names a source
language (JMdict etymology tags — カタカナ gairaigo like コンピュータ ← eng,
plus kanji words like タバコ ← spa, 漢字借用 like 跆拳道 ← kor).

Qdrant can't filter on the nested ``lsource.lang`` path (the dotted-path index
accepts the schema but indexes nothing for arrays of objects — verified against
the live collection 2026-11-14), so the facet is built in-process: one scroll
of the ~6.2k lsource-bearing points, grouped by language and sorted by
``wf_score``, then served from a TTL cache. The collection stays the source of
truth; the cache only avoids re-scrolling per request.
"""

import logging
import threading
import time
from typing import Any

from qdrant_client.models import Filter, IsEmptyCondition, PayloadField, PayloadSelectorInclude

from app.config import COLLECTION, qdrant_client
from app.etymology import enrich_lsource, lang_name
from app.retrieval import _hit_to_dict

log = logging.getLogger(__name__)

_TTL = 600.0  # seconds — the dictionary changes on daily syncs, not per request

# Everything _hit_to_dict + the result cards read, plus lsource itself.
_PAYLOAD_FIELDS = [
    "kanji_form", "reading", "kanji_forms", "readings", "meanings",
    "example_sentences", "is_common", "text", "inflected_forms",
    "lsource", "reading_restrictions",
]

_lock = threading.Lock()
_index: dict[str, list[dict]] | None = None
_loaded_at = 0.0


def _build() -> dict[str, list[dict]]:
    """Scroll every lsource-bearing point once and group the result dicts by
    source language, best-first (wf_score desc — the same prior search uses)."""
    out: dict[str, list[dict]] = {}
    offset = None
    while True:
        page, offset = qdrant_client().scroll(
            COLLECTION,
            scroll_filter=Filter(must_not=[IsEmptyCondition(is_empty=PayloadField(key="lsource"))]),
            limit=1000,
            offset=offset,
            with_payload=PayloadSelectorInclude(include=_PAYLOAD_FIELDS),
            with_vectors=False,
        )
        for rec in page:
            d = _hit_to_dict(rec, score=float((rec.payload or {}).get("wf_score") or 0.0))
            d["lsource"] = enrich_lsource(d.get("lsource"))
            for src in d["lsource"]:
                out.setdefault(src["lang"], []).append(d)
        if offset is None:
            break
    for entries in out.values():
        entries.sort(key=lambda d: -(d.get("score") or 0.0))
    return out


def _loanwords() -> dict[str, list[dict]]:
    """TTL-cached {lang: [result dicts]} — rebuilt in the background of a lock
    so a cold first hit pays one scroll, later hits are dict lookups."""
    global _index, _loaded_at
    with _lock:
        if _index is None or time.monotonic() - _loaded_at > _TTL:
            _index = _build()
            _loaded_at = time.monotonic()
            log.info("loanwords index: %s languages, %s entries",
                     len(_index), sum(len(v) for v in _index.values()))
        return _index


def loanword_facets() -> list[dict[str, Any]]:
    """[{lang, name, count}] sorted by count desc — the chip row."""
    idx = _loanwords()
    return [
        {"lang": lang, "name": lang_name(lang), "count": len(entries)}
        for lang, entries in sorted(idx.items(), key=lambda kv: -len(kv[1]))
    ]


def loanwords_page(lang: str, offset: int = 0, limit: int = 50) -> dict[str, Any] | None:
    """One page of a language's borrowed words, or None for an unknown code."""
    idx = _loanwords()
    entries = idx.get(lang)
    if entries is None:
        return None
    return {
        "lang": lang,
        "name": lang_name(lang),
        "total": len(entries),
        "offset": offset,
        "results": entries[offset:offset + limit],
    }
