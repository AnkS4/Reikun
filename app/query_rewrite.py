"""
Query rewriting before retrieval.

The knowledge base is indexed by short dictionary glosses ("to eat", "sky"),
so natural-language questions retrieve poorly as-is. Two layers:

    1. heuristic  - cheap regex normalisation ("how do you say X in japanese" → "X")
    2. llm        - LLM pivots longer descriptive queries to a short English
                    gloss plus ranked Japanese dictionary headwords. The exact
                    Japanese route uses the headwords; the English gloss is
                    the display value and the fallback when no pivot resolves.

`rewrite_query()` returns the rewritten value plus which layer produced it.
"""

import json
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
You are a Japanese-English dictionary editor. Given a learner's English
description or question, return exactly one JSON object and nothing else:
{"english": "<1-3 word English dictionary gloss>", "japanese": ["<Japanese dictionary headword>", ...]}

Rules:
- "english": the shortest natural English gloss, lowercase, no punctuation.
  For a thing, person, or place use a noun; for an action use "to" plus the verb.
- "japanese": 1 to 3 ranked Japanese dictionary headwords, most likely first.
  Use normal kanji/kana, never romaji, readings, or explanations.
- Prefer the everyday word a learner would look up, not a rare, literary, or
  made-up compound.
- Use dictionary forms, not inflected or attributive forms: 静か (not 静かな),
  疲れる (not 疲れた), 美味しい.
- For a feeling or state, use the adjective/verb dictionary form, not a
  nominalized form. For hunger use 空腹 or お腹が空く, not 食欲. For "the day
  after today" use 明日 (明後日 is the day after tomorrow).
- For a place, person, or thing, use the specific common name, not a generic
  category: prefer スーパー over 店 for a place to buy food; 駅 over 停車場.
- For an occasion or momentary/intense feeling of happiness use 嬉しい; 幸せ is
  lasting wellbeing. For casual farewells use じゃあね/バイバイ/またね; reserve
  さようなら for formal goodbyes.
- Use 友達 or 友人 for friends; 親友 means a best/close friend. Use 職場 for a
  workplace; 事務所 is an office/office room.

Examples:
{"english":"supermarket","japanese":["スーパー","スーパーマーケット","コンビニ"]}
{"english":"train station","japanese":["駅","停車場"]}
{"english":"tired","japanese":["疲れる","疲れている"]}
{"english":"delicious","japanese":["美味しい","旨い"]}
{"english":"lonely","japanese":["寂しい","孤独"]}
{"english":"happy","japanese":["嬉しい","幸せ"]}
{"english":"quiet","japanese":["静か","静けさ"]}
{"english":"hungry","japanese":["空腹","お腹が空く"]}
{"english":"casual goodbye","japanese":["じゃあね","またね","バイバイ"]}
{"english":"friend","japanese":["友達","友人"]}
{"english":"workplace","japanese":["職場","仕事場"]}\
"""


@dataclass(frozen=True, slots=True)
class Rewrite:
    original: str
    query: str
    method: str  # none | heuristic | llm
    # Ranked Japanese headwords for the exact `ja` route. `query` stays the
    # English gloss so API/UI/telemetry keep the learner-facing rewrite.
    japanese: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.method != "none"


def is_japanese(text: str) -> bool:
    """Check if text starts with Japanese (for mixed text detection)."""
    if not text:
        return False
    # Strip leading whitespace and check if first character is Japanese
    text = text.lstrip()
    return bool(_JAPANESE.match(text))


_PAREN_TAIL = re.compile(r"\s*\(.*")
_TRAILING_PUNCT = re.compile(r"[,;:.!\s]+$")


def gloss_key(text: str) -> str:
    """
    Normalise a gloss (or query) for exact keyword matching: lowercase, drop
    parenthetical qualifiers ("dog (Canis lupus)" → "dog"), collapse spaces.
    """
    key = _PAREN_TAIL.sub("", text.strip().lower())
    return _TRAILING_PUNCT.sub("", " ".join(key.split()))


def gloss_keys(gloss: str) -> set[str]:
    """
    Match keys for one gloss: the normalised form plus, for verb glosses, the
    infinitive-stripped variant ("to eat" also matches "eat").
    """
    key = gloss_key(gloss)
    if not key:
        return set()
    keys = {key}
    if key.startswith("to "):
        keys.add(key[3:])
    return keys


def normalise(query: str) -> str:
    """Trim, drop trailing punctuation, lowercase English (Japanese left untouched)."""
    q = _TRAILING.sub("", query.strip())
    return q if is_japanese(q) else q.lower()


def _clean_english(value: object) -> str:
    """Sanitise the LLM's English gloss; empty when it isn't gloss-shaped."""
    text = normalise(str(value or "").strip().strip('"'))
    text = _TRAILING.sub("", text)
    return text if 0 < len(text.split()) <= 4 else ""


def _clean_japanese(value: object) -> tuple[str, ...]:
    """Parse the LLM's Japanese candidates into deduped, plausible headwords."""
    if isinstance(value, str):
        value = re.split(r"[|,、;\n]+", value)
    if not isinstance(value, (list, tuple)):
        return ()
    out: list[str] = []
    for item in value:
        candidate = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", str(item))
        candidate = re.sub(r"\s*[\uff08(].*?[\uff09)]\s*$", "", candidate)
        candidate = candidate.strip().strip('"\'')
        candidate = _TRAILING.sub("", candidate).strip()
        if (
            not candidate
            or not is_japanese(candidate)
            or len(candidate) > 20
            or any(ch.isspace() for ch in candidate)
        ):
            continue
        if candidate not in out:
            out.append(candidate)
        if len(out) == 3:
            break
    return tuple(out)


