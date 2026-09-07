#!/usr/bin/env python3
"""
LLM evaluation: level-aware vs generic grammar-explanation prompts.

For a handful of example sentences and two target levels (N5 and N1) we
generate explanations with both prompts, then score them with:

    • objective proxies – word count, count of linguistic jargon terms,
      presence of an English analogy ("like", "similar to", …)
    • an LLM judge (Cohere, blind to which prompt produced the text) rating
      1–5 for "appropriate for a <level> learner" and 1–5 for accuracy

Sentences come from the same gold set as the retrieval eval
(`eval/gold_set.json`): for each gold query we take the first example
sentence of its first relevant JMdict id from `data/processed/chunks.json`,
so both evals share a single source of truth.

Usage:
    python eval/llm_eval.py                # 5 sentences × 2 levels × 2 prompts = 20 generations + 20 judgments
    python eval/llm_eval.py --sentences 2  # smaller still, to conserve Cohere trial-tier quota

Writes eval/results/llm_eval.{json,md}.
"""

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import PROC_DIR  # noqa: E402
from app.grammar_explain import chat, explain_grammar  # noqa: E402

RESULTS_DIR = ROOT / "eval" / "results"
GOLD_SET = ROOT / "eval" / "gold_set.json"
LEVELS = ("N5", "N1")
PROMPTS = {"level-aware": True, "generic": False}

# Cohere trial keys are capped at ~10 calls/min (see app/grammar_explain.py).
# Each eval row makes two Cohere calls (generation + judge), so we sleep just
# long enough between calls to stay under the rate limit.
_COHERE_MAX_CALLS_PER_MIN = 10
_COHERE_MIN_INTERVAL = 60.0 / _COHERE_MAX_CALLS_PER_MIN
_last_cohere_call = 0.0

# Fallback if the corpus has no example sentences for the gold ids.
FALLBACK_SENTENCES = [
    {"japanese": "私は毎日日本語を勉強します。", "english": "I study Japanese every day."},
    {"japanese": "昨日、友達と映画を見に行きました。", "english": "Yesterday I went to watch a movie with a friend."},
    {"japanese": "日本語を勉強するのは楽しいです。", "english": "Studying Japanese is fun."},
    {"japanese": "彼の意見には賛成できない。", "english": "I cannot agree with his opinion."},
    {"japanese": "いかに困難であろうとも、最後までやり遂げなければならない。", "english": "No matter how difficult it may be, we must carry it through to the end."},
]


def load_sentences(n: int) -> list[dict]:
    """First example sentence of each gold query's first relevant entry (deduped)."""
    gold = json.loads(GOLD_SET.read_text(encoding="utf-8"))
    chunks = {c["id"]: c for c in json.loads((PROC_DIR / "chunks.json").read_text(encoding="utf-8"))}
    out, seen = [], set()
    for q in gold["queries"]:
        for rid in q["relevant_ids"]:
            examples = (chunks.get(str(rid)) or {}).get("example_sentences") or []
            if examples and examples[0]["japanese"] not in seen:
                seen.add(examples[0]["japanese"])
                out.append({"japanese": examples[0]["japanese"], "english": examples[0]["english"],
                            "query": q["query"]})
                break
        if len(out) >= n:
            break
    # Fill with fallbacks if the corpus has no examples for the gold ids.
    for fb in FALLBACK_SENTENCES:
        if len(out) >= n:
            break
        if fb["japanese"] not in seen:
            seen.add(fb["japanese"])
            out.append(fb)
    return out[:n]

JARGON = re.compile(
    r"\b(particle|auxiliary|copula|volitional|nominali[sz]er|conjugat\w*|causative|passive|honorific|humble|"
    r"subordinate|clause|morpheme|inflect\w*|te-form|potential form|conditional|concessive|topic marker|"
    r"case marker|predicate|modality|aspect|stem|adverbial|attributive|literary|formal register)\b",
    re.IGNORECASE,
)
ANALOGY = re.compile(r"\b(like|similar to|think of|imagine|just as|equivalent|in english)\b", re.IGNORECASE)

JUDGE_SYSTEM = """\
You are an expert Japanese teacher evaluating a grammar explanation written
for a learner at a given JLPT level. Return ONLY a JSON object:
{"level_fit": <1-5>, "accuracy": <1-5>, "comment": "<one sentence>"}
level_fit: 5 = perfectly pitched for that learner (vocabulary, terminology,
depth), 1 = badly mismatched (too advanced or too simplistic).
accuracy: 5 = grammatically accurate and complete for the sentence, 1 = wrong.\
"""


def _cohere_wait() -> None:
    """Sleep just enough to stay within the Cohere trial rate limit."""
    global _last_cohere_call
    if _last_cohere_call:
        elapsed = time.perf_counter() - _last_cohere_call
        if elapsed < _COHERE_MIN_INTERVAL:
            time.sleep(_COHERE_MIN_INTERVAL - elapsed)


