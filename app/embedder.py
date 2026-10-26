"""
Embedding models (fastembed / ONNX, CPU-only).

    dense   - all-MiniLM-L6-v2 (384-d). Chosen over bge-small-en-v1.5 and
              snowflake-arctic-embed-xs after benchmarking on the gold set
              (see eval/embed_model_bench.py, eval/reports/embed_model_bench.json):
              both alternatives are English-only tuned and score ~0 MRR on
              Japanese-typed queries in this bilingual corpus.
    sparse  - Qdrant/bm25 for the text-search arm of hybrid retrieval.

Everything is lazily instantiated once per process via `functools.cache`, so the
first call pays the model load cost and later calls are free.

When QDRANT_CLOUD_INFERENCE is enabled, embeddings are handled by Qdrant Cloud
via models.Document instead of local FastEmbed — the container no longer needs
FastEmbed/ONNX for query-side work (ingest still uses local models).
"""

from collections.abc import Iterable, Iterator
from functools import cache

import numpy as np
from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.sparse.sparse_embedding_base import SparseEmbedding
from qdrant_client.models import Document

from app.config import EMBED_MODEL, MODELS_DIR, QDRANT_CLOUD_INFERENCE, SPARSE_MODEL

VECTOR_DIM = 384
CACHE_DIR = str(MODELS_DIR)


@cache
def dense_model() -> TextEmbedding:
    return TextEmbedding(EMBED_MODEL, cache_dir=CACHE_DIR)


@cache
def sparse_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(SPARSE_MODEL, cache_dir=CACHE_DIR)


def embed_query(
    text: str, *, dense: bool = True, sparse: bool = True,
) -> tuple[list[float] | None, SparseEmbedding | None] | Document:
    """
    Dense + sparse embeddings for a single query (uses query-side prefixes).

    Either side can be switched off to skip that model entirely — the
    Japanese route and `text` mode never read the dense vector (the
    English-tuned dense model adds nothing but latency there), `vector` mode
    never reads the sparse one. A skipped side comes back as None.

    When QDRANT_CLOUD_INFERENCE is enabled, returns a qdrant_client.models.Document
    instead of pre-computed vectors — Qdrant Cloud handles embedding.
    """
    if QDRANT_CLOUD_INFERENCE:
        # Cloud inference: return Document for Qdrant to embed
        # Model names must be fully qualified (e.g. sentence-transformers/all-MiniLM-L6-v2)
        from app.config import EMBED_MODEL, SPARSE_MODEL

        if dense and sparse:
            # For hybrid, Qdrant can handle both in one Document via options
            document = Document(text=text, model=EMBED_MODEL, options={"sparse_model": SPARSE_MODEL})
        elif dense:
            document = Document(text=text, model=EMBED_MODEL)
        elif sparse:
            document = Document(text=text, model=SPARSE_MODEL)
        else:
            # Neither dense nor sparse - shouldn't happen in practice
            dense_vec = None
            sparse_vec = None
            return dense_vec, sparse_vec
        return document

    # Local inference: compute vectors with FastEmbed
    dense_vec = next(iter(dense_model().query_embed(text))).tolist() if dense else None
    sparse_vec = next(iter(sparse_model().query_embed(text))) if sparse else None
    return dense_vec, sparse_vec


def embed_documents(
    texts: Iterable[str],
    batch_size: int = 128,
    *,
    sparse_texts: Iterable[str] | None = None,
) -> Iterator[tuple[np.ndarray, SparseEmbedding]]:
    """
    Yield (dense, sparse) pairs for each document, streaming in batches.

    `sparse_texts` overrides the input to the BM25 embedder while `texts`
    feeds the dense model — used at ingest so the dense vector sees glosses
    only while BM25 still indexes headword + reading + glosses (the `ja`
    route is BM25-only and needs the Japanese tokens).
    """
    texts = list(texts)
    sparse_texts = texts if sparse_texts is None else list(sparse_texts)
    dense_iter = dense_model().embed(texts, batch_size=batch_size)
    sparse_iter = sparse_model().embed(sparse_texts, batch_size=batch_size)
    # strict=True: the two models must yield one vector per document. A length
    # mismatch would otherwise truncate silently and misalign dense/sparse
    # pairs — i.e. a corrupt index that only shows up as bad search results.
    for dense, sparse in zip(dense_iter, sparse_iter, strict=True):
        yield np.asarray(dense, dtype=np.float32), sparse


def warm_models() -> None:
    """Download/load every model once (used at Docker build time)."""
    dense_model()
    sparse_model()
