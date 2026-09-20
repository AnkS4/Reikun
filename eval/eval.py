#!/usr/bin/env python3
"""
Unified evaluation entrypoint for Reikun.

`eval/gold_set.tsv` is the single source of truth. Subsets: `en_words` +
`en_verbs` (the default ~106-query English-word benchmark), `en_descriptive`
(question-style queries exercising the rewrite path), and `ja_words` /
`ja_hiragana` / `ja_katakana` (exact-lookup route coverage) — all opt-in via
--subsets.

Default (no suite flag): headword benchmark against *current settings* — no
mode/rewrite overrides, so it uses whatever the env configures (auto route,
QUERY_REWRITE). The ranking knobs can be swept in-process;
each is patched per variant and the search cache cleared between them (query
rewrites stay cached, so Cohere calls only happen on the first variant).
Omitting a flag keeps the value committed in app/retrieval.py:

    --canon   CANONICAL_BOOST — weight of wf_score × first-sense-gloss match
    --pool    PREFETCH_MIN    — candidates per retrieval arm (recall ceiling)
    --common  COMMON_BOOST    — flat prior on JMdict's is_common/commonness

Other suites (combine freely):

    --modes   fixed text / hybrid / auto comparison, rewrite off (no Cohere)
    --ir      retrieval-config suite — Hit@k / MRR / NDCG / MAP / recall over
              relevant entry IDs, overall and per gold subset
    --llm     level-aware vs generic grammar-explanation eval (Cohere judge)

Usage:
    python eval/eval.py                                   # production benchmark
    python eval/eval.py --canon 0.5 1 2 --pool 30 100     # knob sweep
    python eval/eval.py --subsets descriptive
    python eval/eval.py --modes                           # mode comparison
    python eval/eval.py --ir --configs vector hybrid      # IR suite subset
    python eval/eval.py --ir --k 5 --no-llm               # skip Cohere configs
    python eval/eval.py --llm --sentences 2               # conserve Cohere quota

Outputs under eval/results/ (headword/mode runs are timestamped so runs never
overwrite each other; the IR and LLM reports keep canonical names):
    eval_headword_<ts>_<variant>.md   per-variant top-5 detail + Hit@1/2/5
    eval_grid_<ts>.csv                query × variant rank of expected
    eval_modes_<mode>_<ts>.md         per-mode top-5 detail + Hit@1/2/5
    retrieval_eval.{md,json}          IR suite report
    llm_eval.{md,json}                LLM judge report
"""

import argparse
import csv
import json
import math
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app.retrieval as retrieval  # noqa: E402
from app.config import COLLECTION, PROC_DIR, QDRANT_URL, QUERY_REWRITE, qdrant_client  # noqa: E402
from app.retrieval import search  # noqa: E402

RESULTS_DIR = ROOT / "eval" / "results"

# ---------------------------------------------------------------------------
# Gold set — eval/gold_set.tsv is the single source for every suite. One row
# per query: category <TAB> query <TAB> expected_answers <TAB> notes, where
# expected_answers is every accepted alternative joined by " / " (ordered
# most-to-least preferred). A 4th notes column is informational only.
# ---------------------------------------------------------------------------