def judge(sentence: str, level: str, explanation: str) -> dict:
    user = f"Learner level: {level}\nSentence: {sentence}\n\nExplanation:\n{explanation}"
    raw = chat(JUDGE_SYSTEM, user, thinking_budget=100, max_tokens=400)
    try:
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {"level_fit": None, "accuracy": None, "comment": raw.strip()[:200]}


def evaluate(sentences: list[dict]) -> list[dict]:
    rows = []
    for s in sentences:
        for level in LEVELS:
            for prompt, level_aware in PROMPTS.items():
                global _last_cohere_call
                _cohere_wait()
                t0 = time.perf_counter()
                text = explain_grammar(s["japanese"], s["english"], level, level_aware=level_aware)
                _last_cohere_call = time.perf_counter()
                gen_ms = int((time.perf_counter() - t0) * 1000)
                _cohere_wait()
                verdict = judge(s["japanese"], level, text)
                _last_cohere_call = time.perf_counter()
                rows.append({
                    "sentence": s["japanese"], "level": level, "prompt": prompt, "explanation": text,
                    "words": len(text.split()), "jargon_terms": len(JARGON.findall(text)),
                    "has_analogy": bool(ANALOGY.search(text)), "gen_ms": gen_ms, **verdict,
                })
                print(f"  {level} {prompt:12s} words={rows[-1]['words']:3d} jargon={rows[-1]['jargon_terms']:2d} "
                      f"fit={verdict.get('level_fit')} acc={verdict.get('accuracy')}", flush=True)
    return rows


def summarise(rows: list[dict]) -> list[dict]:
    out = []
    for level in LEVELS:
        for prompt in PROMPTS:
            sub = [r for r in rows if r["level"] == level and r["prompt"] == prompt]
            fits = [r["level_fit"] for r in sub if r["level_fit"] is not None]
            accs = [r["accuracy"] for r in sub if r["accuracy"] is not None]
            out.append({
                "level": level, "prompt": prompt, "n": len(sub),
                "avg_words": round(statistics.mean(r["words"] for r in sub), 1),
                "avg_jargon": round(statistics.mean(r["jargon_terms"] for r in sub), 1),
                "analogy_rate": round(sum(r["has_analogy"] for r in sub) / len(sub), 2),
                "judge_level_fit": round(statistics.mean(fits), 2) if fits else None,
                "judge_accuracy": round(statistics.mean(accs), 2) if accs else None,
            })
    return out


def to_markdown(rows: list[dict], summary: list[dict]) -> str:
    lines = [
        "# LLM evaluation — level-aware vs generic grammar prompt",
        "",
        f"{len(rows) // (len(LEVELS) * len(PROMPTS))} sentences × levels {', '.join(LEVELS)} × 2 prompts. "
        "Judge = Cohere (blind to prompt variant), scores 1–5.",
        "",
        "| Level | Prompt | avg words | avg jargon terms | analogy rate | judge: level fit | judge: accuracy |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(f"| {s['level']} | {s['prompt']} | {s['avg_words']} | {s['avg_jargon']} | {s['analogy_rate']:.0%} | "
                     f"{s['judge_level_fit']} | {s['judge_accuracy']} |")
    lines += ["", "## Side-by-side outputs", ""]
    for sent in dict.fromkeys(r["sentence"] for r in rows):
        lines.append(f"### {sent}\n")
        for level in LEVELS:
            for prompt in PROMPTS:
                r = next(x for x in rows if x["sentence"] == sent and x["level"] == level and x["prompt"] == prompt)
                lines += [f"**{level} · {prompt}** — fit {r['level_fit']}/5, accuracy {r['accuracy']}/5, {r['words']} words, "
                          f"{r['jargon_terms']} jargon terms · *{r.get('comment', '')}*", "", r["explanation"], ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sentences", type=int, default=5)
    args = parser.parse_args()

    sentences = load_sentences(args.sentences)
    print(f"{len(sentences)} sentences × {LEVELS} × {list(PROMPTS)}\n")
    for s in sentences:
        print(f"  [{s.get('query', '?')}] {s['japanese']}")
    print()
    rows = evaluate(sentences)
    summary = summarise(rows)

    print("\nSummary:")
    for s in summary:
        print(f"  {s['level']} {s['prompt']:12s} words={s['avg_words']:5.1f} jargon={s['avg_jargon']:4.1f} "
              f"analogy={s['analogy_rate']:.0%} fit={s['judge_level_fit']} acc={s['judge_accuracy']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "llm_eval.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS_DIR / "llm_eval.md").write_text(to_markdown(rows, summary), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'llm_eval.md'}")


if __name__ == "__main__":
    main()
