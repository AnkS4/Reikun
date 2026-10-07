#!/usr/bin/env python3
"""Japanese-subset retrieval eval — Hit@k per config for JA-script queries.

`eval/eval.py --ir` reports per-category MRR only; this script is the JA view
with full Hit@k (including Hit@2) overall and per subset — ja_words (kanji
headwords), ja_hiragana (kana readings), ja_katakana (loanwords, BM25's one
weak spot: compounds like テレビスクリーン edging out bare テレビ).

Runs every config from eval.py's IR_CONFIGS. No Groq calls: JA queries take
the exact-match route and rewrite=auto only fires on 4+ word English input.

Usage:
    python eval/eval_ja.py            # all configs, top-5
    python eval/eval_ja.py --k 10
    python eval/eval_ja.py --configs hybrid "auto + rewrite(heuristic)"

Output (overwrites — canonical names like the other reports):
    eval/reports/retrieval_eval_ja.{md,json}
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.retrieval import search  # noqa: E402

# eval.py owns the gold-set loader and the config table — load it as a module
# so this file is a thin JA-specific view rather than a fork of either.
_spec = importlib.util.spec_from_file_location(
    "eval_main", Path(__file__).resolve().parent / "eval.py"
)
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

JA_SUBSETS = ("ja_words", "ja_hiragana", "ja_katakana")
K_VALUES = (1, 2, 3, 5)
REPORTS_DIR = ROOT / "eval" / "reports"


def run_config(name: str, kwargs: dict, gold: list[dict], k: int) -> dict:
    """First-relevant-rank per query → Hit@k / MRR overall and per JA subset."""
    hits = dict.fromkeys(K_VALUES, 0)
    per_cat: dict[str, list[int]] = {}
    rr_total, latency, misses = 0.0, [], []
    for g in gold:
        resp = search(g["query"], num_results=k, **kwargs)
        latency.append(resp.latency_ms)
        relevant = set(g["relevant_ids"])
        rank = next((i for i, pid in enumerate((r["id"] for r in resp.results), 1)
                     if pid in relevant), 0)
        for kk in K_VALUES:
            hits[kk] += int(0 < rank <= kk)
        rr_total += 1.0 / rank if rank else 0.0
        per_cat.setdefault(g["category"], []).append(rank)
        if not rank:
            misses.append({"query": g["query"], "expected": g.get("expected", []),
                           "got": [r.get("kanji_form") or r["reading"]
                                   for r in resp.results[:3]]})
    n = len(gold)
    return {
        "config": name,
        **{f"hit@{kk}": round(hits[kk] / n, 3) for kk in K_VALUES},
        "mrr": round(rr_total / n, 3),
        "by_subset": {
            c: {
                **{f"hit@{kk}": round(sum(1 for r in ranks if 0 < r <= kk) / len(ranks), 3)
                   for kk in K_VALUES},
                "mrr": round(sum(1.0 / r for r in ranks if r) / len(ranks), 3),
            }
            for c, ranks in sorted(per_cat.items())
        },
        "avg_latency_ms": int(sum(latency) / len(latency)),
        "misses": misses,
    }


def markdown(results: list[dict], gold_n: int, k: int, default: str | None) -> str:
    hit_cols = " | ".join(f"Hit@{kk}" for kk in K_VALUES)
    lines = [
        "# Retrieval evaluation — Japanese subsets",
        "",
        f"Gold: {gold_n} queries ({', '.join(JA_SUBSETS)} from `eval/gold_set.tsv`), top-k = {k}. "
        "Hit@k = share of queries with a relevant entry in the top k. "
        "Companion to `retrieval_eval.md` (all 300 queries, per-category MRR only).",
        "",
        f"| Configuration | {hit_cols} | MRR | avg ms |",
        "|---|" + "---|" * (len(K_VALUES) + 2),
    ]
    # Production default pinned to the top row; the rest keep run order.
    ordered = sorted(results, key=lambda r: r["config"] != default)
    # Best = top (hit@1, mrr); ties go to the default config, else lowest latency.
    top = max((r["hit@1"], r["mrr"]) for r in results)
    tied = [r for r in results if (r["hit@1"], r["mrr"]) == top]
    best = next((r for r in tied if r["config"] == default),
                min(tied, key=lambda r: r["avg_latency_ms"]))

    def label(r: dict) -> str:
        if r["config"] == default:
            return f"**{r['config']}** (default)"
        return f"**{r['config']}**" if r is best else r["config"]

    for r in ordered:
        cells = " | ".join(f"{r[f'hit@{kk}']:.2f}" for kk in K_VALUES)
        lines.append(f"| {label(r)} | {cells} | {r['mrr']:.3f} | {r['avg_latency_ms']} |")
    tie = ""
    if len(tied) > 1:
        why = "default config" if best["config"] == default else "lowest avg ms"
        tie = f" — {len(tied)}-way tie, {why} wins"
    lines += ["", f"Best configuration: **{best['config']}** (Hit@1 {best['hit@1']:.2f}){tie}.", "",
              "## Hit@1 by subset", "",
              "| Configuration | " + " | ".join(JA_SUBSETS) + " |",
              "|---|" + "---|" * len(JA_SUBSETS)]
    for r in ordered:
        lines.append("| " + label(r) + " | " +
                     " | ".join(f"{r['by_subset'].get(c, {}).get('hit@1', 0):.2f}"
                               for c in JA_SUBSETS) + " |")
    for r in results:
        if r["misses"]:
            lines.append(f"\n<details><summary>Misses — {r['config']} ({len(r['misses'])})</summary>\n")
            lines += [f"- `{m['query']}` — expected {m['expected']}, got {m['got']}"
                      for m in r["misses"]]
            lines.append("\n</details>")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--k", type=int, default=5, help="top-k (default: %(default)s)")
    parser.add_argument("--configs", nargs="+", choices=list(ev.IR_CONFIGS),
                        default=list(ev.IR_CONFIGS), help="configurations to run (default: all)")
    args = parser.parse_args()

    gold = ev.load_gold_qrels(JA_SUBSETS)
    print(f"{len(gold)} JA gold queries ({' '.join(JA_SUBSETS)}) x {len(args.configs)} configs\n")

    results = []
    for name in args.configs:
        t0 = time.perf_counter()
        res = run_config(name, ev.IR_CONFIGS[name], gold, args.k)
        results.append(res)
        print(f"{name:34s} hit@1={res['hit@1']:.2f} hit@2={res['hit@2']:.2f} "
              f"hit@5={res['hit@5']:.2f} mrr={res['mrr']:.3f} "
              f"({res['avg_latency_ms']} ms/query, {time.perf_counter() - t0:.0f}s)", flush=True)

    default = ev.default_config_name(args.configs)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "retrieval_eval_ja.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (REPORTS_DIR / "retrieval_eval_ja.md").write_text(
        markdown(results, len(gold), args.k, default), encoding="utf-8")
    print(f"\nSaved → {REPORTS_DIR / 'retrieval_eval_ja.md'}")


if __name__ == "__main__":
    main()