def _load_gold() -> dict[str, dict[str, list[str]]]:
    gold: dict[str, dict[str, list[str]]] = {}
    for line in (Path(__file__).resolve().parent / "gold_set.tsv").read_text(
            encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        subset, query, expected, *_note = line.split("\t")
        if subset == "category":  # header row
            continue
        alts = [re.sub(r"\s*\(.*?\)\s*$", "", a).strip()
                for a in expected.split("/")]
        gold.setdefault(subset, {}).setdefault(query, []).extend(
            a for a in alts if a)
    return gold


GOLD = _load_gold()
DEFAULT_SUBSETS = ("en_words", "en_verbs")
EXPECTED = {q: exp for g in GOLD.values() for q, exp in g.items()}


def load_queries(subsets=DEFAULT_SUBSETS) -> list[str]:
    return [q for name in subsets for q in GOLD[name]]


def load_gold_qrels(subsets=DEFAULT_SUBSETS) -> list[dict]:
    """{query, category, relevant_ids, expected} records for IR-style eval.

    An expected word counts as relevant when it appears in a chunk's
    kanji_form, reading, or their variant lists — matching the
    headword/reading hit rule the headword suite scores against. IDs come
    from chunks.json (= Qdrant point IDs), so no live collection is needed
    at load time.
    """
    chunks = json.loads((PROC_DIR / "chunks.json").read_text(encoding="utf-8"))
    by_form: dict[str, list[int]] = {}
    for c in chunks:
        forms = [c.get("kanji_form"), c.get("reading")]
        forms += c.get("kanji_forms", []) + c.get("readings", [])
        for f in forms:
            if f:
                by_form.setdefault(f, []).append(c["id"])
    out = []
    for name in subsets:
        for q, alts in GOLD[name].items():
            ids = sorted({int(i) for w in alts for i in by_form.get(w, ())})
            out.append({"query": q, "category": name,
                        "relevant_ids": ids, "expected": alts})
    return out


def _hit(res: dict, expected: list[str]) -> bool:
    return any(w in (res["headword"], res["reading"]) for w in expected)


def rank_of_expected(resp, expected: list[str]) -> int:
    """1-based rank of the first result matching an expected alternative; 0 = absent."""
    for i, r in enumerate(resp.results, 1):
        if _hit({"headword": r.get("kanji_form") or r["reading"], "reading": r["reading"]}, expected):
            return i
    return 0


def headword_markdown(rows: list[dict], title: str, meta: dict | None = None) -> str:
    lat = [r["latency_ms"] for r in rows]
    lat_sorted = sorted(lat)
    n = len(lat_sorted)
    median = lat_sorted[n // 2] if n % 2 else (lat_sorted[n // 2 - 1] + lat_sorted[n // 2]) / 2
    scored = [r for r in rows if r.get("expected")]
    hit1 = sum(1 for r in scored if r["results"] and _hit(r["results"][0], r["expected"]))
    hit2 = sum(1 for r in scored if any(_hit(res, r["expected"]) for res in r["results"][:2]))
    hit5 = sum(1 for r in scored if any(_hit(res, r["expected"]) for res in r["results"]))
    out = [f"# {title}\n"]
    if meta:
        out.append(" · ".join(f"{k}={v}" for k, v in meta.items()) + "\n")
    out += [f"{n} queries · median {median:.1f} ms · min {min(lat):.1f} ms · max {max(lat):.1f} ms\n",
            f"**Hit@1 {hit1}/{len(scored)} · Hit@2 {hit2}/{len(scored)} · Hit@5 {hit5}/{len(scored)}** "
            f"(expected headwords from gold_set.tsv)\n"]
    for r in rows:
        exp = f" — expected: {'/'.join(r['expected'])}" if r.get("expected") else ""
        out.append(f"## `{r['query']}`  ({r['latency_ms']} ms){exp}")
        if not r["results"]:
            out.append("- _(no results)_")
        for res in r["results"]:
            head = res["headword"]
            reading = f" 【{res['reading']}】" if res["reading"] != head else ""
            mark = " ✅" if r.get("expected") and _hit(res, r["expected"]) else ""
            out.append(f"- score {res['score']:.3f} — **{head}**{reading}{mark} — {', '.join(res['meanings'])}")
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Headword suite — default benchmark + knob sweep (--canon/--pool/--common).
# ---------------------------------------------------------------------------

def run_headword(canon: float, pool: int, common: float, queries: list[str]) -> list[dict]:
    retrieval.CANONICAL_BOOST, retrieval.PREFETCH_MIN = canon, pool
    retrieval.COMMON_BOOST = common
    retrieval._search_cached.cache_clear()  # knobs aren't part of the cache key
    rows = []
    for q in queries:
        t0 = time.perf_counter()
        resp = search(q, num_results=5)  # all defaults — current settings
        ms = round((time.perf_counter() - t0) * 1000, 1)
        expected = EXPECTED.get(q, [])
        rows.append({
            "query": q, "expected": expected, "latency_ms": ms,
            "rank": rank_of_expected(resp, expected),
            "results": [{"headword": r.get("kanji_form") or r["reading"], "reading": r["reading"],
                         "meanings": r["meanings"][:3], "score": r["score"]} for r in resp.results],
        })
    return rows


def headword_suite(args) -> None:
    subsets = tuple(args.subsets or DEFAULT_SUBSETS)
    queries = load_queries(subsets)
    combos = [(c, pl, cm) for c in args.canon for pl in args.pool for cm in args.common]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    points = qdrant_client().count(COLLECTION).count
    print(f"endpoint={QDRANT_URL[:50]} rewrite={QUERY_REWRITE} points={points}")
    print(f"{len(queries)} queries ({' '.join(subsets)}) × {len(combos)} variants …", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    grid: dict[str, dict[tuple, int]] = {q: {} for q in queries}
    summary: dict[tuple, dict] = {}
    labels: dict[tuple, str] = {}
    for canon, pool, common in combos:
        key = (canon, pool, common)
        label = f"canon{canon:g}_pool{pool}_common{common:g}"
        labels[key] = label
        print(f"→ CANONICAL_BOOST={canon} PREFETCH_MIN={pool} COMMON_BOOST={common}", flush=True)
        rows = run_headword(canon, pool, common, queries)
        meta = {"ts": stamp, "endpoint": QDRANT_URL, "points": points, "mode": "auto",
                "subsets": ",".join(subsets), "rewrite": QUERY_REWRITE,
                "CANONICAL_BOOST": canon, "PREFETCH_MIN": pool,
                "COMMON_BOOST": common}
        md_path = RESULTS_DIR / f"eval_headword_{stamp}_{label}.md"
        md_path.write_text(headword_markdown(rows, f"Vocab scoring — current settings ({label})", meta),
                           encoding="utf-8")
        scored = [r for r in rows if r["expected"]]
        summary[key] = {
            "hit1": sum(1 for r in scored if r["rank"] == 1),
            "hit2": sum(1 for r in scored if 0 < r["rank"] <= 2),
            "hit5": sum(1 for r in scored if r["rank"] > 0),
            "median_ms": sorted(r["latency_ms"] for r in rows)[len(rows) // 2],
        }
        for r in rows:
            grid[r["query"]][key] = r["rank"]
        s = summary[key]
        print(f"   Hit@1={s['hit1']} Hit@2={s['hit2']} Hit@5={s['hit5']}/{len(scored)} "
              f"median={s['median_ms']}ms → {md_path.name}", flush=True)

    csv_path = RESULTS_DIR / f"eval_grid_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"# ts={stamp} endpoint={QDRANT_URL} rewrite={QUERY_REWRITE} points={points}"])
        w.writerow(["query", "expected"] + [labels[c] for c in combos])
        for q in queries:
            w.writerow([q, "/".join(EXPECTED.get(q, []))] + [grid[q].get(c) or "-" for c in combos])
        w.writerow([])
        for metric in ("hit1", "hit2", "hit5", "median_ms"):
            w.writerow([metric, ""] + [summary[c][metric] for c in combos])
    print(f"→ {csv_path}")


# ---------------------------------------------------------------------------
# Mode comparison — text / hybrid / auto, rewrite off (no Cohere calls).
# ---------------------------------------------------------------------------

def modes_suite(args) -> None:
    subsets = tuple(args.subsets or DEFAULT_SUBSETS)
    queries = load_queries(subsets)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    print(f"{len(queries)} queries loaded (subsets: {' '.join(subsets)})")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for mode in ("text", "hybrid", "auto"):
        print(f"→ running mode={mode} …", flush=True)
        rows = []
        for q in queries:
            t0 = time.perf_counter()
            resp = search(q, num_results=5, mode=mode, rewrite_mode="off")
            ms = round((time.perf_counter() - t0) * 1000, 1)
            rows.append({
                "query": q, "expected": EXPECTED.get(q, []), "latency_ms": ms,
                "results": [{"headword": r.get("kanji_form") or r["reading"], "reading": r["reading"],
                             "meanings": r["meanings"][:3], "score": r["score"]}
                            for r in resp.results],
            })
        meta = {"ts": stamp, "mode": mode, "subsets": ",".join(subsets),
                "rewrite": "off"}
        md = headword_markdown(rows, f"Vocab scoring set — mode={mode}", meta)
        out_path = RESULTS_DIR / f"eval_modes_{mode}_{stamp}.md"
        out_path.write_text(md, encoding="utf-8")
        lat = [r["latency_ms"] for r in rows]
        print(f"   median={sorted(lat)[len(lat) // 2]:.1f}ms  min={min(lat):.1f}ms  "
              f"max={max(lat):.1f}ms  -> {out_path}")


# ---------------------------------------------------------------------------
# IR suite — config comparison over relevant entry IDs (Hit@k/MRR/NDCG/MAP).
# ---------------------------------------------------------------------------

K_VALUES = (1, 3, 5)

IR_CONFIGS: dict[str, dict] = {
    "vector": dict(mode="vector", rewrite_mode="off"),
    "text (bm25)": dict(mode="text", rewrite_mode="off"),
    "hybrid": dict(mode="hybrid", rewrite_mode="off"),
    "hybrid + rewrite(heuristic)": dict(mode="hybrid", rewrite_mode="heuristic"),
    "auto + rewrite(heuristic)": dict(mode="auto", rewrite_mode="heuristic"),
    "hybrid + rewrite(auto/llm)": dict(mode="hybrid", rewrite_mode="auto"),
}


def run_ir_config(name: str, kwargs: dict, gold: list[dict], k: int) -> dict:
    hits = dict.fromkeys(K_VALUES, 0)
    ndcg = dict.fromkeys(K_VALUES, 0.0)
    recall = dict.fromkeys(K_VALUES, 0.0)
    rr_total, map_total, latency, per_cat, misses = 0.0, 0.0, [], {}, []
    for g in gold:
        resp = search(g["query"], num_results=k, **kwargs)
        latency.append(resp.latency_ms)
        ids = [r["id"] for r in resp.results]
        relevant = set(g["relevant_ids"])
        num_relevant = len(relevant)
        ranks = [i for i, pid in enumerate(ids, 1) if pid in relevant]
        for kk in K_VALUES:
            hits[kk] += int(any(r <= kk for r in ranks))
            dcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(kk, len(ids)) + 1) if ids[i - 1] in relevant)
            idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(num_relevant, kk) + 1))
            ndcg[kk] += dcg / idcg if idcg > 0 else 0.0
            recall[kk] += sum(1 for r in ranks if r <= kk) / num_relevant if num_relevant > 0 else 0.0
        ap = 0.0
        rel_found = 0
        for i in range(1, k + 1):
            if i <= len(ids) and ids[i - 1] in relevant:
                rel_found += 1
                ap += rel_found / i
        ap = ap / num_relevant if num_relevant > 0 else 0.0
        map_total += ap
        rr = 1.0 / ranks[0] if ranks else 0.0
        rr_total += rr
        per_cat.setdefault(g["category"], []).append(rr)
        if not ranks:
            misses.append({"query": g["query"], "rewritten": resp.rewrite.query,
                           "expected": g.get("expected", []),
                           "got": [r.get("kanji_form") or r["reading"] for r in resp.results[:3]]})
    n = len(gold)
    return {
        "config": name,
        **{f"hit@{kk}": round(hits[kk] / n, 3) for kk in K_VALUES},
        **{f"ndcg@{kk}": round(ndcg[kk] / n, 3) for kk in K_VALUES},
        **{f"recall@{kk}": round(recall[kk] / n, 3) for kk in K_VALUES},
        "mrr": round(rr_total / n, 3),
        "map": round(map_total / n, 3),
        "mrr_by_category": {c: round(sum(v) / len(v), 3) for c, v in per_cat.items()},
        "avg_latency_ms": int(sum(latency) / len(latency)),
        "misses": misses,
    }


