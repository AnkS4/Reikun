"""Retrieval routing for the Japanese rewrite pivot (no Qdrant/LLM)."""

import app.retrieval as retrieval
from app.query_rewrite import Rewrite


def _entry(word: str) -> dict:
    return {
        "id": 1,
        "kanji_form": word,
        "reading": word,
        "kanji_forms": [],
        "readings": [],
        "meanings": ["test"],
        "is_common": True,
        "score": 1.0,
    }


def _install_pivot(monkeypatch, calls, result_for):
    monkeypatch.setattr(
        retrieval,
        "rewrite_query",
        lambda query, mode=None: Rewrite(query, "supermarket", "llm", ("スーパー", "スーパーマーケット")),
    )
    monkeypatch.setattr(retrieval, "embed_query", lambda query, **kwargs: ("dense", "sparse"))

    def fake_auto(query, num_results, *, vectors, route):
        calls.append((query, route))
        return result_for(query)

    monkeypatch.setattr(retrieval, "_auto_search", fake_auto)
    retrieval._search_cached.cache_clear()


def test_pivot_uses_the_first_japanese_headword(monkeypatch):
    calls: list[tuple[str, str]] = []
    _install_pivot(monkeypatch, calls, lambda q: [_entry(q)] if q == "スーパー" else [])

    resp = retrieval.search("a place where you buy food", 5, "auto", rewrite_mode="auto")

    assert calls == [("スーパー", "ja")]
    assert resp.rewrite.query == "supermarket"
    assert resp.rewrite.japanese == ("スーパー", "スーパーマーケット")
    assert resp.meta["route"] == "ja"
    assert resp.results[0]["kanji_form"] == "スーパー"


def test_pivot_falls_back_to_english_when_japanese_candidates_are_empty(monkeypatch):
    calls: list[tuple[str, str]] = []
    _install_pivot(
        monkeypatch,
        calls,
        lambda q: [_entry(q)] if q == "supermarket" else [],
    )

    resp = retrieval.search("a place where you buy food", 5, "auto", rewrite_mode="auto")

    assert calls == [("スーパー", "ja"), ("スーパーマーケット", "ja"), ("supermarket", "en_word")]
    assert resp.meta["route"] == "en_word"
    assert resp.results[0]["kanji_form"] == "supermarket"
