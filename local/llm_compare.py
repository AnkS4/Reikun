#!/usr/bin/env python3
"""
Compare grammar-explanation output across LLM providers.

Sends the same level-aware prompts (app.grammar_explain) through Groq's
chat models (the production backend) plus Cohere and Gemini baselines over
their OpenAI-compatible endpoints, then writes a report with the raw outputs plus
format-adherence stats per model: bullet count vs the level's range, word
count vs the level's ceiling, pattern bolding, leaked reasoning markers,
latency, and finish reason.

Usage:
    python scripts/llm_compare.py                        # all models, N5+N1, 5 sentences
    python scripts/llm_compare.py --levels N5,N3,N1 --sentences 2
    python scripts/llm_compare.py --from-db 10 --seed 3  # sample Tatoeba pairs from chunks.json
    python scripts/llm_compare.py --only groq            # skip Cohere (save its 1k/mo quota)
    python scripts/llm_compare.py --models 120b,qwen     # substring filter over model names
    python scripts/llm_compare.py --no-english           # drop the "Meaning:" line from prompts
    python scripts/llm_compare.py --judge                # scored by gemini:gemini-3.5-flash-lite (non-contestant)
    python scripts/llm_compare.py --judge --judge-model groq:openai/gpt-oss-20b
    python scripts/llm_compare.py --pace 4               # slower — stay well under Groq's 8K TPM

Keys: COHERE_API_KEY / COHERE_MODEL, GROQ_API_KEY, GEMINI_API_KEY — read from .env.
Output: local/results/llm_compare.{md,json}
Note: this file and its outputs are gitignored — local benchmarking scratch only.
"""

import argparse
import json
import os
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.grammar_explain import _LEVEL, level_aware_prompt, level_aware_system

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
COHERE_MODEL = os.getenv("COHERE_MODEL", "command-a-plus-05-2026")

RESULTS_DIR = Path(__file__).resolve().parent / "results"

GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
# Free-tier (AI Studio, Oct 2026): 3.8-flash ~5 RPM/20 RPD, 3.5-flash-lite
# ~15 RPM/500 RPD, gemma-4-31b ~8 RPM/110 RPD.
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemma-4-31b-it"]

# Same starter set eval/eval.py uses when the corpus has no gold examples —
# kept here verbatim so the script stays runnable standalone.
SENTENCES = [
    {"japanese": "私は毎日日本語を勉強します。", "english": "I study Japanese every day."},
    {"japanese": "昨日、友達と映画を見に行きました。", "english": "Yesterday I went to watch a movie with a friend."},
    {"japanese": "日本語を勉強するのは楽しいです。", "english": "Studying Japanese is fun."},
    {"japanese": "彼の意見には賛成できない。", "english": "I cannot agree with his opinion."},
    {"japanese": "いかに困難であろうとも、最後までやり遂げなければならない。",
     "english": "No matter how difficult it may be, we must carry it through to the end."},
]

_LEAKED = re.compile(r"<\|[^|]*\|>")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s", re.MULTILINE)

JUDGE_SYSTEM = """\
You are an expert Japanese teacher evaluating a grammar explanation written
for a learner at a given JLPT level. Return ONLY a JSON object:
{"level_fit": <1-5>, "accuracy": <1-5>, "comment": "<one sentence>"}
level_fit: 5 = perfectly pitched for that learner (vocabulary, terminology,
depth), 1 = badly mismatched (too advanced or too simplistic).
accuracy: 5 = grammatically accurate and complete for the sentence, 1 = wrong.\
"""


@lru_cache(maxsize=1)
def _groq_client():
    from groq import Groq

    return Groq()  # reads GROQ_API_KEY from the environment


@lru_cache(maxsize=1)
def _cohere_client():
    import cohere

    return cohere.ClientV2()


