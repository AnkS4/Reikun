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


def _env(name: str, default: str) -> str:
    """os.getenv with whitespace stripped, so a stray space in .env doesn't
    silently break equality checks (e.g. QUERY_REWRITE=heuristic )."""
    return os.getenv(name, default).strip()


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
KANJIVG_DIR = DATA_DIR / "kanjivg"
MODELS_DIR = Path(_env("MODELS_DIR", str(ROOT / "models" / "fastembed")))
MONITORING_DB = Path(_env("MONITORING_DB", str(DATA_DIR / "monitoring" / "reikun.db")))

# Ensure directories we write to actually exist (first-run safety).
for _dir in (RAW_DIR, PROC_DIR, KANJIVG_DIR, MODELS_DIR, MONITORING_DB.parent):
    _dir.mkdir(parents=True, exist_ok=True)

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

COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")
COHERE_API_KEY = os.getenv("COHERE_API_KEY") or None

# Default "heuristic": free regex normalisation only. "auto" additionally
# spends one Cohere call on long English sentence-like queries (best MRR in
# eval/results/retrieval_eval.md, but costs trial-tier tokens per query).
_VALID_QUERY_REWRITE = {"auto", "heuristic", "off"}
QUERY_REWRITE = _env("QUERY_REWRITE", "heuristic").lower()
if QUERY_REWRITE not in _VALID_QUERY_REWRITE:
    raise ValueError(
        f"QUERY_REWRITE={QUERY_REWRITE!r} invalid; expected one of {sorted(_VALID_QUERY_REWRITE)}"
    )
if QUERY_REWRITE == "auto" and not COHERE_API_KEY:
    raise ValueError("QUERY_REWRITE=auto requires COHERE_API_KEY to be set")

DENSE_VECTOR = "dense"
SPARSE_VECTOR = "bm25"


@lru_cache(maxsize=1)
def qdrant_client(timeout: int = 30) -> QdrantClient:
    """Process-wide Qdrant client (cheap to share; thread-safe for REST).

    NOTE: cached by lru_cache(maxsize=1), so only the `timeout` passed on the
    *first* call takes effect for the life of the process — later calls with
    a different timeout silently reuse the first client instead of rebuilding.
    """
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=timeout)