def _parse_llm_rewrite(raw: str, fallback: str) -> tuple[str, tuple[str, ...]]:
    """Read the pivot JSON; tolerate code fences and a plain-English reply."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text).strip()
    data = None
    if match := re.search(r"\{.*\}", text, re.S):
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
    if isinstance(data, dict):
        english = _clean_english(data.get("english") or data.get("gloss") or "")
        japanese = _clean_japanese(data.get("japanese") or data.get("ja") or ())
    else:
        # Small/older models sometimes ignore the JSON instruction. Preserve
        # the old single-gloss behaviour rather than failing the search.
        english = _clean_english(text.splitlines()[0] if text else "")
        japanese = ()
    return english or fallback, japanese


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
def llm_rewrite(query: str) -> tuple[str, tuple[str, ...]]:
    from app.grammar_explain import chat  # lazy: keeps the LLM SDK off the retrieval-only path

    # gpt-oss burns ~63-144 tokens on reasoning even at effort="low"; the
    # JSON prompt is longer than the old 1-3-word gloss, so keep headroom for
    # reasoning plus three candidates and let chat() grow it on a truncation.
    # Deterministic dictionary mapping; the low temperature also keeps the
    # ranked candidates stable enough to compare runs.
    out = chat(_LLM_SYSTEM, query, max_tokens=700, temperature=0)
    # Empty fallback: an unparsable reply must not replace a good heuristic
    # result with the full original question.
    return _parse_llm_rewrite(out, "")


def rewrite_query(query: str, mode: str | None = None) -> Rewrite:
    """
    mode: 'off' | 'heuristic' | 'auto' (heuristic, then LLM for sentence-like queries).
    Defaults to the QUERY_REWRITE environment setting.
    """
    mode = (mode or QUERY_REWRITE).lower()
    original = query.strip()
    if mode == "off" or not original:
        return Rewrite(original, original, "none")
    if is_japanese(original):
        return Rewrite(original, normalise(original), "none")

    heuristic = heuristic_rewrite(original)
    q = heuristic if heuristic is not None else normalise(original)

    # A heuristic match used to short-circuit the LLM permanently. That left
    # "a word for feeling very tired" as a five-word phrase; let the model
    # pivot any heuristic output that is still more than a one-word lookup.
    # For non-heuristic input, 3 words is enough ("a baby dog" -> 子犬).
    threshold = 2 if heuristic is not None else 3
    if mode == "auto" and len(q.split()) >= threshold:
        try:
            english, japanese = llm_rewrite(original if heuristic is not None else q)
        except Exception:
            english, japanese = "", ()
        if japanese or (english and english != q):
            return Rewrite(original, english or q, "llm", japanese)

    if heuristic is not None:
        return Rewrite(original, q, "heuristic")
    return Rewrite(original, q, "none")
