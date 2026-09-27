"""
Lightweight usage + feedback logging to a local SQLite database.

Tables
    searches      one row per search request (query, rewrite, mode, latency, …)
    feedback      thumbs up/down (+1 / -1) tied to a search or an explanation
    kanji_lookups one row per kanji detail view
    explanations  one row per grammar-explanation request (JLPT level, latency)

The dashboard page (app/ui/dashboard.py) reads these tables with pandas.
SQLite in WAL mode is plenty for a single-instance Streamlit app.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pandas as pd

from app.config import MONITORING_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    query TEXT NOT NULL,
    rewritten_query TEXT,
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
    query TEXT
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
    sentence TEXT NOT NULL,
    jlpt_level TEXT NOT NULL,
    model TEXT,
    latency_ms INTEGER,
    ok INTEGER
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_initialised = False


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    global _initialised
    # mkdir + WAL + CREATE TABLE IF NOT EXISTS are idempotent, so they run
    # once per process rather than in every request's write path. The
    # journal mode is persistent in the database file.
    if not _initialised:
        MONITORING_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MONITORING_DB, timeout=5)
    try:
        if not _initialised:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            _migrate(conn)
            _initialised = True
        yield conn
        conn.commit()
    finally:
        conn.close()


# Columns added after a table's first release: CREATE TABLE IF NOT EXISTS
# leaves an existing database untouched, so they're bolted on here.
_ADDED_COLUMNS = {"searches": {"cached": "INTEGER"}}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, cols in _ADDED_COLUMNS.items():
        have = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, sql_type in cols.items():
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


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
        "searches", ts=_now(), query=query, rewritten_query=rewritten_query, rewrite_method=rewrite_method,
        mode=mode, num_results=num_results, result_count=result_count,
        top_result=top_result, latency_ms=latency_ms, cached=int(cached),
    )


def log_feedback(kind: str, ref_id: int | None, rating: int, query: str | None = None) -> int:
    return _insert("feedback", ts=_now(), kind=kind, ref_id=ref_id, rating=rating, query=query)


def log_kanji_lookup(kanji: str, source: str = "dialog") -> int:
    return _insert("kanji_lookups", ts=_now(), kanji=kanji, source=source)


def log_explanation(sentence: str, jlpt_level: str, *, model: str, latency_ms: int, ok: bool) -> int:
    return _insert(
        "explanations", ts=_now(), sentence=sentence, jlpt_level=jlpt_level, model=model,
        latency_ms=latency_ms, ok=int(ok),
    )


# ── Readers (dashboard) ──────────────────────────────────────────────────────

def load_table(table: str) -> pd.DataFrame:
    """Whole table as a DataFrame with `ts` parsed to UTC datetimes."""
    if table not in {"searches", "feedback", "kanji_lookups", "explanations"}:
        raise ValueError(table)
    with _conn() as conn:
        df = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY id", conn)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df
