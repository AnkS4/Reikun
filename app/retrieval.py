"""
Retrieval over the Qdrant `jmdict_chunks` collection.

Modes (all evaluated in eval/eval.py --ir):
    auto    – query routing (default): the rewritten query is classified and
              sent down the matching plan —
                ja          Japanese input → BM25 arm + exact-match arm
                              (kanji_form / reading), RRF with the exact arm
                              weighted higher so exact entries pin to the top
                en_word     1–2 word English query → dense + BM25 +
                              exact-match (gloss_keys) arms fused with RRF,
                              then a formula query adds a commonness prior
                en_sentence longer English input → dense-heavy RRF (dense arm
                              weighted 2×) — gloss exact-match can't fire
    vector  – dense cosine search only (baseline)
    text    – sparse BM25 search only
    hybrid  – server-side Reciprocal Rank Fusion of three prefetch arms:
                • dense semantic match
                • BM25 lexical match
                • dense match restricted to exact kanji_form / reading /
                  gloss_keys hits
              (explicit-mode default, best on the gold set before routing)

`gloss_keys` is a keyword-indexed payload field of normalised meanings
(lowercased, parentheticals stripped, "to"-less verb variant included) built
by scripts/build_chunks.py — it fixes exact-match for English queries whose
raw glosses carry parentheticals, e.g. 犬 is "dog (Canis (lupus) familiaris)".

Query rewriting runs before retrieval (app.query_rewrite). A re-ranking
stage (local cross-encoder / Cohere Rerank) was implemented and evaluated —
both hurt MRR on this bilingual corpus — and was removed entirely.
"""

import logging
import time
from dataclasses import dataclass, field
from functools import lru_cache

from qdrant_client.models import (
    FieldCondition,
    Filter,
    FormulaQuery,
    Fusion,
    FusionQuery,
    MatchValue,
    MultExpression,
    Prefetch,
    Rrf,
    RrfQuery,
    SparseVector,
    SumExpression,
)

from app.config import COLLECTION, DENSE_VECTOR, SPARSE_VECTOR, qdrant_client
from app.embedder import embed_query
from app.kanji_lookup import is_kanji
from app.query_rewrite import Rewrite, gloss_key, is_japanese, rewrite_query

log = logging.getLogger(__name__)

MODES = ("auto", "hybrid", "vector", "text")
PREFETCH_MIN = 100      # min candidates fetched per arm — retrieval is cheap,
PREFETCH_FACTOR = 4     # so a generous pool is free and lets fusion rescue
                        # entries that rank poorly in a single arm. This is the
                        # recall ceiling: the formula can only reorder what the
                        # arms return, and raising 30→100 moved Hit@5 77→91 on
                        # eval/eval.py (a diluted entry like 空, whose vector
                        # is spread over 30 glosses, only surfaces this deep).
EXACT_BONUS = 1.0       # additive boost when the query equals a kanji_form /
                        # reading / gloss_key — several arm positions, so an
                        # exact dictionary hit beats a merely-similar entry
COMMON_BOOST = 1.0      # flat prior on JMdict's own commonness (1.0 tier-1 pri
                        # markers, 0.5 tier-2, nf gradient otherwise). Unlike
                        # CANONICAL_BOOST it applies to every candidate, not
                        # just first-sense gloss matches, so it still nudges
                        # results for queries that match no gloss exactly.
CANONICAL_BOOST = 3.0   # K × wf_score × (query is a *first-sense* gloss).
                        # The one canonicality prior, replacing the earlier
                        # commonness / nf-band boosts. Two signals multiplied,
                        # and both are needed:
                        #   wf_score  – corpus Zipf frequency (~0–7), the only
                        #               signal fine-grained enough to order
                        #               near-synonyms that share JMdict's pri
                        #               markers and nf band (仕事 5.7/作業 4.9)
                        #               and to rank katakana either way
                        #               (ゲーム 5.6 vs キャット 3.1).
                        #   primary   – is the query what the entry *mainly*
                        #               means? Frequency alone is harmful
                        #               without it: 足 ("leg") lists "money" as
                        #               a minor sense and outranks お金;
                        #               委員長 lists "chair" and beats 椅子.


@dataclass
class SearchResponse:
    results: list[dict]
    rewrite: Rewrite
    mode: str
    latency_ms: int
    meta: dict = field(default_factory=dict)


def _hit_to_dict(hit, score: float | None = None) -> dict:
    p = hit.payload or {}
    return {
        "id": int(hit.id),
        "kanji_form": p.get("kanji_form"),
        "reading": p.get("reading", ""),
        "kanji_forms": p.get("kanji_forms") or [],
        "readings": p.get("readings") or [],
        "meanings": p.get("meanings", []),
        "example_sentences": p.get("example_sentences", []),
        "is_common": p.get("is_common", False),
        "text": p.get("text", ""),
        "score": round(float(hit.score if score is None else score), 4),
    }


def entry_forms(r: dict) -> tuple:
    """Every written form of a result — primary kanji_form/reading plus the
    variant lists — the same fields _exact_filter matches a Japanese query
    against (a kana query like しごと hits via `reading`, an alternate like
    しまうま via `readings`)."""
    return (r.get("kanji_form"), r.get("reading"),
            *(r.get("kanji_forms") or []), *(r.get("readings") or []))