def cohere_chat(system: str, user: str, max_tokens: int) -> str:
    """Cohere baseline leg — self-contained now that the app speaks Groq.
    Same knobs the retired app/grammar_explain.chat used."""
    import cohere

    for attempt in range(3):
        try:
            r = _cohere_client().chat(
                model=COHERE_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                thinking={"type": "enabled", "token_budget": 150},
                max_tokens=max_tokens)
            return "".join(i.text for i in r.message.content or [] if i.type == "text").strip()
        except cohere.TooManyRequestsError:
            if attempt == 2:
                raise
            time.sleep(7)
    raise RuntimeError("unreachable")


def db_sentences(n: int, seed: int) -> list[dict]:
    """N random (seeded) example pairs from chunks.json — real Tatoeba sentences."""
    import random

    chunks = json.loads((Path(__file__).resolve().parent.parent / "data/processed/chunks.json")
                        .read_text(encoding="utf-8"))
    pool = [c["example_sentences"][0] for c in chunks if c.get("example_sentences")]
    random.Random(seed).shuffle(pool)
    out, seen = [], set()
    for ex in pool:
        if ex["japanese"] not in seen:
            seen.add(ex["japanese"])
            out.append(ex)
        if len(out) >= n:
            break
    return out


def groq_chat(system: str, user: str, model: str, max_tokens: int, *, effort: str = "low") -> tuple[str, dict]:
    """One non-streaming chat completion via the Groq SDK."""
    import groq

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY not set")
    kwargs = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_tokens,
        "reasoning_effort": effort,
    }
    for _ in range(3):  # ride out transient RPM/TPM 429s using the API's own hint
        try:
            resp = _groq_client().chat.completions.create(**kwargs)
            break
        except groq.RateLimitError as exc:
            wait = exc.response.headers.get("retry-after")
            time.sleep(float(wait) + 0.5 if wait else 10.0)
        except groq.BadRequestError as exc:
            if "reasoning_effort" not in str(exc):
                raise
            kwargs.pop("reasoning_effort")  # non-reasoning models reject the param
    else:
        raise RuntimeError("Groq rate limit persisted across retries")
    choice = resp.choices[0]
    return (choice.message.content or "").strip(), {
        "finish_reason": choice.finish_reason,
        "tokens": resp.usage.total_tokens if resp.usage else None,
    }


@lru_cache(maxsize=1)
def _gemini_client():
    from google import genai

    return genai.Client()  # reads GEMINI_API_KEY from the environment


def gemini_chat(system: str, user: str, model: str, max_tokens: int) -> tuple[str, dict]:
    from google.genai import errors, types

    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY not set")
    # Gemma rejects system_instruction and thinking_config — fold the system
    # prompt into the user turn instead.
    is_gemma = model.startswith("gemma")
    contents = f"{system}\n\n{user}" if is_gemma else user
    cfg = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        **({} if is_gemma else {
            "system_instruction": system,
            "thinking_config": types.ThinkingConfig(thinking_budget=0),
        }),
    )
    last_exc: Exception | None = None
    for _ in range(3):  # ride out transient 429/500s
        try:
            resp = _gemini_client().models.generate_content(model=model, contents=contents, config=cfg)
            return (resp.text or "").strip(), {
                "tokens": getattr(resp.usage_metadata, "total_token_count", None)}
        except errors.ClientError as exc:
            last_exc = exc
            if exc.code == 400:  # thinking_budget unsupported/invalid (3.x) → drop it only
                cfg = types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    **({} if is_gemma else {"system_instruction": system}))
                continue
            if exc.code == 429:
                time.sleep(10.0)  # RPM/RPD window
            else:
                raise
        except errors.ServerError as exc:
            last_exc = exc
            time.sleep(2.0)  # intermittent INTERNAL flake on Gemma models
    raise RuntimeError("Gemini request failed across retries") from last_exc


def check(text: str, level: str) -> dict:
    """Format adherence against the level's LevelConfig contract."""
    cfg = _LEVEL[level]
    lo, hi = 1, cfg.max_bullets
    bullets = len(_BULLET.findall(text))
    words = len(text.split())
    return {
        "bullets": bullets, "bullets_ok": lo <= bullets <= hi,
        "words": words, "words_ok": words <= cfg.words,
        "bolded": "**" in text, "leaked": bool(_LEAKED.search(text)),
    }


