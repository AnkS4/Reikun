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

# Schema stamp for data/processed/chunks.json — build_chunks writes it into
# chunks.meta.json and startup's check_state() refuses to ingest files that
# lack it, so a stale pre-v2 chunks.json can't crash-loop ingest on missing
# keys. Bump when the chunk payload shape changes.
CHUNKS_SCHEMA = 2

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

# ── Serving ──────────────────────────────────────────────────────────────────
# Usage/event telemetry sink: "stdout" (one JSON line per event — the
# stateless-instance default) or "sqlite" (the feedback_log monitoring DB).
TELEMETRY = _env("TELEMETRY", "stdout").lower()

# How long SQLite telemetry rows are kept; pruned once per process start.
# Default 0 = keep forever; set a day count to enable pruning.
TELEMETRY_RETENTION_DAYS = int(_env("TELEMETRY_RETENTION_DAYS", "0"))

# Comma-separated allowed origins for CORS (the standalone API serves a
# different-origin frontend). "*" is the permissive dev default; deployment
# pins it to the site origin.
CORS_ORIGINS = _env("CORS_ORIGINS", "*")


QDRANT_TIMEOUT = int(_env("QDRANT_TIMEOUT", "30"))


@lru_cache(maxsize=1)
def qdrant_client() -> QdrantClient:
    """Process-wide Qdrant client (cheap to share; thread-safe for REST).

    Deliberately parameterless: it is cached once per process, so a per-call
    timeout would silently be decided by whoever called first. Code that
    needs a different timeout (a boot-time reachability probe) builds its
    own short-lived client from QDRANT_URL / QDRANT_API_KEY.
    """
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=QDRANT_TIMEOUT)
