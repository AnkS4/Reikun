"""
Query rewriting before retrieval.

The knowledge base is indexed by short dictionary glosses ("to eat", "sky"),
so natural-language questions retrieve poorly as-is. Two layers:

    1. heuristic  – cheap regex normalisation ("how do you say X in japanese" → "X")
    2. llm        – Cohere rewrites longer descriptive queries into a 1–3 word
                    gloss; only used when the heuristic layer did not simplify
                    the query and the query still looks like a sentence.

`rewrite_query()` returns the rewritten string plus which layer produced it.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from app.config import QUERY_REWRITE

_JAPANESE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
_PATTERNS = [
    re.compile(r"^(?:how (?:do|would|can) (?:you|i|we) say|how to say)\s+(?P<x>.+?)(?:\s+in japanese)?$"),
    re.compile(r"^(?:what(?:'s| is) (?:the )?(?:japanese )?(?:word|term|verb|noun|adjective) for)\s+(?P<x>.+)$"),
    re.compile(r"^(?:japanese (?:word |term )?for|word for|meaning of|translate)\s+(?P<x>.+)$"),
    re.compile(r"^(?:a|an|the)\s+(?:word|term)\s+(?:for|meaning|that means)\s+(?P<x>.+)$"),
]
_TRAILING = re.compile(r"[\s?!.。、]+$")
_ARTICLES = re.compile(r"^(?:a|an|the)\s+")

_LLM_SYSTEM = """\
You convert a learner's English description or question into the shortest
English dictionary gloss that a Japanese-English dictionary would list.
Respond with 1 to 3 words only, lowercase, no punctuation, no explanation.
Write verbs as "to" plus the verb, e.g. "when you arrive late" becomes
"to be late". "the vehicle that flies in the sky" becomes "airplane".\
"""


@dataclass(frozen=True)
class Rewrite:
    original: str
    query: str
    method: str  # none | heuristic | llm

    @property
    def changed(self) -> bool:
        return self.method != "none"


def is_japanese(text: str) -> bool:
    return bool(_JAPANESE.search(text))


def normalise(query: str) -> str:
    """Trim, drop trailing punctuation, lowercase English (Japanese left untouched)."""
    q = _TRAILING.sub("", query.strip())
    return q if is_japanese(q) else q.lower()


def heuristic_rewrite(query: str) -> str | None:
    """Strip question scaffolding ('how do you say X in japanese' → 'x'); None if no pattern matched."""
    q = normalise(query)
    if is_japanese(q):
        return None
    for pat in _PATTERNS:
        if m := pat.match(q):
            return _TRAILING.sub("", _ARTICLES.sub("", m.group("x").strip())) or None
    return None


@lru_cache(maxsize=512)
def llm_rewrite(query: str) -> str:
    from app.grammar_explain import chat  # lazy: keeps cohere optional for retrieval-only use

    out = chat(_LLM_SYSTEM, query, thinking_budget=40, max_tokens=150).strip().strip('"').lower()
    out = _TRAILING.sub("", out)
    return out if 0 < len(out.split()) <= 4 else query


def rewrite_query(query: str, mode: str | None = None) -> Rewrite:
    """
    mode: 'off' | 'heuristic' | 'auto' (heuristic, then LLM for sentence-like queries).
    Defaults to the QUERY_REWRITE environment setting.
    """
    mode = (mode or QUERY_REWRITE).lower()
    original = query.strip()
    if mode == "off" or not original:
        return Rewrite(original, original, "none")

    if (q := heuristic_rewrite(original)) is not None:
        return Rewrite(original, q, "heuristic")

    q = normalise(original)
    if mode == "auto" and not is_japanese(q) and len(q.split()) >= 4:
        try:
            rewritten = llm_rewrite(q)
        except Exception:
            rewritten = q
        if rewritten != q:
            return Rewrite(original, rewritten, "llm")
    return Rewrite(original, q, "none")
