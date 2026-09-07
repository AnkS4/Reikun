"""
Embedding models (fastembed / ONNX, CPU-only).

    dense   – all-MiniLM-L6-v2 (384-d). Chosen over bge-small-en-v1.5 and
              snowflake-arctic-embed-xs after benchmarking on the gold set
              (see eval/embed_model_bench.py, eval/results/embed_model_bench.json):
              both alternatives are English-only tuned and score ~0 MRR on
              Japanese-typed queries in this bilingual corpus.
    sparse  – Qdrant/bm25 for the text-search arm of hybrid retrieval.
    rerank  – ms-marco-MiniLM-L-6-v2 cross-encoder (optional re-ranking step).

Everything is lazily instantiated once per process via `lru_cache`, so the
first call pays the model load cost and later calls are free.
"""

from functools import lru_cache
from typing import Iterable, Iterator

import numpy as np
from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from fastembed.sparse.sparse_embedding_base import SparseEmbedding

from app.config import EMBED_MODEL, MODELS_DIR, RERANK_MODEL, SPARSE_MODEL

VECTOR_DIM = 384
CACHE_DIR = str(MODELS_DIR)


@lru_cache(maxsize=1)
def dense_model() -> TextEmbedding:
    return TextEmbedding(EMBED_MODEL, cache_dir=CACHE_DIR)


@lru_cache(maxsize=1)
def sparse_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(SPARSE_MODEL, cache_dir=CACHE_DIR)


@lru_cache(maxsize=1)
def rerank_model() -> TextCrossEncoder:
    return TextCrossEncoder(RERANK_MODEL, cache_dir=CACHE_DIR)


def embed_query(text: str) -> tuple[list[float], SparseEmbedding]:
    """Dense + sparse embeddings for a single query (uses query-side prefixes)."""
    dense = next(iter(dense_model().query_embed(text)))
    sparse = next(iter(sparse_model().query_embed(text)))
    return np.asarray(dense, dtype=np.float32).tolist(), sparse


def embed_documents(
    texts: Iterable[str], batch_size: int = 128
) -> Iterator[tuple[np.ndarray, SparseEmbedding]]:
    """Yield (dense, sparse) pairs for each document, streaming in batches."""
    texts = list(texts)
    dense_iter = dense_model().embed(texts, batch_size=batch_size)
    sparse_iter = sparse_model().embed(texts, batch_size=batch_size)
    for dense, sparse in zip(dense_iter, sparse_iter):
        yield np.asarray(dense, dtype=np.float32), sparse


def warm_models(include_reranker: bool = True) -> None:
    """Download/load every model once (used at Docker build time)."""
    dense_model()
    sparse_model()
    if include_reranker:
        rerank_model()