def ir_markdown(results: list[dict], gold_n: int, k: int) -> str:
    cats = sorted({c for r in results for c in r["mrr_by_category"]})
    lines = [
        "# Retrieval evaluation",
        "",
        f"Gold set: {gold_n} queries (`eval/gold_set.tsv`), top-k = {k}. "
        "Hit@k = share of queries with a relevant entry in the top k; MRR = mean reciprocal rank; "
        "NDCG = normalized discounted cumulative gain; MAP = mean average precision over all relevant IDs.",
        "",
        "| Configuration | Hit@1 | Hit@3 | Hit@5 | MRR | NDCG@5 | MAP | R@5 | avg ms | " + " | ".join(f"MRR {c}" for c in cats) + " |",
        "|---|" + "---|" * (8 + len(cats)),
    ]
    best = max(results, key=lambda r: (r["mrr"], r["hit@1"]))
    for r in results:
        name = f"**{r['config']}**" if r is best else r["config"]
        cat_cells = " | ".join(f"{r['mrr_by_category'].get(c, 0):.2f}" for c in cats)
        lines.append(f"| {name} | {r['hit@1']:.2f} | {r['hit@3']:.2f} | {r['hit@5']:.2f} | {r['mrr']:.3f} | {r['ndcg@5']:.3f} | {r['map']:.3f} | {r['recall@5']:.2f} | {r['avg_latency_ms']} | {cat_cells} |")
    lines += ["", f"Best configuration: **{best['config']}** (MRR {best['mrr']:.3f}).", ""]
    for r in results:
        if r["misses"]:
            lines.append(f"<details><summary>Misses — {r['config']} ({len(r['misses'])})</summary>\n")
            lines += [f"- `{m['query']}` → `{m['rewritten']}` → got {m['got']}" for m in r["misses"]]
            lines.append("\n</details>\n")
    return "\n".join(lines)


