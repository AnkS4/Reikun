"""Tests for the borrowed-words index build (app/loanwords.py) — the scroll,
wf_score ranking and per-language grouping. These drive the real ``_build``
with a stubbed Qdrant client, since the endpoint-level tests elsewhere
monkeypatch ``_loanwords`` and never execute it."""

from __future__ import annotations

import app.loanwords as lw


class _Rec:
    """Minimal stand-in for a qdrant Record: id + payload only."""

    def __init__(self, id: int, payload: dict) -> None:
        self.id = id
        self.payload = payload


class _FakeClient:
    """Serves pre-built pages; asserts the scroll selector is honored."""

    def __init__(self, pages: list[list[_Rec]]) -> None:
        self._pages = pages
        self.calls = 0

    def scroll(self, _collection, scroll_filter=None, limit=0, offset=None,
               with_payload=None, with_vectors=False):
        self.calls += 1
        idx = 0 if offset is None else int(offset)
        if idx >= len(self._pages):
            return [], None
        return self._pages[idx], (idx + 1 if idx + 1 < len(self._pages) else None)


def test_build_ranks_by_wf_score(monkeypatch) -> None:
    """wf_score comes from the scrolled payload and drives the per-language
    order — a missing selector field silently flattens every score to 0.0
    and the listing degenerates to scroll order (regression 2026-11-14)."""
    pages = [[
        _Rec(1, {"reading": "レア", "lsource": [{"lang": "por", "text": "raro"}], "wf_score": 2.0}),
        _Rec(2, {"reading": "パン", "lsource": [{"lang": "por", "text": "pan"}], "wf_score": 5.5}),
        _Rec(3, {"reading": "カステラ", "lsource": [{"lang": "por", "text": "castilla"}], "wf_score": 3.1}),
    ]]
    fake = _FakeClient(pages)
    monkeypatch.setattr(lw, "qdrant_client", lambda: fake)
    idx = lw._build()
    por = idx["por"]
    assert [d["reading"] for d in por] == ["パン", "カステラ", "レア"]
    assert [d["score"] for d in por] == [5.5, 3.1, 2.0]
    # The selector must include wf_score — the ranking's only input.
    assert "wf_score" in lw._PAYLOAD_FIELDS


def test_build_groups_by_every_lsource_lang(monkeypatch) -> None:
    """An entry with sources in two languages appears under each."""
    pages = [[
        _Rec(4, {"reading": "レンズ", "lsource": [
            {"lang": "eng", "text": "lens"}, {"lang": "lat", "text": "lens"}]}),
    ]]
    fake = _FakeClient(pages)
    monkeypatch.setattr(lw, "qdrant_client", lambda: fake)
    idx = lw._build()
    assert set(idx) == {"eng", "lat"}
    assert idx["eng"][0]["reading"] == "レンズ"
    assert idx["lat"][0]["reading"] == "レンズ"


def test_build_dedupes_repeated_lang_within_entry(monkeypatch) -> None:
    """Two lsource items in the same language list the entry once — appended
    per item it would render duplicate cards on the listing page."""
    pages = [[
        _Rec(5, {"reading": "バーゲン", "lsource": [
            {"lang": "ger", "text": "Bargain"}, {"lang": "ger", "text": "bargain"}]}),
    ]]
    fake = _FakeClient(pages)
    monkeypatch.setattr(lw, "qdrant_client", lambda: fake)
    idx = lw._build()
    assert len(idx["ger"]) == 1
    assert idx["ger"][0]["reading"] == "バーゲン"


def test_loanwords_page_slices(monkeypatch) -> None:
    """loanwords_page slices the cached listing and 404s unknown codes."""
    monkeypatch.setattr(lw, "_index", {"por": [{"id": i, "reading": f"r{i}"} for i in range(3)]})
    monkeypatch.setattr(lw, "_loaded_at", lw.time.monotonic())
    page = lw.loanwords_page("por", offset=1, limit=2)
    assert page is not None
    assert page["total"] == 3
    assert [d["id"] for d in page["results"]] == [1, 2]
    assert lw.loanwords_page("zzz") is None
