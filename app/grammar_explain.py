"""
LLM-powered, JLPT-level-calibrated grammar explanations via Cohere.

Reads COHERE_API_KEY from .env (or the environment). Two prompt variants are
kept side by side so eval/llm_eval.py can compare them; the app uses the
level-aware one (see eval/results/llm_eval.md).
"""

import re
import time
from functools import lru_cache

import cohere

from app.config import COHERE_MODEL

_LEAKED_SPECIAL_TOKEN = re.compile(r"<\|[^|]*\|>.*", re.DOTALL)

JLPT_LEVELS = ("N5", "N4", "N3", "N2", "N1")

# Human-readable JLPT level descriptions used inside the prompt
_JLPT_DESC: dict[str, str] = {
    "N5": "absolute beginner — knows hiragana, katakana, ~100 kanji, very basic grammar (は/が/を/です)",
    "N4": "beginner — knows ~300 kanji, basic verb conjugations, simple sentence patterns",
    "N3": "intermediate — knows ~650 kanji, can read everyday texts with some difficulty",
    "N2": "upper-intermediate — knows ~1000 kanji, reads most Japanese with a dictionary",
    "N1": "advanced — knows 2000+ kanji, understands complex and nuanced Japanese",
}

LEVEL_AWARE_SYSTEM = """\
You are a Japanese language teacher who explains Japanese grammar concisely
and at exactly the right difficulty for the student's JLPT level.

Rules:
- Use 3–6 bullet points maximum.
- Bold the grammar pattern name on each bullet: **〜ている** → explanation.
- For N5/N4: use plain English, avoid jargon, give an English analogy.
- For N3: introduce standard grammar terminology (て-form, potential form …).
- For N2/N1: use precise linguistic terms; mention nuance and formality.
- Do NOT repeat the sentence or its translation.
- Keep the total response under 200 words.
- Focus on grammar patterns, not vocabulary.\
"""

GENERIC_SYSTEM = """\
You are a Japanese language teacher. Explain the grammar of the given
sentence in concise Markdown bullet points (3–6 bullets, under 200 words).
Bold the grammar pattern name on each bullet. Do not repeat the sentence or
its translation. Focus on grammar, not vocabulary.\
"""


@lru_cache(maxsize=1)
def cohere_client() -> cohere.ClientV2:
    """Lazily instantiated Cohere client (reads COHERE_API_KEY from env)."""
    return cohere.ClientV2()


def _with_retries(call, retries: int, backoff: float = 7.0):
    """
    Retry `call()` on transient Cohere errors:
      - 429 TooManyRequestsError (trial keys are capped at 10 calls/min) →
        wait a full `backoff` seconds so the per-minute window clears
      - 422 UnprocessableEntityError (intermittent server-side flake on this
        model with thinking disabled, even with no tools configured) → retry immediately
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return call()
        except cohere.TooManyRequestsError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff)
        except (cohere.UnprocessableEntityError, RuntimeError) as exc:
            last_exc = exc
    raise last_exc


def chat(
    system: str,
    user: str,
    *,
    model: str = COHERE_MODEL,
    thinking_budget: int = 120,
    max_tokens: int = 600,
    retries: int = 3,
    **kwargs,
) -> str:
    """
    Single-turn chat completion; returns the concatenated text blocks (reasoning blocks dropped).

    Thinking is always left *enabled* — this model intermittently raises a
    spurious 422 INVALID_TOOL_GENERATION when thinking is disabled, even
    with no tools configured — but `thinking_budget` caps how many tokens it
    may spend reasoning, which keeps free-tier token usage low without
    reintroducing that flakiness. Tune per call site: short structured
    outputs (query rewriting, judging) need a small budget; multi-bullet
    explanations need more room. `max_tokens` bounds the whole response
    (thinking + text) and should leave enough headroom above the budget for
    the actual answer.

    If generation is cut off by `max_tokens` mid-answer, the model can spill
    raw reasoning/channel markers (e.g. "<|channel|>...") into the text
    block instead of a clean answer; this is treated as a retryable failure
    (with a larger budget) rather than returned to the caller.
    """
    budget = max_tokens
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = cohere_client().chat(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                thinking={"type": "enabled", "token_budget": thinking_budget},
                max_tokens=budget,
                **kwargs,
            )
            text = "".join(item.text for item in response.message.content or [] if item.type == "text").strip()
            if text and not _LEAKED_SPECIAL_TOKEN.search(text) and response.finish_reason != "MAX_TOKENS":
                return text
            last_exc = RuntimeError(f"Truncated/malformed response (finish_reason={response.finish_reason})")
            budget = int(budget * 1.5)  # give the retry more room to finish cleanly
        except cohere.TooManyRequestsError as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(7.0)
        except cohere.UnprocessableEntityError as exc:
            last_exc = exc
    raise last_exc


def rerank(query: str, documents: list[str], top_n: int, *, model: str, retries: int = 8):
    """Cohere Rerank with retry/backoff on trial-key rate limits."""
    return _with_retries(
        lambda: cohere_client().rerank(model=model, query=query, documents=documents, top_n=top_n), retries
    )


def level_aware_prompt(sentence: str, english: str, jlpt_level: str) -> str:
    desc = _JLPT_DESC.get(jlpt_level, "intermediate learner")
    return (
        f"Explain the Japanese grammar patterns for a {jlpt_level} learner ({desc}).\n\n"
        f"Sentence: {sentence}\nMeaning:  {english}"
    )


def generic_prompt(sentence: str, english: str, jlpt_level: str = "") -> str:
    return f"Explain the Japanese grammar patterns.\n\nSentence: {sentence}\nMeaning:  {english}"


def explain_grammar(
    sentence: str,
    english: str,
    jlpt_level: str = "N5",
    *,
    model: str = COHERE_MODEL,
    level_aware: bool = True,
) -> str:
    """
    Generate a grammar explanation for `sentence`.

    level_aware=True (default, used by the app) calibrates the explanation to
    `jlpt_level`; False uses the one-size-fits-all baseline prompt.
    Returns Markdown bullet points (~100–200 words).
    """
    # 200-word cap in the prompt is ~280 tokens; token_budget=150 covers
    # reasoning for even N1-level sentences (see eval/results/llm_eval.md).
    kwargs = dict(model=model, thinking_budget=150, max_tokens=900)
    if level_aware:
        return chat(LEVEL_AWARE_SYSTEM, level_aware_prompt(sentence, english, jlpt_level), **kwargs)
    return chat(GENERIC_SYSTEM, generic_prompt(sentence, english), **kwargs)
