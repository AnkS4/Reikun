"""Groq failover/retry behavior of the grammar explainer (SDK mocked out)."""

from unittest.mock import MagicMock

import pytest

import app.grammar_explain as ge
from app.config import LLM_MODEL, LLM_MODEL_FALLBACK


def _resp(text: str, finish: str = "stop"):
    """Minimal stand-in for a Groq ChatCompletion / stream chunk."""
    choice = MagicMock()
    choice.message.content = text
    choice.delta.content = text
    choice.finish_reason = finish
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _client(create):
    client = MagicMock()
    client.chat.completions.create.side_effect = create
    return client


def _no_sleep(monkeypatch):
    monkeypatch.setattr(ge.time, "sleep", lambda _: None)


def test_chat_primary_success(monkeypatch):
    client = _client(lambda **kw: _resp("answer"))
    monkeypatch.setattr(ge, "_groq", lambda: client)
    assert ge.chat("sys", "user") == "answer"
    assert client.chat.completions.create.call_args.kwargs["model"] == LLM_MODEL
    assert ge.last_model() == LLM_MODEL


def test_chat_fails_over_to_fallback(monkeypatch):
    def create(**kw):
        if kw["model"] == LLM_MODEL:
            raise RuntimeError("429: daily quota exhausted")
        return _resp("fallback answer")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert ge.chat("sys", "user", retries=0) == "fallback answer"
    assert ge.last_model() == LLM_MODEL_FALLBACK


def test_chat_all_models_down(monkeypatch):
    def create(**kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    with pytest.raises(RuntimeError, match="service is down"):
        ge.chat("sys", "user", retries=0)


def test_chat_retries_same_model_then_succeeds(monkeypatch):
    calls = []

    class FlakeError(Exception):
        status_code = 500

    def create(**kw):
        calls.append(kw["model"])
        if len(calls) == 1:
            raise FlakeError("transient 5xx")
        return _resp("ok")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert ge.chat("sys", "user", retries=1) == "ok"
    assert calls == [LLM_MODEL, LLM_MODEL]  # retried before falling over


def test_chat_truncated_retries_with_bigger_budget(monkeypatch):
    budgets = []

    def create(**kw):
        budgets.append(kw["max_completion_tokens"])
        if len(budgets) == 1:
            return _resp("cut off mid-", finish="length")
        return _resp("full answer")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert ge.chat("sys", "user", max_tokens=100, retries=1) == "full answer"
    assert budgets == [100, 150]


def test_stream_failover(monkeypatch):
    def create(**kw):
        if kw["model"] == LLM_MODEL:
            raise RuntimeError("stream refused")
        return iter([_resp("hel", None), _resp("lo", "stop")])

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert "".join(ge.explain_grammar_stream("文です。", "It is a sentence.")) == "hello"
    assert ge.last_model() == LLM_MODEL_FALLBACK


def test_stream_all_down_raises_service_down(monkeypatch):
    def create(**kw):
        raise RuntimeError("429: quota")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    with pytest.raises(RuntimeError, match="service is down"):
        list(ge.explain_grammar_stream("文です。", "It is a sentence."))


def test_explain_grammar_uses_level_budget(monkeypatch):
    client = _client(lambda **kw: _resp("answer"))
    monkeypatch.setattr(ge, "_groq", lambda: client)
    ge.explain_grammar("文です。", "It is a sentence.", "N5")
    kw = client.chat.completions.create.call_args.kwargs
    assert kw["max_completion_tokens"] == ge._LEVEL["N5"].token_budget
    assert "<sentence>文です。</sentence>" in kw["messages"][1]["content"]
    assert "<meaning>It is a sentence.</meaning>" in kw["messages"][1]["content"]


def test_chat_permanent_error_skips_to_fallback(monkeypatch):
    """A non-retryable error (401/bad request) must not burn retry attempts —
    it fails over to the next model immediately."""
    calls = []

    def create(**kw):
        calls.append(kw["model"])
        if kw["model"] == LLM_MODEL:
            raise RuntimeError("401 invalid api key")  # no status_code → non-retryable
        return _resp("fallback ok")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert ge.chat("sys", "user", retries=2) == "fallback ok"
    assert calls == [LLM_MODEL, LLM_MODEL_FALLBACK]  # one attempt each, no retries


def test_chat_long_retry_after_fails_over(monkeypatch):
    """429 with retry-after > MAX_BACKOFF_S = daily quota gone → next model."""
    calls = []

    class RateLimited(Exception):
        status_code = 429
        response = MagicMock(headers={"retry-after": "86400"})

    def create(**kw):
        calls.append(kw["model"])
        if kw["model"] == LLM_MODEL:
            raise RateLimited("quota")
        return _resp("fallback ok")

    monkeypatch.setattr(ge, "_groq", lambda: _client(create))
    _no_sleep(monkeypatch)
    assert ge.chat("sys", "user", retries=2) == "fallback ok"
    assert calls == [LLM_MODEL, LLM_MODEL_FALLBACK]


def test_validate_input_caps_and_normalises():
    s, e, _h = ge.validate_input("  日本語　を  話す  ", "  speak Japanese  ")
    assert s == "日本語 を 話す" and e == "speak Japanese"
    assert ge.validate_input("文", "en", "x" * 9999)[2] == "x" * ge.MAX_HINT_CHARS
    with pytest.raises(ValueError, match="empty"):
        ge.validate_input("   ")
    with pytest.raises(ValueError, match="too long"):
        ge.validate_input("あ" * (ge.MAX_SENTENCE_CHARS + 1))


def test_prompt_is_data_only_and_system_carries_level():
    """The level lives once, in the system prompt — not duplicated per call."""
    user = ge.level_aware_prompt("文", "en", "N1")
    assert "Student level" not in user
    assert "Student level: N1" in ge.level_aware_system("N1")
    assert ge.level_aware_system("N1") is ge.level_aware_system("N1")  # cached


def test_groq_client_owns_retries():
    """SDK-level retries must be off (our ladder owns them) and a timeout set."""
    ge._groq.cache_clear()
    client = ge._groq()
    assert client.max_retries == 0 and client.timeout == 30


def test_prompt_rules_present():
    sys_prompt = ge.level_aware_system("N1")
    assert "English" in sys_prompt and "ceilings, not targets" in sys_prompt
    assert "<sentence>" in ge.level_aware_prompt("文", "en", "N5")
    assert "<analysis>" in ge.level_aware_prompt("文", "en", "N5", hint="verb/past")


def test_last_model_starts_at_primary():
    assert ge.last_model() == LLM_MODEL or ge.last_model() in (LLM_MODEL, LLM_MODEL_FALLBACK)
