"""Spanish language pack — hybrid search over the `es_words` collection.

The es_words corpus (scripts/build_chunks_es.py) holds Spanish lemma entries
whose `meanings` are the English glosses (what the dense model embeds — the
JMdict model: Spanish words explained in English) and whose `definitions_es`
carry the native definitions. `infl_forms` lists every conjugated surface
(hablas/hablasen/hablando…) so a typed inflection exact-matches its lemma.

The search is a compact hybrid — dense + BM25 + an exact arm fused with RRF
server-side — reusing the Japanese pipeline's primitives (embedder, RRF
prefetch shape, hit shaping) without its Japanese machinery (sudachi
segmentation, kanji exact arms, counter aliases, headword trie), which has no
es counterpart.
"""

import os
import time
from functools import lru_cache
from types import MappingProxyType

from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
)

from app.config import DENSE_VECTOR, SPARSE_VECTOR, qdrant_client
from app.embedder import embed_query
from app.query_rewrite import Rewrite
from app.retrieval import MAX_QUERY_CHARS, SearchResponse, _hit_to_dict, _ms_since, _pool

ES_COLLECTION = os.getenv("QDRANT_ES_COLLECTION", "es_words")


def es_exact_filter(query: str) -> Filter:
    """Exact arms for both search directions: the entry's own surface
    (`reading`), its inflected forms (`hablas` → hablar), and its English
    gloss tokens (`house` in casa's gloss_keys)."""
    return Filter(should=[
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="infl_forms", match=MatchValue(value=query)),
        FieldCondition(key="gloss_keys", match=MatchValue(value=query)),
    ])


def _es_query(query: str, num_results: int, vectors=None) -> list[dict]:
    """One hybrid query: dense + BM25 + exact-filtered dense, RRF-fused."""
    vectors = vectors or embed_query(query)
    pool = _pool(num_results)
    if not isinstance(vectors, tuple):
        # Cloud inference: the Document carries both vectors; Qdrant fuses.
        hits = qdrant_client().query_points(ES_COLLECTION, query=vectors, limit=num_results).points
    else:
        dense, sparse = vectors
        prefetch = [Prefetch(query=dense, using=DENSE_VECTOR, limit=pool)]
        if sparse is not None:
            from app.retrieval import _sparse

            prefetch.append(Prefetch(query=_sparse(sparse), using=SPARSE_VECTOR, limit=pool))
        prefetch.append(
            Prefetch(query=dense, using=DENSE_VECTOR, filter=es_exact_filter(query), limit=pool))
        hits = qdrant_client().query_points(
            ES_COLLECTION,
            prefetch=prefetch,
            query=FusionQuery(fusion=Fusion.RRF),
            limit=num_results,
        ).points
    return [_hit_to_dict(h) for h in hits]


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
