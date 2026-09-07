#!/usr/bin/env python3
"""
Retrieval evaluation on eval/gold_set.json against the live Qdrant collection.

Compares retrieval approaches (dense-only, BM25-only, hybrid RRF) and the
optional post-processing steps (query rewriting, cross-encoder re-ranking)
using Hit@k, MRR, NDCG, recall, and MAP overall and per query category.

Usage:
    python eval/retrieval_eval.py                      # all configurations
    python eval/retrieval_eval.py --configs vector hybrid
    python eval/retrieval_eval.py --k 5 --no-llm       # skip LLM/Cohere calls

Writes eval/results/retrieval_eval.{json,md}.
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.retrieval import search  # noqa: E402

RESULTS_DIR = ROOT / "eval" / "results"
K_VALUES = (1, 3, 5)

# name → kwargs for app.retrieval.search
CONFIGS: dict[str, dict] = {
    "vector": dict(mode="vector", use_rerank=False, rewrite_mode="off"),
    "text (bm25)": dict(mode="text", use_rerank=False, rewrite_mode="off"),
    "hybrid": dict(mode="hybrid", use_rerank=False, rewrite_mode="off"),
    "hybrid + rewrite(heuristic)": dict(mode="hybrid", use_rerank=False, rewrite_mode="heuristic"),
    "hybrid + rewrite(auto/llm)": dict(mode="hybrid", use_rerank=False, rewrite_mode="auto"),
    "vector + rerank(local)": dict(mode="vector", use_rerank=True, rewrite_mode="off", rerank_backend="local"),
    "hybrid + rerank(local)": dict(mode="hybrid", use_rerank=True, rewrite_mode="off", rerank_backend="local"),
    "hybrid + rewrite + rerank(local)": dict(mode="hybrid", use_rerank=True, rewrite_mode="heuristic", rerank_backend="local"),
    "hybrid + rewrite + rerank(cohere)": dict(mode="hybrid", use_rerank=True, rewrite_mode="heuristic", rerank_backend="cohere"),
    "hybrid + rewrite(auto/llm) + rerank(cohere)": dict(mode="hybrid", use_rerank=True, rewrite_mode="auto", rerank_backend="cohere"),
}


def run_config(name: str, kwargs: dict, gold: list[dict], k: int) -> dict:
    hits = {kk: 0 for kk in K_VALUES}
    ndcg = {kk: 0.0 for kk in K_VALUES}
    recall = {kk: 0.0 for kk in K_VALUES}
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


def to_markdown(results: list[dict], gold_n: int, k: int) -> str:
    cats = sorted({c for r in results for c in r["mrr_by_category"]})
    lines = [
        "# Retrieval evaluation",
        "",
        f"Gold set: {gold_n} queries (`eval/gold_set.json`), top-k = {k}. "
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--configs", nargs="+", choices=list(CONFIGS), default=list(CONFIGS))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--no-llm", action="store_true", help="skip configurations that call the Cohere API (auto rewrite and Cohere rerank)")
    args = parser.parse_args()

    gold = json.loads((ROOT / "eval" / "gold_set.json").read_text(encoding="utf-8"))["queries"]
    if args.no_llm:
        configs = [c for c in args.configs if "auto" not in c and "cohere" not in c]
    else:
        configs = list(args.configs)
    print(f"{len(gold)} gold queries · {len(configs)} configurations\n")

    results = []
    for name in configs:
        t0 = time.perf_counter()
        res = run_config(name, CONFIGS[name], gold, args.k)
        results.append(res)
        print(f"{name:34s} hit@1={res['hit@1']:.2f} hit@5={res['hit@5']:.2f} mrr={res['mrr']:.3f} "
              f"map={res['map']:.3f} ndcg@5={res['ndcg@5']:.3f} "
              f"({res['avg_latency_ms']} ms/query, {time.perf_counter() - t0:.0f}s)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "retrieval_eval.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS_DIR / "retrieval_eval.md").write_text(to_markdown(results, len(gold), args.k), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'retrieval_eval.md'}")


if __name__ == "__main__":
    main()
