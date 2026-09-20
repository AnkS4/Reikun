"""
LLM-powered, JLPT-level-calibrated grammar explanations via Cohere.

Reads COHERE_API_KEY from .env (or the environment). Two prompt variants are
kept side by side so eval/eval.py --llm can compare them; the app uses the
level-aware one (see eval/results/llm_eval.md).

Level calibration is grounded in the JLPT's own level descriptions and the
commonly-cited kanji-count estimates (JLPT stopped publishing official
vocab/kanji lists in 2010, but exam-derived estimates are consistent across
independent sources): N5/N4 are explicitly "basic Japanese mainly learned in
class" (JLPT's own wording) and benefit from plain English and analogies;
N3 is the acknowledged bridging level where standard terminology gets
introduced; N2/N1 assume real-world fluency, so explanations there should
read as notes between competent speakers, not lessons — concise, precise,
nuance-focused. `_LEVEL` below encodes that progression explicitly (style,
target word count, bullet range) instead of applying one flat length/tone
ceiling to every level, which was the previous version's core gap.
"""

import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

import cohere

from app.config import COHERE_MODEL

_LEAKED_SPECIAL_TOKEN = re.compile(r"<\|[^|]*\|>.*", re.DOTALL)

JLPT_LEVELS = ("N5", "N4", "N3", "N2", "N1")


@dataclass(frozen=True)
class LevelConfig:
    desc: str  # learner profile, injected into the prompt
    style: str  # tone/depth instruction, injected into the system prompt
    bullets: str  # e.g. "4-6"
    words: int  # target word ceiling for this level
    max_tokens: int  # response token ceiling (thinking + text)


_LEVEL: dict[str, LevelConfig] = {
    "N5": LevelConfig(
        desc="absolute beginner — knows hiragana, katakana, ~100 kanji, only は/が/を/です-level grammar",
        style=(
            "Use plain, everyday English with no jargon. Briefly define any grammar term the "
            "first time you use it, in your own words (e.g. \"particle — a small word marking "
            "the noun's role\"). Include one short comparison to a similar English construction "
            "where it genuinely clarifies the pattern."
        ),
        bullets="4-6",
        words=280,
        max_tokens=950,
    ),
    "N4": LevelConfig(
        desc="beginner — knows ~300 kanji, basic verb conjugations, simple sentence patterns",
        style=(
            "Use mostly plain English. You may name a grammar form (e.g. \"te-form\"), but "
            "briefly say what it does the first time. A short English comparison is fine but "
            "not required."
        ),
        bullets="4-5",
        words=220,
        max_tokens=800,
    ),
    "N3": LevelConfig(
        desc="intermediate — knows ~650 kanji, can read everyday texts with some difficulty",
        style=(
            "Use standard grammar terminology (て-form, potential form, conditional, etc.) "
            "without redefining basics. Briefly note any nuance that distinguishes this pattern "
            "from a similar one the learner may already know."
        ),
        bullets="3-5",
        words=170,
        max_tokens=650,
    ),
    "N2": LevelConfig(
        desc="upper-intermediate — knows ~1000 kanji, reads most Japanese with a dictionary",
        style=(
            "Assume comfort with standard grammar terminology — do not define basic terms. "
            "Be efficient: focus on nuance, formality level, and why this construction was used "
            "over a close alternative."
        ),
        bullets="3-4",
        words=120,
        max_tokens=550,
    ),
    "N1": LevelConfig(
        desc="advanced — knows 2000+ kanji, understands complex and nuanced Japanese",
        style=(
            "Be maximally concise and precise, as if writing a note to a fluent peer. Use exact "
            "linguistic terminology with no definitions. Skip anything an N2 speaker would "
            "already know — cover only subtle nuance, register, or literary/rhetorical effect."
        ),
        bullets="2-4",
        words=90,
        max_tokens=450,
    ),
}

_BASE_RULES = """\
You are a Japanese language teacher explaining grammar to a student at a \
specific JLPT level.

Rules that apply regardless of level:
- Bold the grammar pattern name on each bullet: **〜ている** → explanation.
- Do NOT repeat the sentence or its translation.
- Focus on grammar patterns, not vocabulary.
- Output Markdown bullet points only — no preamble, no closing summary.\
"""

GENERIC_SYSTEM = """\
You are a Japanese language teacher. Explain the grammar of the given
sentence in concise Markdown bullet points (3–6 bullets, under 200 words).
Bold the grammar pattern name on each bullet. Do not repeat the sentence or
its translation. Focus on grammar, not vocabulary.\
"""