def _exact_filter(query: str) -> Filter:
    # kanji_form/reading match Japanese input verbatim; kanji_forms/readings
    # hold every variant form so alternates (斑馬, シマウマ) hit too;
    # gloss_keys expects the same normalisation used at index time
    # (lowercased, parens stripped).
    return Filter(should=[
        FieldCondition(key="kanji_form", match=MatchValue(value=query)),
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="kanji_forms", match=MatchValue(value=query)),
        FieldCondition(key="readings", match=MatchValue(value=query)),
        FieldCondition(key="gloss_keys", match=MatchValue(value=gloss_key(query))),
    ])


def _primary_filter(query: str) -> Filter:
    """Matches only entries whose *first sense* means the query — Japanese
    input matches verbatim as before (a headword is its own primary sense)."""
    return Filter(should=[
        FieldCondition(key="kanji_form", match=MatchValue(value=query)),
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="kanji_forms", match=MatchValue(value=query)),
        FieldCondition(key="readings", match=MatchValue(value=query)),
        FieldCondition(key="primary_gloss_keys", match=MatchValue(value=gloss_key(query))),
    ])


def _sparse(vec) -> SparseVector:
    return SparseVector(indices=vec.indices.tolist(), values=vec.values.tolist())


def _pool(num_results: int) -> int:
    return max(PREFETCH_MIN, num_results * PREFETCH_FACTOR)


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
    pool = _pool(num_results)
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


# ── Query routing (mode="auto") ──────────────────────────────────────────────

def route_query(query: str) -> str:
    """ja | en_word | en_sentence — which retrieval plan fits this query."""
    if is_japanese(query):
        return "ja"
    # ≤3 tokens covers gloss-style queries ("to eat", "to be late",
    # "thank you", "train station"); real descriptions run longer.
    return "en_word" if len(query.split()) <= 3 else "en_sentence"


def _rrf(prefetches: list[Prefetch], weights: list[float], limit: int):
    return dict(prefetch=prefetches, query=RrfQuery(rrf=Rrf(weights=weights)), limit=limit)


def _auto_search(query: str, num_results: int, *, vectors, route: str) -> list[dict]:
    dense, sparse = vectors
    pool = _pool(num_results)
    sparse_vec = _sparse(sparse)

    if route == "ja":
        # Dense embeddings are English-tuned (they score ~0 MRR on kana in
        # eval/retrieval_eval.md), so Japanese input goes BM25 + exact-match
        # only. The exact arm is weighted higher so a headword/reading hit
        # always outranks a merely-similar BM25 result.
        params = _rrf(
            [
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, filter=_exact_filter(query), limit=pool),
            ],
            weights=[1.0, 2.0],
            limit=num_results,
        )
    elif route == "en_sentence":
        # No exact arm — a sentence can't equal a headword or a gloss key.
        # Dense carries semantics, so it gets double weight.
        params = _rrf(
            [
                Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
            ],
            weights=[2.0, 1.0],
            limit=num_results,
        )
    else:  # en_word
        # Full hybrid fused with RRF, then a formula query layers two priors on
        # the fused score: +EXACT_BONUS when the query equals a headword,
        # reading or normalised gloss, and +CANONICAL_BOOST × wf_score when the
        # query is the entry's *first-sense* gloss. Ranking exact matches by
        # bonus (not by dense order inside a filtered arm) is what puts 犬 above
        # 猟犬 for "dog"; the canonical prior is what puts it above ワン子.
        # (Nested prefetch → RRF → formula is the documented pattern; a main
        # query can't be both fusion+formula.)
        params = dict(
            prefetch=Prefetch(
                prefetch=[
                    Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
                    Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
                    Prefetch(query=dense, using=DENSE_VECTOR, filter=_exact_filter(query), limit=pool),
                ],
                query=RrfQuery(rrf=Rrf()),
                limit=pool,
            ),
            query=FormulaQuery(
                defaults={"wf_score": 0.0},
                formula=SumExpression(sum=[
                    "$score",
                    MultExpression(mult=[EXACT_BONUS, _exact_filter(query)]),
                    MultExpression(mult=[COMMON_BOOST, "commonness"]),
                    MultExpression(mult=[CANONICAL_BOOST, "wf_score", _primary_filter(query)]),
                ])
            ),
            limit=num_results,
        )

    hits = qdrant_client().query_points(COLLECTION, **params).points
    return [_hit_to_dict(h) for h in hits]


_SEARCHERS = {"hybrid": hybrid_search, "vector": vector_search, "text": text_search}


# ── Japanese compound queries ────────────────────────────────────────────────

