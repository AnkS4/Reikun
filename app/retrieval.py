"""
Retrieval over the Qdrant `jmdict_chunks` collection.

Modes (all evaluated in eval/retrieval_eval.py):
    vector  – dense cosine search only (baseline)
    text    – sparse BM25 search only
    hybrid  – server-side Reciprocal Rank Fusion of three prefetch arms:
                • dense semantic match
                • BM25 lexical match
                • dense match restricted to exact kanji_form / reading / gloss hits
              (default, best on the gold set)

Optional post-processing:
    rewrite – query rewriting before retrieval (app.query_rewrite)
    rerank  – cross-encoder (local) or Cohere Rerank re-scoring of the fused
              candidates, keeping the top `num_results`
"""

import time
from dataclasses import dataclass, field

from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    SparseVector,
)

from app.config import COLLECTION, DENSE_VECTOR, RERANKER, SPARSE_VECTOR, qdrant_client
from app.embedder import embed_query
from app.query_rewrite import Rewrite, rewrite_query

MODES = ("hybrid", "vector", "text")
RERANK_CANDIDATES = 4  # candidate pool = num_results × this


@dataclass
class SearchResponse:
    results: list[dict]
    rewrite: Rewrite
    mode: str
    reranked: bool
    latency_ms: int
    meta: dict = field(default_factory=dict)


def _hit_to_dict(hit, score: float | None = None) -> dict:
    p = hit.payload or {}
    return {
        "id": int(hit.id),
        "kanji_form": p.get("kanji_form"),
        "reading": p.get("reading", ""),
        "meanings": p.get("meanings", []),
        "example_sentences": p.get("example_sentences", []),
        "is_common": p.get("is_common", False),
        "text": p.get("text", ""),
        "score": round(float(hit.score if score is None else score), 4),
    }


def _exact_filter(query: str) -> Filter:
    return Filter(should=[FieldCondition(key=k, match=MatchValue(value=query)) for k in ("kanji_form", "reading", "meanings")])


def _sparse(vec) -> SparseVector:
    return SparseVector(indices=vec.indices.tolist(), values=vec.values.tolist())


# ── Retrieval arms ───────────────────────────────────────────────────────────

def vector_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Dense cosine search only."""
    dense, _ = vectors or embed_query(query)
    hits = qdrant_client().query_points(COLLECTION, query=dense, using=DENSE_VECTOR, limit=num_results).points
    return [_hit_to_dict(h) for h in hits]


def text_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Sparse BM25 search only."""
    _, sparse = vectors or embed_query(query)
    hits = qdrant_client().query_points(COLLECTION, query=_sparse(sparse), using=SPARSE_VECTOR, limit=num_results).points
    return [_hit_to_dict(h) for h in hits]


def hybrid_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Dense + BM25 + exact-match arms fused with RRF inside Qdrant."""
    dense, sparse = vectors or embed_query(query)
    pool = num_results * 2
    hits = qdrant_client().query_points(
        COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
            Prefetch(query=_sparse(sparse), using=SPARSE_VECTOR, limit=pool),
            Prefetch(query=dense, using=DENSE_VECTOR, filter=_exact_filter(query), limit=pool),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=num_results,
    ).points
    return [_hit_to_dict(h) for h in hits]


_SEARCHERS = {"hybrid": hybrid_search, "vector": vector_search, "text": text_search}


# ── Re-ranking ───────────────────────────────────────────────────────────────

def rerank(query: str, results: list[dict], num_results: int, backend: str | None = None) -> list[dict]:
    """Re-score `results` against `query` with a cross-encoder and keep the top N."""
    backend = (backend or RERANKER).lower()
    if backend == "none" or len(results) <= 1:
        return results[:num_results]

    docs = [r["text"] for r in results]
    if backend == "cohere":
        from app.config import COHERE_RERANK_MODEL
        from app.grammar_explain import rerank as cohere_rerank

        resp = cohere_rerank(query, docs, num_results, model=COHERE_RERANK_MODEL)
        return [{**results[r.index], "score": round(r.relevance_score, 4)} for r in resp.results]

    from app.embedder import rerank_model

    scores = list(rerank_model().rerank(query, docs))
    order = sorted(range(len(results)), key=scores.__getitem__, reverse=True)[:num_results]
    return [{**results[i], "score": round(float(scores[i]), 4)} for i in order]


# ── Public entry point ───────────────────────────────────────────────────────

def search(
    query: str,
    num_results: int = 5,
    mode: str = "hybrid",
    *,
    use_rerank: bool = True,
    rewrite_mode: str | None = None,
    rerank_backend: str | None = None,
) -> SearchResponse:
    """Full pipeline: rewrite → retrieve (mode) → optional rerank."""
    if mode not in _SEARCHERS:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    def ms_since(t: float) -> int:
        return int((time.perf_counter() - t) * 1000)

    t0 = time.perf_counter()
    rw = rewrite_query(query, rewrite_mode)
    t1 = time.perf_counter()
    vectors = embed_query(rw.query)
    t2 = time.perf_counter()
    do_rerank = use_rerank and (rerank_backend or RERANKER) != "none"
    fetch = num_results * RERANK_CANDIDATES if do_rerank else num_results
    results = _SEARCHERS[mode](rw.query, fetch, vectors=vectors)
    t3 = time.perf_counter()
    if do_rerank:
        results = rerank(rw.query, results, num_results, rerank_backend)

    latency_ms = ms_since(t0)
    meta = {
        "rewrite_ms": int((t1 - t0) * 1000),
        "embed_ms": int((t2 - t1) * 1000),
        "retrieve_ms": int((t3 - t2) * 1000),
        "rerank_ms": int((time.perf_counter() - t3) * 1000),
    }
    print(f"search {mode!r}: embed={meta['embed_ms']}ms retrieve={meta['retrieve_ms']}ms "
          f"rerank={meta['rerank_ms']}ms total={latency_ms}ms")
    return SearchResponse(
        results=results,
        rewrite=rw,
        mode=mode,
        reranked=do_rerank,
        latency_ms=latency_ms,
        meta=meta,
    )
