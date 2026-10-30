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


# ── _infl_indexed: one schema probe, latched ─────────────────────────────────

def test_infl_indexed_checked_once_per_process(monkeypatch):
    """_exact_filter runs on every search arm, so _infl_indexed must not get
    a fresh get_collection round-trip per call — the schema lookup latches on
    first use (either answer)."""
    calls = 0

    class _FakeCollection:
        payload_schema = ()  # immutable; only truthiness matters to _infl_indexed

    class _FakeClient:
        def get_collection(self, *_a, **_k):
            nonlocal calls
            calls += 1
            return _FakeCollection()

    monkeypatch.setattr(retrieval, "qdrant_client", _FakeClient)
    retrieval._infl_indexed.cache_clear()
    retrieval._exact_filter("食べる")
    retrieval._exact_filter("水")
    assert calls == 1
    retrieval._infl_indexed.cache_clear()


def test_infl_indexed_transport_error_reads_not_indexed(monkeypatch):
    """A Qdrant blip at first use must degrade (conjugation arm off) rather
    than error every search — and the degraded answer is cached too, so Qdrant
    stays out of each query's hot path."""

    class _BlipClient:
        def get_collection(self, *_a, **_k):
            raise RuntimeError("qdrant briefly unreachable")

    monkeypatch.setattr(retrieval, "qdrant_client", _BlipClient)
    retrieval._infl_indexed.cache_clear()
    assert retrieval._infl_indexed() is False
    assert retrieval._infl_indexed() is False
    retrieval._infl_indexed.cache_clear()