def ir_suite(args) -> None:
    gold = load_gold_qrels(tuple(args.subsets or GOLD))  # IR suite covers all subsets by default
    if args.no_llm:
        configs = [c for c in args.configs if "auto/llm" not in c and "cohere" not in c]
    else:
        configs = list(args.configs)
    print(f"{len(gold)} gold queries · {len(configs)} configurations\n")

    results = []
    for name in configs:
        t0 = time.perf_counter()
        res = run_ir_config(name, IR_CONFIGS[name], gold, args.k)
        results.append(res)
        print(f"{name:34s} hit@1={res['hit@1']:.2f} hit@5={res['hit@5']:.2f} mrr={res['mrr']:.3f} "
              f"map={res['map']:.3f} ndcg@5={res['ndcg@5']:.3f} "
              f"({res['avg_latency_ms']} ms/query, {time.perf_counter() - t0:.0f}s)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "retrieval_eval.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS_DIR / "retrieval_eval.md").write_text(ir_markdown(results, len(gold), args.k), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'retrieval_eval.md'}")


# ---------------------------------------------------------------------------
# LLM suite — level-aware vs generic grammar prompt, Cohere judge (opt-in).
# ---------------------------------------------------------------------------

LEVELS = ("N5", "N1")
PROMPTS = {"level-aware": True, "generic": False}

