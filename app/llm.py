"""
OpenAI-compatible LLM providers for grammar explanations / rewrites.

Switch with one env line — `LLM_PROVIDER=nebius` (or groq / gemini / cohere).
Each provider uses the same Chat Completions shape via the `openai` SDK;
only the base URL, API key env name, and default model IDs differ.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cache


@dataclass(frozen=True, slots=True)
class Provider:
    """One OpenAI-compatible chat backend."""

    name: str
    base_url: str
    api_key_env: str
    default_model: str
    default_fallback: str
    # Some hosts (e.g. gpt-oss) accept reasoning_effort; others reject it.
    reasoning: bool = False
    # Newer OpenAI-style APIs prefer max_completion_tokens; most compat layers want max_tokens.
    token_param: str = "max_tokens"


# Defaults match production (groq) and local/llm_compare baselines; override
# per deploy with LLM_MODEL / LLM_MODEL_FALLBACK without changing provider.
PROVIDERS: dict[str, Provider] = {
    "groq": Provider(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        default_model="openai/gpt-oss-120b",
        default_fallback="openai/gpt-oss-20b",
        reasoning=True,
        token_param="max_completion_tokens",
    ),
    # Gemini Flash's free tier allows only 20 requests/day — too small to
    # serve as a fallback, so Lite is the only default Gemini model.
    "gemini": Provider(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-3.5-flash-lite",
        default_fallback="",
    ),
    "cohere": Provider(
        name="cohere",
        base_url="https://api.cohere.ai/compatibility/v1",
        api_key_env="COHERE_API_KEY",
        default_model="command-a-plus-05-2026",
        default_fallback="command-r-plus-08-2024",
    ),
    "nebius": Provider(
        name="nebius",
        base_url="https://api.tokenfactory.nebius.com/v1/",
        api_key_env="NEBIUS_API_KEY",
        # Catalog IDs are exact (case-sensitive): Nano uses NVIDIA- prefix; Super is lowercase.
        default_model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        default_fallback="nvidia/nemotron-3-super-120b-a12b",
    ),
}


@cache
def provider() -> Provider:
    """Active provider from `LLM_PROVIDER` (validated in config)."""
    from app.config import LLM_PROVIDER

    return PROVIDERS[LLM_PROVIDER]


def api_key() -> str | None:
    """API key for the active provider, or None if unset."""
    from app.config import COHERE_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, LLM_PROVIDER, NEBIUS_API_KEY

    return {
        "groq": GROQ_API_KEY,
        "gemini": GEMINI_API_KEY,
        "cohere": COHERE_API_KEY,
        "nebius": NEBIUS_API_KEY,
    }[LLM_PROVIDER]


@cache
def client():
    """Lazily built OpenAI client pointed at the active provider.

    max_retries=0: grammar_explain owns the retry/failover ladder. timeout=30
    so a hung request cannot pin an SSE connection for minutes.
    """
    from openai import OpenAI

    p = provider()
    key = api_key()
    if not key:
        raise RuntimeError(
            f"{p.api_key_env} is not set (LLM_PROVIDER={p.name}). "
            f"Add it to .env or switch LLM_PROVIDER."
        )
    # Optional override for forks / regional endpoints without a new provider entry.
    base = (os.getenv("LLM_BASE_URL") or "").strip() or p.base_url
    return OpenAI(api_key=key, base_url=base, max_retries=0, timeout=30.0)