def level_aware_system(jlpt_level: str) -> str:
    """Build a system prompt whose depth, tone, and length scale with
    `jlpt_level` — N5 gets more room and plain-English scaffolding, N1 gets
    a hard, terse ceiling. Falls back to N3 (the bridging-level default) if
    an unrecognised level string slips through."""
    cfg = _LEVEL.get(jlpt_level, _LEVEL["N3"])
    return (
        f"{_BASE_RULES}\n\n"
        f"Student level: {jlpt_level} ({cfg.desc}).\n"
        f"Depth and tone: {cfg.style}\n"
        f"Length: {cfg.bullets} bullets, {cfg.words} words maximum — treat this as a hard "
        f"ceiling, not a target to fill."
    )


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
    thinking_budget: int = 150,
    max_tokens: int = 900,
    retries: int = 3,
    **kwargs,
) -> str:
    """
    Single-turn chat completion; returns the concatenated text blocks (reasoning blocks dropped).

    Thinking is always left *enabled* — this model intermittently raises a
    spurious 422 INVALID_TOOL_GENERATION when thinking is disabled, even
    with no tools configured — but `thinking_budget` caps how many tokens it
    may spend reasoning, which keeps free-tier token usage low without
    reintroducing that flakiness. `max_tokens` bounds the whole response
    (thinking + text); callers should pass a per-level ceiling with enough
    headroom above `thinking_budget` for the target word count (see
    `LevelConfig.max_tokens`).

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


def level_aware_prompt(sentence: str, english: str, jlpt_level: str) -> str:
    cfg = _LEVEL.get(jlpt_level, _LEVEL["N3"])
    return (
        f"Explain the Japanese grammar patterns for a {jlpt_level} learner ({cfg.desc}).\n\n"
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

    level_aware=True (default, used by the app) calibrates both the *depth*
    (plain English + analogies at N5, terse jargon at N1) and the *length*
    (per-level word ceiling, see `_LEVEL`) to `jlpt_level`. False uses the
    one-size-fits-all baseline prompt (fixed ~200-word cap for every level)
    — kept only for eval/eval.py --llm's level-aware-vs-generic comparison.
    """
    if level_aware:
        cfg = _LEVEL.get(jlpt_level, _LEVEL["N3"])
        return chat(
            level_aware_system(jlpt_level),
            level_aware_prompt(sentence, english, jlpt_level),
            model=model,
            thinking_budget=150,
            max_tokens=cfg.max_tokens,
        )
    return chat(GENERIC_SYSTEM, generic_prompt(sentence, english), model=model, thinking_budget=150, max_tokens=900)


def explain_grammar_stream(
    sentence: str,
    english: str,
    jlpt_level: str = "N5",
    *,
    model: str = COHERE_MODEL,
) -> Iterator[str]:
    """
    Generator variant of `explain_grammar` for `st.write_stream` / SSE.

    Yields answer text chunks as Cohere streams them (reasoning blocks are
    dropped). Stream creation retries via `_with_retries`; if the stream
    fails before any text was emitted, falls back to the blocking
    `explain_grammar` (which has the same retry/backoff) and yields its
    result as a single chunk. Once text has been emitted, errors propagate —
    partial output has already been shown and can't be safely retried.
    """
    cfg = _LEVEL.get(jlpt_level, _LEVEL["N3"])
    thinking_budget = 150
    emitted = False
    try:
        stream = _with_retries(
            lambda: cohere_client().chat_stream(
                model=model,
                messages=[{"role": "system", "content": level_aware_system(jlpt_level)},
                          {"role": "user", "content": level_aware_prompt(sentence, english, jlpt_level)}],
                thinking={"type": "enabled", "token_budget": thinking_budget},
                max_tokens=cfg.max_tokens,
            ),
            retries=3,
        )
        for event in stream:
            if event.type == "content-delta":
                text = getattr(getattr(getattr(event.delta, "message", None), "content", None), "text", None)
                if text:
                    emitted = True
                    yield text
            elif event.type == "message-end" and getattr(event.delta, "finish_reason", None) == "MAX_TOKENS":
                yield "\n\n*(truncated)*"
    except Exception:
        if emitted:
            raise
        yield explain_grammar(sentence, english, jlpt_level, model=model)