# Cohere trial keys are capped at ~10 calls/min (see app/grammar_explain.py).
# Each eval row makes two Cohere calls (generation + judge), so we sleep just
# long enough between calls to stay under the rate limit.
_COHERE_MAX_CALLS_PER_MIN = 10
_COHERE_MIN_INTERVAL = 60.0 / _COHERE_MAX_CALLS_PER_MIN
_last_cohere_call = 0.0

FALLBACK_SENTENCES = [
    {"japanese": "私は毎日日本語を勉強します。", "english": "I study Japanese every day."},
    {"japanese": "昨日、友達と映画を見に行きました。", "english": "Yesterday I went to watch a movie with a friend."},
    {"japanese": "日本語を勉強するのは楽しいです。", "english": "Studying Japanese is fun."},
    {"japanese": "彼の意見には賛成できない。", "english": "I cannot agree with his opinion."},
    {"japanese": "いかに困難であろうとも、最後までやり遂げなければならない。", "english": "No matter how difficult it may be, we must carry it through to the end."},
]


def load_sentences(n: int) -> list[dict]:
    """First example sentence of each gold query's first relevant entry (deduped)."""
    gold = load_gold_qrels()
    chunks = {c["id"]: c for c in json.loads((PROC_DIR / "chunks.json").read_text(encoding="utf-8"))}
    out, seen = [], set()
    for q in gold:
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
    from app.grammar_explain import chat
    user = f"Learner level: {level}\nSentence: {sentence}\n\nExplanation:\n{explanation}"
    raw = chat(JUDGE_SYSTEM, user, thinking_budget=100, max_tokens=400)
    try:
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {"level_fit": None, "accuracy": None, "comment": raw.strip()[:200]}


