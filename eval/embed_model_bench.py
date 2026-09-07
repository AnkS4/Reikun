#!/usr/bin/env python3
"""
Compare candidate dense embedding models on the gold set (vector-only, in-memory).

This is a one-off model-selection benchmark, independent of Qdrant: every
candidate embeds the full ingest subset of chunks.json, then we measure
Hit@k / MRR for the gold queries by brute-force cosine similarity.

Usage:
    python eval/embed_model_bench.py
    python eval/embed_model_bench.py --models sentence-transformers/all-MiniLM-L6-v2 snowflake/snowflake-arctic-embed-xs
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from app.embedder import CACHE_DIR  # noqa: E402
from scripts.ingest import load_chunks  # noqa: E402

DEFAULT_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "snowflake/snowflake-arctic-embed-xs",
]
K_VALUES = (1, 3, 5, 10)


def evaluate(model_name: str, chunks: list[dict], gold: list[dict]) -> dict:
    model = TextEmbedding(model_name, cache_dir=CACHE_DIR)
    ids = np.array([int(c["id"]) for c in chunks])

    t0 = time.perf_counter()
    docs = np.array(list(model.embed([c["text"] for c in chunks], batch_size=256)), dtype=np.float32)
    embed_s = time.perf_counter() - t0
    docs /= np.linalg.norm(docs, axis=1, keepdims=True)

    queries = np.array(list(model.query_embed([g["query"] for g in gold])), dtype=np.float32)
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)

    hits = {k: 0 for k in K_VALUES}
    rr_sum = 0.0
    per_category: dict[str, list[float]] = {}
    for g, qvec in zip(gold, queries):
        top = ids[np.argsort(-(docs @ qvec))[: max(K_VALUES)]].tolist()
        rank = next((i for i, pid in enumerate(top, 1) if pid in g["relevant_ids"]), None)
        for k in K_VALUES:
            hits[k] += int(rank is not None and rank <= k)
        rr = 1.0 / rank if rank else 0.0
        rr_sum += rr
        per_category.setdefault(g["category"], []).append(rr)

    n = len(gold)
    return {
        "model": model_name,
        "embed_seconds": round(embed_s, 1),
        "docs_per_second": round(len(chunks) / embed_s, 1),
        **{f"hit@{k}": round(hits[k] / n, 3) for k in K_VALUES},
        "mrr": round(rr_sum / n, 3),
        "mrr_by_category": {c: round(sum(v) / len(v), 3) for c, v in per_category.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "results" / "embed_model_bench.json")
    args = parser.parse_args()

    chunks = load_chunks(ingest_all=False)
    gold = json.loads((ROOT / "eval" / "gold_set.json").read_text(encoding="utf-8"))["queries"]
    print(f"{len(chunks):,} chunks, {len(gold)} gold queries\n")

    results = []
    for name in args.models:
        print(f"→ {name}", flush=True)
        res = evaluate(name, chunks, gold)
        results.append(res)
        print(f"   {res['embed_seconds']}s ({res['docs_per_second']}/s)  "
              f"hit@1={res['hit@1']}  hit@5={res['hit@5']}  mrr={res['mrr']}  {res['mrr_by_category']}\n")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved → {args.out}")


if __name__ == "__main__":
    main()