def run_one(provider: str, model: str, s: dict, level: str, *, with_english: bool) -> dict:
    system = level_aware_system(level)
    if with_english:
        user = level_aware_prompt(s["japanese"], s["english"], level)
    else:
        cfg = _LEVEL.get(level, _LEVEL["N3"])
        user = (f"Explain the Japanese grammar patterns for a {level} learner ({cfg.desc}).\n\n"
                f"Sentence: {s['japanese']}")
    t0 = time.perf_counter()
    try:
        if provider == "cohere":
            text = cohere_chat(system, user, max_tokens=_LEVEL[level].token_budget)
            meta = {}
        elif provider == "gemini":
            text, meta = gemini_chat(system, user, model, _LEVEL[level].token_budget)
        else:
            text, meta = groq_chat(system, user, model, _LEVEL[level].token_budget)
        status = "ok" if text.strip() else "empty"  # reasoning-only responses return blank content
    except Exception as exc:
        text, meta, status = "", {}, f"{type(exc).__name__}: {exc}"
    row = {"provider": provider, "model": model, "sentence": s["japanese"], "level": level,
           "ms": int((time.perf_counter() - t0) * 1000), "status": status, "explanation": text, **meta}
    if status == "ok":
        row.update(check(text, level))
    return row


def judge(text: str, level: str, sentence: str, model_spec: str) -> dict:
    """Score one explanation via a `provider:model` spec — e.g.
    `gemini:gemini-2.5-flash`, `groq:openai/gpt-oss-20b`, `cohere:` (uses
    COHERE_MODEL). Prefer a non-contestant provider to avoid self-scoring bias."""
    provider, _, model = model_spec.partition(":")
    user = f"Learner level: {level}\nSentence: {sentence}\n\nExplanation:\n{text}"
    if provider == "gemini":
        raw, _ = gemini_chat(JUDGE_SYSTEM, user, model, 400)
    elif provider == "cohere":
        raw = cohere_chat(JUDGE_SYSTEM, user, max_tokens=400)
    else:
        raw, _ = groq_chat(JUDGE_SYSTEM, user, model, 400)
    return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])


def pace(provider: str, last: dict, gaps: dict) -> None:
    """Cohere trial keys: ~10 calls/min; Groq free: 30 RPM / 8K TPM."""
    gap = gaps[provider]
    if last.get(provider):
        wait = gap - (time.perf_counter() - last[provider])
        if wait > 0:
            time.sleep(wait)
    last[provider] = time.perf_counter()


