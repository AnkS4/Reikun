"""
Central configuration shared by the app, scripts and eval tooling.

All values can be overridden through environment variables (or a `.env` file
at the project root). Defaults match docker-compose.yml.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from qdrant_client import QdrantClient

load_dotenv(find_dotenv(usecwd=True))

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
KANJIVG_DIR = DATA_DIR / "kanjivg"
MODELS_DIR = Path(os.getenv("MODELS_DIR", ROOT / "models" / "fastembed"))
MONITORING_DB = Path(os.getenv("MONITORING_DB", DATA_DIR / "monitoring" / "reikun.db"))

# ── Qdrant ───────────────────────────────────────────────────────────────────
# QDRANT_URL wins (e.g. a Qdrant Cloud endpoint); otherwise host/port are used.
QDRANT_URL = os.getenv("QDRANT_URL") or (
    f"http://{os.getenv('QDRANT_HOST', 'localhost')}:{os.getenv('QDRANT_PORT', '6333')}"
)
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION = os.getenv("QDRANT_COLLECTION", "jmdict_chunks")

# ── Models ───────────────────────────────────────────────────────────────────
# all-MiniLM-L6-v2 beat bge-small-en-v1.5 and snowflake-arctic-embed-xs on the
# gold set (eval/embed_model_bench.py → eval/results/embed_model_bench.json):
# both alternatives are English-only tuned and score ~0 on Japanese-typed
# queries, while this corpus mixes English glosses with Japanese kanji/kana.
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SPARSE_MODEL = os.getenv("SPARSE_MODEL", "Qdrant/bm25")
RERANK_MODEL = os.getenv("RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
# Default "none": eval/retrieval_eval.py shows both the local cross-encoder
# (English-only MS MARCO training) and Cohere Rerank *hurt* MRR on this
# bilingual EN/JA corpus relative to plain hybrid search — see
# eval/results/retrieval_eval.md. Kept selectable for the best-practice
# rubric point ("at least evaluating" re-ranking) and future multilingual
# rerankers.
RERANKER = os.getenv("RERANKER", "none").lower()  # local | cohere | none
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
COHERE_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-v3.5")
# Default "heuristic": free regex normalisation only. "auto" additionally
# spends one Cohere call on long English sentence-like queries (best MRR in
# eval/results/retrieval_eval.md, but costs trial-tier tokens per query).
QUERY_REWRITE = os.getenv("QUERY_REWRITE", "heuristic").lower()  # auto | heuristic | off

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "bm25"


@lru_cache(maxsize=1)
def qdrant_client(timeout: int = 30) -> QdrantClient:
    """Process-wide Qdrant client (cheap to share; thread-safe for REST)."""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=timeout)
