"""Spanish language pack — hybrid search over the `es_words` collection.

The es_words corpus (scripts/build_chunks_es.py) holds Spanish lemma entries
whose `meanings` are the English glosses (what the dense model embeds — the
JMdict model: Spanish words explained in English) and whose `definitions_es`
carry the native definitions. `infl_forms` lists every conjugated surface
(hablas/hablasen/hablando…) so a typed inflection exact-matches its lemma.

The search is a compact hybrid — BM25 (Spanish input) or dense+BM25
(English input), plus frequency-ordered exact arms, language-routed and fused
with weighted RRF — reusing the Japanese pipeline's primitives (embedder, RRF
prefetch shape, hit shaping) without its Japanese machinery (sudachi
segmentation, kanji exact arms, counter aliases, headword trie), which has no
es counterpart.
"""

import os
import re
import time
from functools import lru_cache
from types import MappingProxyType

from qdrant_client.models import (
    Direction,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    OrderBy,
    OrderByQuery,
    Prefetch,
)
from wordfreq import zipf_frequency

from app.config import DENSE_VECTOR, SPARSE_VECTOR, qdrant_client
from app.embedder import embed_query
from app.query_rewrite import Rewrite, gloss_key
from app.retrieval import (
    MAX_QUERY_CHARS,
    SearchResponse,
    _hit_to_dict,
    _ms_since,
    _pool,
    _rrf,
    _sparse,
)

ES_COLLECTION = os.getenv("QDRANT_ES_COLLECTION", "es_words")
_ORIGIN_FIELD = "origin_languages"

# RRF's default k=60 flattens rank gaps: a rank-5 exact-gloss hit can tie a
# rank-1 one once the other arms add up. With k=1 the exact arms' ordering
# dominates — which is the point of the frequency-ordered prefetches.
RRF_K = 1


def es_word_filter(query: str) -> Filter:
    """The Spanish-input exact arm: the entry's own surface (`reading`) or one
    of its inflected forms (`hablas` → hablar). Deliberately NOT gloss_keys —
    native gloss tokens ("hablar") appear in hundreds of unrelated
    definitions."""
    return Filter(should=[
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="infl_forms", match=MatchValue(value=query)),
    ])


def es_gloss_filter(query: str) -> Filter:
    """The English-input exact arm: the query as a normalised primary gloss
    (`house` in casa's primary_gloss_keys, but not in casita's "diminutive of
    casa"). Phrase keys make multi-word headline glosses exact too ("to
    speak" -> hablar)."""
    return Filter(should=[FieldCondition(
        key="primary_gloss_keys", match=MatchValue(value=gloss_key(query)))])


def _looks_spanish(query: str) -> bool:
    """Language route by relative frequency, not an absolute es-zipf bar:
    wordfreq's es corpus carries plenty of English (subtitle loans — "house"
    scores 4.2), so a fixed threshold misroutes common English words. Sum the
    per-token zipf scores of both corpora: phrase entries are sparse in
    wordfreq, while the tokens ("casa"+"grande") are decisive. Ties and
    unknowns fall through to the English route, where the dense arm is safe
    and the exact-word arm still catches Spanish homographs."""
    tokens = re.findall(r"[^\W_]+", query.lower())
    if not tokens:
        return False
    es = sum(zipf_frequency(t, "es") for t in tokens)
    en = sum(zipf_frequency(t, "en") for t in tokens)
    return es > 0 and es > en


def _es_query(query: str, num_results: int, vectors=None) -> list[dict]:
    """Route by input language, then fuse with weighted RRF:

    - **Spanish input**: the dense model is English-tuned and pure noise on
      Spanish text, so it stays out — BM25 + the exact arm, where the exact
      arm matches ONLY the word itself or one of its inflected surfaces (NOT
      gloss_keys: native gloss tokens like "hablar" appear in hundreds of
      unrelated definitions) and ranks the filtered set by an ORDER-BY
      prefetch (wf_score DESC) — no vector scoring, so the lemma always
      carries the arm (the ja route's documented trick).
    - **English input**: dense leads (semantic over the English glosses),
      BM25 rides along (the sparse index holds both languages' tokens), the
      exact arm pins primary-gloss hits ("house" -> casa, not casita's
      "diminutive of casa"), and a low-weight word arm catches Spanish
      homographs.
    """
    vectors = vectors or embed_query(query)
    pool = _pool(num_results)
    client = qdrant_client()
    if not isinstance(vectors, tuple):
        # Cloud inference: the Document carries both vectors; Qdrant fuses.
        hits = client.query_points(ES_COLLECTION, query=vectors, limit=num_results).points
        return [_es_hit_to_dict(h) for h in hits]

    dense, sparse = vectors
    sparse_arm: Prefetch | None = None
    if sparse is not None:
        sparse_arm = Prefetch(query=_sparse(sparse), using=SPARSE_VECTOR, limit=pool)
    word_arm = Prefetch(
        query=OrderByQuery(order_by=OrderBy(key="wf_score", direction=Direction.DESC)),
        filter=es_word_filter(query),
        limit=pool,
    )
    if _looks_spanish(query):
        arms = [(sparse_arm, 1.0), (word_arm, 3.0)]
    else:  # English (or ambiguous) input
        arms = [
            (Prefetch(query=dense, using=DENSE_VECTOR, limit=pool), 2.0),
            (sparse_arm, 1.0),
            (Prefetch(query=OrderByQuery(
                          order_by=OrderBy(key="wf_score", direction=Direction.DESC)),
                      filter=es_gloss_filter(query), limit=pool), 4.0),
            (word_arm, 1.0),
        ]
    prefetches = [arm for arm, _ in arms if arm is not None]
    weights = [weight for arm, weight in arms if arm is not None]
    params = _rrf(prefetches, weights, limit=num_results, k=RRF_K)
    hits = client.query_points(ES_COLLECTION, **params).points
    return [_es_hit_to_dict(h) for h in hits]


