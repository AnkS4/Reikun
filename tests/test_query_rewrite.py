"""Query-rewrite tests that do not touch a live LLM or Qdrant."""

import pytest

import app.grammar_explain as grammar_explain
import app.query_rewrite as query_rewrite


@pytest.fixture(autouse=True)
def _clear_llm_cache():
    query_rewrite.llm_rewrite.cache_clear()
    yield
    query_rewrite.llm_rewrite.cache_clear()


def _patch_chat(monkeypatch: pytest.MonkeyPatch, reply: str, calls: list[str] | None = None):
    def fake_chat(system: str, user: str, **kwargs) -> str:
        if calls is not None:
            calls.append(user)
        return reply

    monkeypatch.setattr(grammar_explain, "chat", fake_chat)


def test_parse_pivot_json_tolerates_fences_and_prose():
    raw = """```json
    {"english":"supermarket","japanese":["スーパー","スーパーマーケット","コンビニ"]}
    ```"""
    assert query_rewrite._parse_llm_rewrite(raw, "fallback") == (
        "supermarket",
        ("スーパー", "スーパーマーケット", "コンビニ"),
    )


def test_parse_pivot_rejects_romaji_and_keeps_english_fallback():
    assert query_rewrite._parse_llm_rewrite("market", "market") == ("market", ())
    assert query_rewrite._parse_llm_rewrite(
        '{"english":"cat","japanese":["neko","猫"]}', "cat"
    ) == ("cat", ("猫",))
    assert query_rewrite._parse_llm_rewrite(
        '{"english":"cat","japanese":["猫(ねこ)"]}', "cat"
    ) == ("cat", ("猫",))


def test_heuristic_short_circuits_one_word_lookups(monkeypatch):
    calls: list[str] = []
    _patch_chat(monkeypatch, "{}", calls)
    rw = query_rewrite.rewrite_query("what is the word for weather", mode="auto")
    assert rw.query == "weather"
    assert rw.method == "heuristic"
    assert rw.japanese == ()
    assert calls == []


def test_heuristic_phrase_is_sent_to_llm(monkeypatch):
    calls: list[str] = []
    _patch_chat(
        monkeypatch,
        '{"english":"tired","japanese":["疲れる","疲れている"]}',
        calls,
    )
    rw = query_rewrite.rewrite_query("a word for feeling very tired", mode="auto")
    assert rw.query == "tired"
    assert rw.method == "llm"
    assert rw.japanese == ("疲れる", "疲れている")
    assert calls == ["a word for feeling very tired"]


def test_three_word_description_gets_a_pivot(monkeypatch):
    calls: list[str] = []
    _patch_chat(monkeypatch, '{"english":"puppy","japanese":["子犬"]}', calls)
    rw = query_rewrite.rewrite_query("a baby dog", mode="auto")
    assert rw.query == "puppy"
    assert rw.japanese == ("子犬",)
    assert calls == ["a baby dog"]


def test_llm_failure_falls_back_to_heuristic(monkeypatch):
    def failing_chat(*args, **kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(grammar_explain, "chat", failing_chat)
    rw = query_rewrite.rewrite_query("a word for feeling very tired", mode="auto")
    assert rw.query == "feeling very tired"
    assert rw.method == "heuristic"
    assert rw.japanese == ()


def test_malformed_llm_reply_falls_back_to_heuristic(monkeypatch):
    _patch_chat(monkeypatch, "")
    rw = query_rewrite.rewrite_query("a word for feeling very tired", mode="auto")
    assert rw.query == "feeling very tired"
    assert rw.method == "heuristic"
    assert rw.japanese == ()


def test_heuristic_mode_never_calls_the_llm(monkeypatch):
    calls: list[str] = []
    _patch_chat(monkeypatch, "{}", calls)
    rw = query_rewrite.rewrite_query("a word for feeling very tired", mode="heuristic")
    assert rw.query == "feeling very tired"
    assert rw.method == "heuristic"
    assert rw.japanese == ()
    assert calls == []


def test_japanese_input_is_not_pivoted(monkeypatch):
    calls: list[str] = []
    _patch_chat(monkeypatch, "{}", calls)
    rw = query_rewrite.rewrite_query("猫", mode="auto")
    assert rw.query == "猫"
    assert rw.method == "none"
    assert rw.japanese == ()
    assert calls == []