@lru_cache(maxsize=1)
def headword_index() -> dict[str, dict]:
    """
    Every kanji_form/reading in the collection → minimal entry info.

    Built by one payload-only scroll (~40 requests for ~37k points) and cached
    for the process lifetime — dictionary contents only change on re-ingest,
    which restarts the app anyway. Used to decompose compound Japanese queries
    ("静かな場所" → 静か + 場所) that have no single dictionary entry.
    """
    index: dict[str, dict] = {}
    offset = None
    client = qdrant_client()
    while True:
        points, offset = client.scroll(
            COLLECTION, with_payload=["kanji_form", "reading", "meanings", "kanji_forms", "readings"],
            with_vectors=False, limit=1000, offset=offset,
        )
        for p in points:
            pay = p.payload or {}
            entry = {
                "kanji_form": pay.get("kanji_form"),
                "reading": pay.get("reading", ""),
                "meanings": (pay.get("meanings") or [])[:3],
            }
            for key in (
                pay.get("kanji_form"),
                pay.get("reading"),
                *(pay.get("kanji_forms") or []),
                *(pay.get("readings") or []),
            ):
                if key:
                    index.setdefault(key, entry)
        if offset is None:
            return index


def segment_japanese(query: str, max_len: int = 12) -> list[dict] | None:
    """
    Greedy longest-match split of a Japanese query into dictionary headwords.

    Returns [{"text", "kanji_form", "reading", "meanings"}, …] when the query
    decomposes into ≥2 known words ("例訓" → 例 + 訓, "静かな場所" → 静か + 場所
    with な unmatched and skipped). None when the query is itself a headword,
    is too long, or doesn't decompose.
    """
    if not query or len(query) > max_len:
        return None
    index = headword_index()
    if query in index:
        return None
    parts: list[dict] = []
    i = 0
    while i < len(query):
        for size in range(min(8, len(query) - i), 0, -1):
            word = query[i : i + size]
            # A lone kana can be a headword too (な → "greens"), but for a
            # compound it is almost always a particle/suffix — only accept
            # single-character segments that are kanji.
            if word in index and (len(word) > 1 or is_kanji(word)):
                parts.append({"text": word, **index[word]})
                i += size
                break
        else:
            i += 1  # unmatched character (particle, suffix …) — skip it
    return parts if len(parts) >= 2 else None


# ── Public entry point ───────────────────────────────────────────────────────

def search(
    query: str,
    num_results: int = 5,
    mode: str = "auto",
    *,
    rewrite_mode: str | None = None,
) -> SearchResponse:
    """Full pipeline: rewrite → route (auto) → retrieve.

    Results are cached per-process: the same (query, settings) pair — whether
    repeated by one user or first asked by another — is served without
    re-embedding or re-querying. Queries are normalised (whitespace + case)
    before keying so superficial variants share an entry. The cache is safe
    because the collection is static between ingest runs (which restart the
    process).
    """
    normalized = " ".join(query.split()).lower()
    return _search_cached(normalized, num_results, mode, rewrite_mode)


@lru_cache(maxsize=512)
def _search_cached(
    query: str,
    num_results: int,
    mode: str,
    rewrite_mode: str | None,
) -> SearchResponse:
    if mode not in _SEARCHERS and mode != "auto":
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    def ms_since(t: float) -> int:
        return int((time.perf_counter() - t) * 1000)

    t0 = time.perf_counter()
    rw = rewrite_query(query, rewrite_mode)
    t1 = time.perf_counter()

    route = route_query(rw.query) if mode == "auto" else None
    # Japanese routes never touch the dense model (English-tuned, ~useless on
    # kana) — skipping it saves the embedding time on those queries entirely.
    vectors = embed_query(rw.query, dense=route != "ja")
    t2 = time.perf_counter()

    if mode == "auto":
        results = _auto_search(rw.query, num_results, vectors=vectors, route=route)
    else:
        results = _SEARCHERS[mode](rw.query, num_results, vectors=vectors)
    t3 = time.perf_counter()

    meta = {
        "rewrite_ms": int((t1 - t0) * 1000),
        "embed_ms": int((t2 - t1) * 1000),
        "retrieve_ms": int((t3 - t2) * 1000),
    }
    if route:
        meta["route"] = route
        # A Japanese query with no exact headword hit may be a compound
        # expression — decompose it so the UI can show the parts.
        if route == "ja" and not any(rw.query in entry_forms(r) for r in results):
            try:
                if segments := segment_japanese(rw.query):
                    meta["segments"] = segments
                    if not results:
                        # Compound query with no single entry — surface the
                        # segment entries as the results themselves so the UI
                        # and API consumers get the decomposed words directly.
                        results = [
                            {
                                "id": None,
                                "kanji_form": s["kanji_form"],
                                "reading": s["reading"],
                                "meanings": s["meanings"],
                                "example_sentences": [],
                                "is_common": False,
                                "text": s["text"],
                                "score": 0.0,
                            }
                            for s in segments[:num_results]
                        ]
            except Exception as exc:
                log.warning("segmentation failed for %r: %s", rw.query, exc)

    latency_ms = ms_since(t0)
    log.info(
        "search %s%s: embed=%dms retrieve=%dms total=%dms",
        mode, f"/{route}" if route else "",
        meta["embed_ms"], meta["retrieve_ms"], latency_ms,
    )
    return SearchResponse(
        results=results,
        rewrite=rw,
        mode=mode,
        latency_ms=latency_ms,
        meta=meta,
    )
