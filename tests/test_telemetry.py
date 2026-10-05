"""Telemetry: searches keep raw text, feedback/explanations stay hashed."""

import hashlib
import sqlite3
from pathlib import Path

import pytest

import scripts.feedback_log as fl
from app.telemetry import _h


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


def test_rows_kept_forever(db: Path) -> None:
    fl.log_search("old", rewritten_query="o", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)
    con = sqlite3.connect(db)
    con.execute("UPDATE searches SET ts = '2000-01-01T00:00:00+00:00'")
    con.commit()
    con.close()
    fl.log_search("new", rewritten_query="n", rewrite_method="none", mode="auto",
                  num_results=1, result_count=1, top_result=None, latency_ms=1)
    assert len(_rows(db)) == 2
