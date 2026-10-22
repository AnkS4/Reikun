#!/usr/bin/env python3
"""
Show the full phase breakdown behind a search's latency_ms.

The stats line (auto · ja · N ms · embed X ms · retrieve Y ms …) reads its
fields from SearchResponse.meta; this runs real `search()` calls in a fresh
process — warmup threads never start, so the first compound Japanese query
pays the lazy loads (Sudachi dict, headword trie mmap, ONNX sessions) inline,
the same cold path a first click after boot takes. Each row prints the meta
fields, their sum, and the gap left over inside latency_ms (int truncation,
routing, the headword-hit check).

Usage:
    uv run python local/timing_breakdown.py            # the homepage pills, cold
    uv run python local/timing_breakdown.py 店 犬       # any queries
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.retrieval import search

PHASE_KEYS = ("rewrite_ms", "embed_ms", "retrieve_ms", "segment_ms")

# The homepage pills plus a second ja sentence — the first compound query is
# the cold path, the second shows the warm steady state.
PILLS = [
    "あの店のサービスは素晴らしいです。",
    "train",
    "国",
    "海外",
    "How do you say cheese in Japanese",
    "毎朝七時に起きます。",
]


def main() -> None:
    for q in sys.argv[1:] or PILLS:
        resp = search(q, 10)
        m = dict(resp.meta)
        shown = sum(m.get(k) or 0 for k in PHASE_KEYS)
        phases = " ".join(f"{k.removesuffix('_ms')}={v}ms"
                          for k in PHASE_KEYS if (v := m.get(k)) is not None)
        print(f"{q!r}\n"
              f"  UI  : {resp.mode} · {m.get('route') or '-'} · {resp.latency_ms} ms\n"
              f"  meta: {phases}  (sum {shown} ms, gap {resp.latency_ms - shown} ms)\n"
              f"  rest: {len(resp.results)} results, "
              f"{len(m.get('segments') or ())} segments, cached={m.get('cached', False)}")


if __name__ == "__main__":
    main()
