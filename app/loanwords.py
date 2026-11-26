"""Borrowed-words browse: entries whose payload ``lsource`` names a source
language (JMdict etymology tags — カタカナ gairaigo like コンピュータ ← eng,
plus kanji words like タバコ ← spa, 漢字借用 like 跆拳道 ← kor).

Qdrant can't filter on the nested ``lsource.lang`` path (the dotted-path index
accepts the schema but indexes nothing for arrays of objects — verified against
the live collection 2026-11-14), so the facet is built in-process: one scroll
of the ~6.2k lsource-bearing points, grouped by language and sorted by the common-first rule (``is_common`` first,
then ``wf_score``, then alphabetical headword/reading), then served from a TTL cache. The collection stays the source of
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
# wf_score is fetched solely to rank each language's listing (d["score"]);
# it isn't echoed into the response dicts.
_PAYLOAD_FIELDS = [
    "kanji_form", "reading", "kanji_forms", "readings", "meanings",
    "example_sentences", "is_common", "text", "inflected_forms",
    "lsource", "reading_restrictions", "ke_inf", "senses", "wf_score",
]

_lock = threading.Lock()
_index: dict[str, list[dict]] | None = None
_loaded_at = 0.0

# Precomputed views of _index, swapped atomically as one tuple so a concurrent
# reader never sees facets/listings derived from a different index than the
# guard claims: (facet chip row, {lang: filtered entries}, the index object
# they were derived from). Facet and page requests then cost dict lookups +
# slices instead of re-filtering every entry per request.
_derived: tuple[list[dict[str, Any]], dict[str, list[dict]], dict[str, list[dict]]] | None = None


def _precomputed(idx: dict[str, list[dict]]) -> tuple[list[dict[str, Any]], dict[str, list[dict]]]:
    """(facet dicts, per-language filtered listings) for ``idx``, derived once
    per index object. The real build primes this in _loanwords while the lock
    is held; an index injected by another seam (tests monkeypatching _index or
    _loanwords) derives on first use instead. Derivation is a pure function of
    idx, so concurrent derivations of the same object converge on one winner."""
    global _derived
    cached = _derived
    if cached is not None and cached[2] is idx:
        return cached[0], cached[1]
    listings: dict[str, list[dict]] = {}
    for lang, entries in idx.items():
        # _build only files matching entries into each bucket, so for its
        # output this filter is a no-op — it exists for indexes built by an
        # older code path or monkeypatched in tests (see
        # _entry_has_source_lang). The wasei pseudo-bucket is stored
        # unfiltered: its page never filters, and facets skip it entirely.
        listings[lang] = entries if lang == "wasei" else [
            d for d in entries if _entry_has_source_lang(d, lang)
        ]
    # Same common-first rule as before: raw bucket length desc, stable sort
    # keeps idx's insertion order for ties, wasei never becomes a chip.
    facets = [
        {"lang": lang, "name": lang_name(lang), "count": len(listings[lang])}
        for lang, _ in sorted(idx.items(), key=lambda kv: -len(kv[1]))
        if lang != "wasei"
    ]
    _derived = (facets, listings, idx)
    return facets, listings


def _build() -> dict[str, list[dict]]:
    """Scroll every lsource-bearing point once and group the result dicts by
    source language, best-first: JMdict's ``is_common`` headwords first, then
    ``wf_score`` desc (the same prior search uses), then headword and reading
    alphabetical as a deterministic tie-break — scroll order isn't guaranteed,
    so raw frequency ties must not reshuffle between index builds."""
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
            # An entry can carry several lsource items in the same language
            # (e.g. eng + eng-variant) — list it once per language.
            seen: set[str] = set()
            for src in d["lsource"]:
                # Wasei-eigo items are Japanese-made coinages: they get their
                # own pseudo-bucket below and must NOT be folded into the
                # source language's listing, otherwise /loanwords?lang=eng (and
                # its lite twin) would be dominated by words that already have a
                # dedicated section. Skip them here.
                if src.get("wasei"):
                    continue
                if src["lang"] in seen:
                    continue
                seen.add(src["lang"])
                out.setdefault(src["lang"], []).append(d)
            # Wasei entries — regardless of source lang — also join the
            # pseudo-bucket so /loanwords?lang=wasei lists them. An entry with
            # several wasei tags still counts once.
            if any(src.get("wasei") for src in d["lsource"]):
                out.setdefault("wasei", []).append(d)
        if offset is None:
            break
    for entries in out.values():
        entries.sort(key=lambda d: (not d.get("is_common"),
                                    -(d.get("score") or 0.0),
                                    str(d.get("kanji_form") or d.get("reading") or ""),
                                    str(d.get("reading") or "")))
    return out


def _entry_has_source_lang(d: dict, lang: str) -> bool:
    """Whether ``d`` carries a (non-wasei) lsource item for ``lang``.

    Used to keep wasei-tagged entries out of source-language listings even
    when the in-memory index was built by an older code path or monkeypatched
    in tests.
    """
    lsource = d.get("lsource") or []
    if not lsource:
        # No etymology payload to inspect (synthetic/test entries) — keep.
        return True
    for src in lsource:
        if src.get("lang") == lang and not src.get("wasei"):
            return True
    return False


def _loanwords() -> dict[str, list[dict]]:
    """TTL-cached {lang: [result dicts]} — rebuilt in the background of a lock
    so a cold first hit pays one scroll, later hits are dict lookups."""
    global _index, _loaded_at
    with _lock:
        if _index is None or time.monotonic() - _loaded_at > _TTL:
            _index = _build()
            _loaded_at = time.monotonic()
            # Prime the facet row and per-language listings while the lock is
            # held, so no request ever pays the per-entry filter itself.
            _precomputed(_index)
            log.info("loanwords index: %s languages, %s entries",
                     len(_index), sum(len(v) for v in _index.values()))
        return _index


def loanword_facets() -> list[dict[str, Any]]:
    """[{lang, name, count}] sorted by count desc — the chip row.

    The wasei pseudo-bucket is deliberately excluded: wasei-eigo lives in
    its own dedicated section (the home-grid tile and /loanwords?lang=wasei)
    rather than alongside the source languages. Returns the precomputed row
    itself — callers (the api and lite endpoints) only read it.
    """
    idx = _loanwords()
    facets, _ = _precomputed(idx)
    return facets


def loanwords_page(lang: str, offset: int = 0, limit: int = 50) -> dict[str, Any] | None:
    """One page of a language's borrowed words, or None for an unknown code."""
    idx = _loanwords()
    # The None test stays on the raw index: a known language whose entries all
    # filter out still serves a real page with total 0, not a 404.
    if idx.get(lang) is None:
        return None
    _, listings = _precomputed(idx)
    entries = listings[lang]
    return {
        "lang": lang,
        "name": lang_name(lang),
        "total": len(entries),
        "offset": offset,
        "results": entries[offset:offset + limit],
    }