def markdown(rows: list[dict], models: list[tuple[str, str]]) -> str:
    def mname(r): return (r["provider"], r["model"])
    out = ["# LLM comparison — grammar explanations\n"]
    out.append("## Format adherence (level-aware prompts)\n")
    out.append("| model | level | n | bullets ok | words ok | bolded | leaks | errors | avg ms |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    for m in models:
        for level in sorted({r["level"] for r in rows}):
            sub = [r for r in rows if mname(r) == m and r["level"] == level]
            ok = [r for r in sub if r["status"] == "ok"]
            if not sub:
                continue
            def rate(k, ok=ok): return f"{sum(r.get(k) for r in ok)}/{len(ok)}"
            avg_ms = round(sum(r["ms"] for r in sub) / len(sub))
            errs = len(sub) - len(ok)
            out.append(f"| {m[1]} | {level} | {len(sub)} | {rate('bullets_ok')} | {rate('words_ok')} "
                       f"| {rate('bolded')} | {sum(r.get('leaked', False) for r in ok)} | {errs} | {avg_ms} |")
    for m in models:
        out.append(f"\n## {m[1]} ({m[0]})\n")
        for r in rows:
            if mname(r) != m:
                continue
            out.append(f"### {r['level']} — {r['sentence']}")
            if r["status"] != "ok":
                out.append(f"**ERROR** `{r['status']}`\n")
            else:
                judge = ""
                if r.get("level_fit"):
                    judge = f" — judge: fit {r['level_fit']}/5, acc {r['accuracy']}/5 — {r.get('comment', '')}"
                out.append(f"_{r['words']} words, {r['bullets']} bullets, {r['ms']} ms{judge}_\n")
                out.append(r["explanation"] + "\n")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default="N5,N1", help="comma list (default: N5,N1 — the calibration extremes)")
    ap.add_argument("--sentences", type=int, default=len(SENTENCES))
    ap.add_argument("--from-db", type=int, metavar="N", help="sample N example pairs from chunks.json instead")
    ap.add_argument("--seed", type=int, default=0, help="sampling seed for --from-db")
    ap.add_argument("--only", choices=["cohere", "groq", "gemini"], help="run one provider only")
    ap.add_argument("--models", help="comma-separated substrings to filter models, e.g. '120b,qwen'")
    ap.add_argument("--no-english", action="store_true", help="omit the 'Meaning:' line — JA-only prompts")
    ap.add_argument("--judge", action="store_true", help="score outputs level_fit/accuracy 1-5")
    ap.add_argument("--judge-model", default="gemini:gemini-3.5-flash-lite",
                    help="provider:model for --judge "
                         "(default: gemini-3.5-flash-lite — non-contestant, 15 RPM / 500 RPD free)")
    ap.add_argument("--out", default="llm_compare", help="output file stem in local/results/")
    ap.add_argument("--pace", type=float, default=2.5, help="seconds between Groq calls (default 2.5)")
    args = ap.parse_args()

    models = []
    have = {"groq": os.getenv("GROQ_API_KEY"), "gemini": os.getenv("GEMINI_API_KEY"), "cohere": COHERE_API_KEY}
    for prov, lst in (("groq", GROQ_MODELS), ("gemini", GEMINI_MODELS), ("cohere", [COHERE_MODEL])):
        if args.only in (None, prov) and have[prov]:
            models += [(prov, m) for m in lst]
    if args.models:
        keep = args.models.lower().split(",")
        models = [m for m in models if any(k in m[1].lower() for k in keep)]
    if not models:
        sys.exit("No API keys found — set GROQ_API_KEY / GEMINI_API_KEY / COHERE_API_KEY in .env")

    jprov = args.judge_model.partition(":")[0] if args.judge else ""
    if args.judge and not {"gemini": os.getenv("GEMINI_API_KEY"), "groq": os.getenv("GROQ_API_KEY"),
                          "cohere": COHERE_API_KEY}.get(jprov):
        sys.exit(f"--judge-model {args.judge_model} needs its API key in .env")

    levels = args.levels.upper().split(",")
    sentences = db_sentences(args.from_db, args.seed) if args.from_db else SENTENCES[: args.sentences]
    print(f"{len(sentences)} sentences x {levels} x {[m[1] for m in models]}\n")

    last: dict = {}
    gaps = {"cohere": 6.5, "groq": args.pace, "gemini": 4.5}
    rows = []
    for s in sentences:
        for level in levels:
            for provider, model in models:
                pace(provider, last, gaps)
                row = run_one(provider, model, s, level, with_english=not args.no_english)
                if args.judge and row["status"] == "ok":
                    pace(jprov, last, gaps)
                    try:
                        row.update(judge(row["explanation"], level, s["japanese"], args.judge_model))
                    except Exception as exc:
                        row["judge_error"] = f"{type(exc).__name__}: {exc}"[:200]
                rows.append(row)
                tick = f"fit={row.get('level_fit')} acc={row.get('accuracy')}" if row.get("level_fit") else ""
                status_str = (
                    row["status"]
                    if row["status"] != "ok"
                    else f"{row.get('words', 0)}w {row.get('bullets', 0)}b {row['ms']}ms"
                )
                print(f"  {row['model']:24s} {level} {status_str} {tick}", flush=True)

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{args.out}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS_DIR / f"{args.out}.md").write_text(markdown(rows, models), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / (args.out + '.md')}")


if __name__ == "__main__":
    main()
