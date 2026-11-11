"""Telemetry: searches keep raw text, feedback/explanations stay hashed."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import app.telemetry as telemetry
import scripts.feedback_log as fl
from app.config import TELEMETRY_RETENTION_DAYS
from app.telemetry import _h, _SqliteTelemetry, _StdoutTelemetry


def test_retention_defaults_to_keep_forever() -> None:
    # The shipped posture: no purge window unless an operator sets one.
    assert TELEMETRY_RETENTION_DAYS == 0


def test_h_is_sha256_prefix() -> None:
    assert _h("cat") == hashlib.sha256(b"cat").hexdigest()[:12]
    assert _h("cat") == _h("cat") != _h("dog")
    assert _h(None) is None


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch monitoring DB — patch the module-level MONITORING_DB and
    reset the once-per-process init flag so each test gets a fresh schema."""
    path = tmp_path / "reikun.db"
    monkeypatch.setattr(fl, "MONITORING_DB", path)
    monkeypatch.setattr(fl, "_initialised", False)
    return path


def _rows(db: Path, table: str = "searches") -> list[tuple]:
    return sqlite3.connect(db).execute(f"SELECT * FROM {table}").fetchall()


def test_search_stores_query_and_hash(db: Path) -> None:
    fl.log_search("raw query", rewritten_query="rewritten gloss", rewrite_method="heuristic",
                  mode="auto", num_results=1, result_count=1, top_result=None, latency_ms=1)
    row = sqlite3.connect(db).execute(
        "SELECT query, query_hash, rewritten_query, rewritten_query_hash, rewrite_method,"
        " rewritten FROM searches").fetchone()
    assert row == ("raw query", _h("raw query"), "rewritten gloss", _h("rewritten gloss"),
                   "heuristic", 1)


def test_stdout_sink_emits_raw_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def capture(event: str, **fields) -> None:
        captured.update(event=event, **fields)

    monkeypatch.setattr("app.telemetry._emit", capture)
    _StdoutTelemetry().search(
        "raw query", rewritten_query="gloss", rewrite_method="heuristic", mode="auto",
        num_results=1, result_count=1, top_result=None, latency_ms=5,
    )
    assert captured["event"] == "search"
    assert captured["query"] == "raw query"
    assert captured["rewritten_query"] == "gloss"
    assert captured["query_hash"] == _h("raw query")


def test_search_unchanged_query_not_rewritten(db: Path) -> None:
    fl.log_search("same", rewritten_query="same", rewrite_method="none",
                  mode="auto", num_results=1, result_count=1, top_result=None, latency_ms=1)
    assert sqlite3.connect(db).execute("SELECT rewritten FROM searches").fetchone() == (0,)


def test_feedback_and_explanation_hash_too(db: Path) -> None:
    fl.log_feedback("search", None, 1, "raw query")
    fl.log_explanation("猫が好きです", "N5", model="m", latency_ms=1, ok=True)
    assert sqlite3.connect(db).execute("SELECT query_hash FROM feedback").fetchone() == (_h("raw query"),)
    assert sqlite3.connect(db).execute(
        "SELECT sentence_hash FROM explanations").fetchone() == (_h("猫が好きです"),)


def test_migration_readds_raw_search_columns(db: Path) -> None:
    # A pre-hash DB has raw query/rewritten_query and no *_hash columns.
    # The seeded row is recent so the init-time retention purge doesn't
    # remove it before the migration runs (that path is tested below).
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE searches (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,"
        " query TEXT, rewritten_query TEXT, rewrite_method TEXT, mode TEXT,"
        " num_results INTEGER, result_count INTEGER, top_result TEXT, latency_ms INTEGER)"
    )
    seeded_ts = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec="seconds")
    con.execute(
        "INSERT INTO searches (ts, query, rewritten_query, latency_ms)"
        " VALUES (?, 'raw', 'gloss', 5)",
        (seeded_ts,),
    )
    con.commit()
    con.close()

    # Initialising through the writer runs the migration + schema.
    fl.log_search("new", rewritten_query="new", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)

    con = sqlite3.connect(db)
    columns = {row[1] for row in con.execute("PRAGMA table_info(searches)")}
    assert {"query", "rewritten_query", "query_hash", "rewritten_query_hash"} <= columns
    assert con.execute(
        "SELECT query, query_hash FROM searches WHERE query = 'new'"
    ).fetchone() == ("new", _h("new"))
    # The old raw text was hashed in place; the re-added raw column is NULL.
    assert con.execute(
        "SELECT query, query_hash FROM searches WHERE query_hash = ?", (_h("raw"),)
    ).fetchone() == (None, _h("raw"))