def _es_hit_to_dict(hit, score: float | None = None) -> dict:
    result = _hit_to_dict(hit, score=score)
    payload = hit.payload or {}
    # Chunks with English glosses carry a separate Spanish definitions list.
    # Older native-only chunks leave that field null and store them in meanings.
    definitions = payload.get("definitions_es")
    result["definitions_es"] = result["meanings"] if definitions is None else definitions
    for field in ("etymology_es", _ORIGIN_FIELD, "examples_es"):
        result[field] = payload.get(field) or []
    return result


def es_etymology_facets() -> list[dict]:
    """Use the indexed keyword array to count tagged entries in Qdrant."""
    hits = qdrant_client().facet(ES_COLLECTION, _ORIGIN_FIELD, limit=512, exact=True).hits
    facets = [
        {"lang": h.value, "name": h.value[0].upper() + h.value[1:], "count": h.count}
        for h in hits if isinstance(h.value, str) and h.value
    ]
    return sorted(facets, key=lambda facet: (-facet["count"], facet["lang"]))


def es_etymology_page(lang: str, offset: int, limit: int) -> dict | None:
    """Page through entries with the selected Spanish Wiktionary origin tag."""
    selection = Filter(must=[FieldCondition(key=_ORIGIN_FIELD, match=MatchValue(value=lang))])
    client = qdrant_client()
    total = client.count(ES_COLLECTION, count_filter=selection, exact=True).count
    if not total:
        return None
    hits = []
    if offset < total:
        hits = client.query_points(
            ES_COLLECTION,
            query=OrderByQuery(order_by=OrderBy(key="wf_score", direction=Direction.DESC)),
            query_filter=selection,
            limit=limit,
            offset=offset,
        ).points
    return {
        "lang": lang,
        "name": lang[0].upper() + lang[1:],
        "total": total,
        "offset": offset,
        "results": [_es_hit_to_dict(hit, score=0.0) for hit in hits],
    }


def es_conjugations(word: str) -> dict | None:
    """Read a verb table by headword, falling back to an exact inflection."""
    normalized = " ".join(word.split())
    forms = list(dict.fromkeys((normalized, normalized.lower())))
    client = qdrant_client()
    for field in ("reading", "infl_forms"):
        points = client.query_points(
            ES_COLLECTION,
            query=OrderByQuery(order_by=OrderBy(key="wf_score", direction=Direction.DESC)),
            query_filter=Filter(must=[FieldCondition(key=field, match=MatchAny(any=forms))]),
            with_payload=["reading", "inflected_forms"],
            limit=50,
        ).points
        for point in points:
            payload = point.payload or {}
            if payload.get("inflected_forms"):
                return {"word": payload["reading"], "inflected_forms": payload["inflected_forms"]}
    return None


@lru_cache(maxsize=512)
def _search_cached(query: str, num_results: int) -> tuple[SearchResponse, float]:
    t0 = time.perf_counter()
    results = tuple(_es_query(query, num_results))
    resp = SearchResponse(
        results=results,
        rewrite=Rewrite(original=query, query=query, method="none"),
        mode="es",
        latency_ms=_ms_since(t0),
    )
    return resp, time.perf_counter()


def search_es(query: str, num_results: int = 5) -> SearchResponse:
    """Full es pipeline: normalise → (cache) → hybrid retrieve. Same response
    shape and caching discipline as app.retrieval.search."""
    t0 = time.perf_counter()
    original = query.strip()
    normalized = " ".join(query.split()).lower()
    if len(normalized) > MAX_QUERY_CHARS:
        return SearchResponse(
            results=(),
            rewrite=Rewrite(original=original, query=normalized, method="none"),
            mode="es",
            latency_ms=_ms_since(t0),
            meta=MappingProxyType({"too_long": MAX_QUERY_CHARS}),
        )
    resp, computed_at = _search_cached(normalized, num_results)
    if computed_at < t0:
        resp = SearchResponse(
            results=resp.results, rewrite=resp.rewrite, mode=resp.mode,
            latency_ms=_ms_since(t0), meta=MappingProxyType({**resp.meta, "cached": True}),
        )
    if resp.rewrite.original != original:
        resp = SearchResponse(
            results=resp.results,
            rewrite=Rewrite(original=original, query=resp.rewrite.query, method=resp.rewrite.method),
            mode=resp.mode, latency_ms=resp.latency_ms, meta=resp.meta,
        )
    return resp
