"""
Lightweight usage + feedback logging to a local SQLite database.

Tables
    searches      one row per search request (hashed query, mode, latency, …)
    feedback      thumbs up/down (+1 / -1) tied to a search or an explanation
    kanji_lookups one row per kanji detail view
    explanations  one row per grammar-explanation request (JLPT level, latency)

User-entered text (queries, rewritten queries, explained sentences) is kept
only as a 12-hex-char SHA-256 prefix — enough for frequency analysis without
storing raw free-text input. Rows older than TELEMETRY_RETENTION_DAYS
(default 0 = keep forever) are deleted once per process. SQLite in WAL mode
is plenty for a single-instance deployment.
"""

import hashlib
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from app.config import MONITORING_DB, TELEMETRY_RETENTION_DAYS

_SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    query_hash TEXT NOT NULL,      -- _h() of the raw query
    rewritten_query_hash TEXT,
    rewrite_method TEXT,
    mode TEXT,
    num_results INTEGER,
    result_count INTEGER,
    top_result TEXT,
    latency_ms INTEGER,
    cached INTEGER               -- 1 when served from the in-process result cache
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,          -- 'search' | 'explanation'
    ref_id INTEGER,              -- searches.id or explanations.id
    rating INTEGER NOT NULL,     -- +1 thumbs up, -1 thumbs down
    query_hash TEXT
);
CREATE TABLE IF NOT EXISTS kanji_lookups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    kanji TEXT NOT NULL,
    source TEXT                  -- 'search' | 'pill' | 'dialog' (legacy)
);
CREATE TABLE IF NOT EXISTS explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    sentence_hash TEXT NOT NULL, -- _h() of the explained sentence
    jlpt_level TEXT NOT NULL,
    model TEXT,
    latency_ms INTEGER,
    ok INTEGER
);
"""


def _h(text: str | None) -> str | None:
    """SHA-256 prefix — groups identical inputs for counts without storing them."""
    return None if text is None else hashlib.sha256(text.encode()).hexdigest()[:12]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_init_lock = threading.Lock()
_initialised = False


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    global _initialised
    # mkdir + WAL + CREATE TABLE IF NOT EXISTS are idempotent, so they run
    # once per process rather than in every request's write path. The
    # journal mode is persistent in the database file. The lock guards
    # concurrent first-writers — uvicorn serves plain-def endpoints on a
    # threadpool, so two simultaneous first requests could otherwise race
    # _migrate(): both ALTER TABLE, one dies on 'duplicate column name'.
    conn = sqlite3.connect(MONITORING_DB, timeout=5)
    try:
        if not _initialised:
            with _init_lock:
                if not _initialised:
                    MONITORING_DB.parent.mkdir(parents=True, exist_ok=True)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.executescript(_SCHEMA)
                    _migrate(conn)
                    _prune(conn)
                    _initialised = True
        yield conn
        conn.commit()
    finally:
        conn.close()


# Columns added after a table's first release: CREATE TABLE IF NOT EXISTS
# leaves an existing database untouched, so they're bolted on here.
_ADDED_COLUMNS = {"searches": {"cached": "INTEGER"}}

# Columns renamed when raw text gave way to hashes. Old rows keep their data
# — the raw values are re-hashed in place by _migrate().
_RENAMED_COLUMNS = {
    "searches": {"query": "query_hash", "rewritten_query": "rewritten_query_hash"},
    "feedback": {"query": "query_hash"},
    "explanations": {"sentence": "sentence_hash"},
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, cols in _ADDED_COLUMNS.items():
        have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in cols.items():
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
    for table, cols in _RENAMED_COLUMNS.items():
        have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for old, new in cols.items():
            if old in have and new not in have:
                conn.execute(f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}")
                for rid, raw in conn.execute(f"SELECT id, {new} FROM {table}"):
                    conn.execute(f"UPDATE {table} SET {new} = ? WHERE id = ?", (_h(raw), rid))


def _prune(conn: sqlite3.Connection) -> None:
    if TELEMETRY_RETENTION_DAYS <= 0:
        return
    cutoff = (datetime.now(UTC) - timedelta(days=TELEMETRY_RETENTION_DAYS)).isoformat(timespec="seconds")
    for table in ("searches", "feedback", "kanji_lookups", "explanations"):
        conn.execute(f"DELETE FROM {table} WHERE ts < ?", (cutoff,))


def _insert(table: str, **values) -> int:
    cols = ", ".join(values)
    marks = ", ".join("?" * len(values))
    with _conn() as conn:
        cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(values.values()))
        return int(cur.lastrowid)


# ── Writers ──────────────────────────────────────────────────────────────────

def log_search(
    query: str, *, rewritten_query: str, rewrite_method: str, mode: str,
    num_results: int, result_count: int, top_result: str | None, latency_ms: int,
    cached: bool = False,
) -> int:
    return _insert(
        "searches", ts=_now(), query_hash=_h(query), rewritten_query_hash=_h(rewritten_query),
        rewrite_method=rewrite_method, mode=mode, num_results=num_results, result_count=result_count,
        top_result=top_result, latency_ms=latency_ms, cached=int(cached),
    )


def log_feedback(kind: str, ref_id: int | None, rating: int, query: str | None = None) -> int:
    return _insert("feedback", ts=_now(), kind=kind, ref_id=ref_id, rating=rating, query_hash=_h(query))


def log_kanji_lookup(kanji: str, source: str = "dialog") -> int:
    return _insert("kanji_lookups", ts=_now(), kanji=kanji, source=source)


def log_explanation(sentence: str, jlpt_level: str, *, model: str, latency_ms: int, ok: bool) -> int:
    return _insert(
        "explanations", ts=_now(), sentence_hash=_h(sentence), jlpt_level=jlpt_level, model=model,
        latency_ms=latency_ms, ok=int(ok),
    )