def test_retention_purge_removes_expired_rows_only(db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Retention: rows older than TELEMETRY_RETENTION_DAYS are deleted by
    # purge_expired() — writes themselves never purge (the daily/init cadence
    # owns that), so a stale row survives between writes until the reaper runs.
    monkeypatch.setattr(fl, "TELEMETRY_RETENTION_DAYS", 90)
    fl.log_search("old", rewritten_query="o", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)
    con = sqlite3.connect(db)
    con.execute("UPDATE searches SET ts = '2000-01-01T00:00:00+00:00'")
    con.commit()
    con.close()
    fl.log_search("new", rewritten_query="n", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)
    assert len(_rows(db)) == 2  # writes don't prune

    assert fl.purge_expired() == 1  # the 2000 row is gone, the fresh one stays
    rows = sqlite3.connect(db).execute("SELECT query FROM searches").fetchall()
    assert rows == [("new",)]


def test_retention_zero_keeps_forever(db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 0 days disables the purge entirely — and 0 is the shipped default:
    # dictionary queries and hashed feedback are low-sensitivity, so rows are
    # kept forever unless an operator opts into a window via the env var.
    monkeypatch.setattr(fl, "TELEMETRY_RETENTION_DAYS", 0)
    fl.log_search("old", rewritten_query="o", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)
    con = sqlite3.connect(db)
    con.execute("UPDATE searches SET ts = '2000-01-01T00:00:00+00:00'")
    con.commit()
    con.close()
    assert fl.purge_expired() == 0
    assert len(_rows(db)) == 1


def _broken_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A monitoring DB path whose parent is a *file* — mkdir always fails, so
    every writer raises sqlite3.OperationalError before touching any table."""
    parent = tmp_path / "blocker"
    parent.write_text("not a directory")
    monkeypatch.setattr(fl, "MONITORING_DB", parent / "sub" / "reikun.db")
    monkeypatch.setattr(fl, "_initialised", False)


def test_broken_sqlite_sink_degrades_instead_of_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Telemetry decorates the request — a sink it can't write to must come
    back as None ('not recorded'), never raise: an unwritable SQLite would
    otherwise 500 successful /search, /explain and /feedback calls."""
    _broken_db(tmp_path, monkeypatch)
    sink = _SqliteTelemetry()
    assert sink.search("q", rewritten_query="q", rewrite_method="none", mode="auto",
                       num_results=1, result_count=0, top_result=None, latency_ms=1) is None
    assert sink.feedback("search", None, 1, "q") is None
    assert sink.kanji_lookup("日", source="test") is None
    assert sink.explanation("雨です", "N5", model="m", latency_ms=1, ok=True) is None


def test_broken_sqlite_sink_logs_one_json_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The dedicated telemetry logger emits only JSON lines (its handler prints
    # bare messages, so anything plain-text would corrupt the line stream).
    _broken_db(tmp_path, monkeypatch)
    captured: list[str] = []
    monkeypatch.setattr(telemetry._log, "warning", lambda line: captured.append(line))
    _SqliteTelemetry().feedback("search", None, 1)
    assert len(captured) == 1
    event = json.loads(captured[0])
    assert event["event"] == "telemetry_error"
    assert event["method"] == "feedback"
    assert event["error"]