def llm_evaluate(sentences: list[dict]) -> list[dict]:
    from app.grammar_explain import explain_grammar
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


def llm_summarise(rows: list[dict]) -> list[dict]:
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


def llm_markdown(rows: list[dict], summary: list[dict]) -> str:
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


def llm_suite(args) -> None:
    sentences = load_sentences(args.sentences)
    print(f"{len(sentences)} sentences × {LEVELS} × {list(PROMPTS)}\n")
    for s in sentences:
        print(f"  [{s.get('query', '?')}] {s['japanese']}")
    print()
    rows = llm_evaluate(sentences)
    summary = llm_summarise(rows)

    print("\nSummary:")
    for s in summary:
        print(f"  {s['level']} {s['prompt']:12s} words={s['avg_words']:5.1f} jargon={s['avg_jargon']:4.1f} "
              f"analogy={s['analogy_rate']:.0%} fit={s['judge_level_fit']} acc={s['judge_accuracy']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "llm_eval.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS_DIR / "llm_eval.md").write_text(llm_markdown(rows, summary), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'llm_eval.md'}")


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--subsets", nargs="+", default=None, choices=list(GOLD),
                        metavar="NAME", help="gold subsets to evaluate (default: en_words en_verbs; all for --ir)")
    parser.add_argument("--canon", type=float, nargs="+", default=[retrieval.CANONICAL_BOOST],
                        help="CANONICAL_BOOST values to sweep (default: committed %(default)s)")
    parser.add_argument("--pool", type=int, nargs="+", default=[retrieval.PREFETCH_MIN],
                        help="PREFETCH_MIN values to sweep (default: committed %(default)s)")
    parser.add_argument("--common", type=float, nargs="+", default=[retrieval.COMMON_BOOST],
                        help="COMMON_BOOST values to sweep (default: committed %(default)s)")
    parser.add_argument("--modes", action="store_true",
                        help="run the text/hybrid/auto mode comparison (rewrite off)")
    parser.add_argument("--ir", action="store_true",
                        help="run the retrieval-config IR suite (Hit@k/MRR/NDCG/MAP)")
    parser.add_argument("--configs", nargs="+", choices=list(IR_CONFIGS), default=list(IR_CONFIGS),
                        help="--ir configurations to run (default: all)")
    parser.add_argument("--k", type=int, default=5, help="--ir top-k (default: %(default)s)")
    parser.add_argument("--no-llm", action="store_true",
                        help="--ir: skip configurations that call the Cohere API")
    parser.add_argument("--llm", action="store_true",
                        help="run the grammar-explanation LLM-judge eval")
    parser.add_argument("--sentences", type=int, default=5,
                        help="--llm: sentences to evaluate (default: %(default)s)")
    args = parser.parse_args()

    if not (args.modes or args.ir or args.llm):
        headword_suite(args)
    if args.modes:
        modes_suite(args)
    if args.ir:
        ir_suite(args)
    if args.llm:
        llm_suite(args)


if __name__ == "__main__":
    main()
