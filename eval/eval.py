#!/usr/bin/env python3
"""
Unified evaluation entrypoint for Reikun.

`eval/gold_set.tsv` is the single source of truth. Subsets: `en_words` +
`en_verbs` (common English nouns and "to X" verbs), `en_descriptive`
(paraphrase/question-style queries — a different kind of query, so it is
reported apart), and `ja_words` / `ja_hiragana` / `ja_katakana`
(exact-lookup route coverage). The file holds 360 queries, 60 per category —
a fixed count, so the per-category rates stay comparable across runs (see the
counting rule at the top of the file).

`--subsets` takes category names and group aliases:

    (default)   every category except en_descriptive — the 300 ranking queries
    all         every category (360)
    en-only     en_words, en_verbs, en_descriptive
    ja-only     ja_words, ja_hiragana, ja_katakana
    list        print the category catalog (counts + one-liners) and exit

Default suite (no suite flag): the headword benchmark against *current
settings* — no mode/rewrite overrides, so it uses whatever the env configures
(auto route, QUERY_REWRITE). The ranking knobs can be swept in-process;
each is patched per variant and the search cache cleared between them (query
rewrites stay cached, so Groq calls only happen on the first variant).
Omitting a flag keeps the value committed in app/retrieval.py:

    --canon   CANONICAL_BOOST — weight of wf_score x first-sense-gloss match
    --pool    PREFETCH_MIN    — candidates per retrieval arm (recall ceiling)
    --common  COMMON_BOOST    — flat prior on JMdict's is_common/commonness
    --head    HEAD_BONUS      — weight of wf_score x first-gloss (headline
                               translation) match

Other suites (combine freely):

    --modes   fixed text / hybrid / auto comparison, rewrite off (no Groq)
    --ir      retrieval-config suite — Hit@k / MRR / NDCG / MAP / recall over
              relevant entry IDs, overall and per gold subset
    --llm     level-aware vs generic grammar-explanation eval (Groq judge)

Outputs under eval/results/ (headword/mode runs are timestamped so runs never
overwrite each other; the IR and LLM reports keep canonical names):
    eval_headword_<ts>_<variant>.md   per-variant top-5 detail + Hit@1/2/5
    eval_grid_<ts>.csv                query x variant rank of expected
    eval_modes_<mode>_<ts>.md         per-mode top-5 detail + Hit@1/2/5
    retrieval_eval.{md,json}          IR suite report
    llm_eval.{md,json}                LLM judge report
"""

import argparse
import csv
import json
import math
import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_meta import report_meta, stamp_line

import app.retrieval as retrieval
from app.config import COLLECTION, PROC_DIR, QDRANT_URL, QUERY_REWRITE, qdrant_client
from app.retrieval import search

EXAMPLES = """\
examples:
  # the ranking categories (300 queries — everything except en_descriptive)
  uv run python eval/eval.py

  # every category, including the paraphrase suite (360)
  uv run python eval/eval.py --subsets all

  # one language, or one category
  uv run python eval/eval.py --subsets en-only
  uv run python eval/eval.py --subsets ja-only
  uv run python eval/eval.py --subsets ja_hiragana

  # what categories exist
  uv run python eval/eval.py --subsets list

  # curated category report → eval/reports/headword_eval.{md,json}
  uv run python eval/eval.py --report --subsets all

  # ranking-knob sweep (CANONICAL_BOOST x PREFETCH_MIN)
  uv run python eval/eval.py --canon 2 3 --pool 200

  # retrieval-config grid (--no-llm skips the Groq configuration)
  uv run python eval/eval.py --ir --no-llm
  uv run python eval/eval.py --ir --subsets all --publish      # → eval/reports/
  uv run python eval/eval.py --ir --subsets ja-only --publish \\
      --report-name retrieval_eval_ja

  # mode comparison (text / hybrid / auto)
  uv run python eval/eval.py --modes

  # grammar-prompt eval (Groq quota)
  uv run python eval/eval.py --llm --sentences 2
"""

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT
RESULTS_DIR = ROOT / "eval" / "results"
REPORTS_DIR = ROOT / "eval" / "reports"

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
EXPECTED = {q: exp for g in GOLD.values() for q, exp in g.items()}
# query -> gold category (the category-wise report groups by it)
QUERY_CATEGORY = {q: name for name, g in GOLD.items() for q in g}

# Subset selection. `--subsets` takes category names and these group aliases:
#   all      every category
#   en-only  the English categories
#   ja-only  the Japanese categories
#   list     print the catalog (with query counts) and exit
# The default — no --subsets — is every category EXCEPT en_descriptive: the
# paraphrase suite is a different kind of query (a sentence, not a gloss), so
# it is reported apart from the ranking categories rather than mixed into
# their rates.
SUBSET_ALIASES: dict[str, tuple[str, ...]] = {
    "all": tuple(GOLD),
    "en-only": tuple(c for c in GOLD if c.startswith("en_")),
    "ja-only": tuple(c for c in GOLD if c.startswith("ja_")),
}
RANKING_SUBSETS = tuple(c for c in GOLD if c != "en_descriptive")
DEFAULT_SUBSETS = RANKING_SUBSETS


def _category_docs() -> dict[str, str]:
    """One-line description per category, parsed from the gold file's header."""
    docs: dict[str, str] = {}
    for line in (Path(__file__).resolve().parent / "gold_set.tsv").read_text(
            encoding="utf-8").splitlines():
        m = re.match(r"#\s{3}(\w+)\s{2,}(\S.*?)\s*$", line)
        if m and m.group(1) in GOLD:
            docs[m.group(1)] = m.group(2)
    return docs


def print_subset_catalog() -> None:
    """The category catalog — `--subsets list`."""
    docs = _category_docs()
    total = sum(len(v) for v in GOLD.values())
    print(f"\nGold categories — eval/gold_set.tsv ({total} queries in {len(GOLD)} categories)\n")
    for cat in GOLD:
        print(f"  {cat:<16s}{len(GOLD[cat]):>3d}  {docs.get(cat, '')}")
    print(f"\n  default (no --subsets) : every category except en_descriptive "
          f"({sum(len(GOLD[c]) for c in RANKING_SUBSETS)} ranking queries)")
    print(f"  all                    : every category ({total} queries)")
    print(f"  en-only                : {', '.join(SUBSET_ALIASES['en-only'])}")
    print(f"  ja-only                : {', '.join(SUBSET_ALIASES['ja-only'])}")
    print("  list                   : this catalog\n")


def resolve_subsets(tokens: list[str] | None) -> tuple[str, ...]:
    """Resolve --subsets tokens (names + group aliases) to category names."""
    if not tokens:
        return DEFAULT_SUBSETS
    out: list[str] = []
    for token in tokens:
        cats = SUBSET_ALIASES.get(token, (token,))
        for cat in cats:
            if cat not in GOLD:
                valid = ", ".join([*GOLD, *SUBSET_ALIASES, "list"])
                raise SystemExit(f"eval.py: error: unknown subset {cat!r} (choose from: {valid})")
            if cat not in out:
                out.append(cat)
    return tuple(out)


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
    n, median = len(lat), statistics.median(lat)
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

def run_headword(canon: float, pool: int, common: float, head: float, queries: list[str]) -> list[dict]:
    retrieval.CANONICAL_BOOST, retrieval.PREFETCH_MIN = canon, pool
    retrieval.COMMON_BOOST = common
    retrieval.HEAD_BONUS = head
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


def category_summary(rows: list[dict]) -> list[tuple[str, int, int, int, int]]:
    """(category, n, hit1, hit2, hit5) per gold category.

    `en_descriptive` is the long-English paraphrase suite — a different kind of
    query, so it is reported apart from the ranking categories; the ranking
    categories are the ones a headword search is scored on.
    """
    buckets: dict[str, list[dict]] = {}
    for r in rows:
        if not r.get("expected"):
            continue
        buckets.setdefault(QUERY_CATEGORY.get(r["query"], "?"), []).append(r)
    out = []
    for cat in sorted(c for c in buckets if c != "en_descriptive"):
        group = buckets[cat]
        out.append((cat, len(group),
                    sum(1 for r in group if r["rank"] == 1),
                    sum(1 for r in group if 0 < r["rank"] <= 2),
                    sum(1 for r in group if r["rank"] > 0)))
    if "en_descriptive" in buckets:
        group = buckets["en_descriptive"]
        out.append(("en_descriptive", len(group),
                    sum(1 for r in group if r["rank"] == 1),
                    sum(1 for r in group if 0 < r["rank"] <= 2),
                    sum(1 for r in group if r["rank"] > 0)))
    return out


def format_category_table(rows: list[dict]) -> str:
    """The category-wise score block (fixed width, copy-pasteable)."""
    summary = category_summary(rows)
    lines = ["  subset              n          Hit@1    Hit@2    Hit@5"]
    ranking = [s for s in summary if s[0] != "en_descriptive"]
    for cat, n, h1, h2, h5 in ranking:
        lines.append(f"  {cat:<19s}{n:>2d}   {h1:>2d} ({100 * h1 / n:.1f}%)   {h2:>2d}     {h5:>2d}")
    if len(summary) > len(ranking):
        lines.append("  " + "-" * 46)
        cat, n, h1, h2, h5 = summary[-1]
        lines.append(f"  {cat:<19s}{n:>2d}   {h1:>2d} ({100 * h1 / n:.1f}%)   {h2:>2d}     {h5:>2d}")
        lines.append("  " + "-" * 46)
    if ranking:
        n = sum(s[1] for s in ranking)
        h1 = sum(s[2] for s in ranking)
        h2 = sum(s[3] for s in ranking)
        h5 = sum(s[4] for s in ranking)
        lines.append(f"  {'ranking total':<19s}{n:>2d}   {h1:>2d} ({100 * h1 / n:.1f}%)   {h2:>2d}     {h5:>2d}")
    return "\n".join(lines)


def write_category_report(rows: list[dict], meta: dict, out_dir) -> tuple[Path, Path]:
    """Curated category report → eval/reports/headword_eval.{md,json}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = report_meta(**meta)
    summary = category_summary(rows)
    ranking = [s for s in summary if s[0] != "en_descriptive"]
    n = sum(s[1] for s in ranking)
    totals = {
        "hit1": sum(s[2] for s in ranking),
        "hit2": sum(s[3] for s in ranking),
        "hit5": sum(s[4] for s in ranking),
        "n": n,
    }
    lat = [r["latency_ms"] for r in rows]
    md = ["# Headword evaluation — category report\n",
          f"Gold set: {len(rows)} queries (`eval/gold_set.tsv`), "
          f"{summary[0][1] if summary else 0} per category. Hit@k = share of queries whose "
          "expected headword (or an accepted alternative) is in the top k.\n",
          " · ".join(f"{k}={v}" for k, v in meta.items()) + "\n",
          format_category_table(rows) + "\n",
          "\n| subset | n | Hit@1 | Hit@2 | Hit@5 |", "|---|---|---|---|---|"]
    for cat, cn, h1, h2, h5 in summary:
        md.append(f"| {cat} | {cn} | {h1} ({100 * h1 / cn:.1f}%) | {h2} | {h5} |")
    md.append(f"| **ranking total** | **{n}** | **{totals['hit1']} ({100 * totals['hit1'] / n:.1f}%)** "
              f"| **{totals['hit2']}** | **{totals['hit5']}** |")
    md += ["\n## Misses (expected answer not at rank 1)\n"]
    ranking_rows = [r for r in rows if r.get("expected") and r["rank"] != 1
                    and QUERY_CATEGORY.get(r["query"]) != "en_descriptive"]
    desc_rows = [r for r in rows if r.get("expected") and r["rank"] != 1
                 and QUERY_CATEGORY.get(r["query"]) == "en_descriptive"]
    md += ["| subset | query | expected | rank | top hits |", "|---|---|---|---|---|"]
    for r in ranking_rows:
        top = ", ".join(res["headword"] for res in r["results"][:3])
        md.append(f"| {QUERY_CATEGORY.get(r['query'], '?')} | `{r['query']}` | "
                  f"{'/'.join(r['expected'])} | {r['rank'] or '—'} | {top} |")
    if desc_rows:
        md += ["", f"<details><summary>Misses — en_descriptive ({len(desc_rows)})</summary>", "",
               "| query | expected | rank | top hits |", "|---|---|---|---|"]
        for r in desc_rows:
            top = ", ".join(res["headword"] for res in r["results"][:3])
            md.append(f"| `{r['query']}` | {'/'.join(r['expected'])} | {r['rank'] or '—'} | {top} |")
        md += ["", "</details>"]
    md.append("")
    md_path = out_dir / "headword_eval.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    json_path = out_dir / "headword_eval.json"
    json_path.write_text(json.dumps({
        "meta": meta,
        "totals": totals,
        "median_ms": statistics.median(lat) if lat else 0,
        "categories": {cat: {"n": cn, "hit1": h1, "hit2": h2, "hit5": h5}
                       for cat, cn, h1, h2, h5 in summary},
        "queries": {r["query"]: {"category": QUERY_CATEGORY.get(r["query"], "?"),
                                 "rank": r["rank"], "expected": r["expected"],
                                 "latency_ms": r["latency_ms"]} for r in rows},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path


def headword_suite(args) -> None:
    subsets = tuple(args.subsets or DEFAULT_SUBSETS)
    queries = load_queries(subsets)
    combos = [(c, pl, cm, h) for c in args.canon for pl in args.pool
              for cm in args.common for h in args.head]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    points = qdrant_client().count(COLLECTION).count
    print(f"endpoint={QDRANT_URL[:50]} rewrite={QUERY_REWRITE} points={points}")
    print(f"{len(queries)} queries ({' '.join(subsets)}) x {len(combos)} variants …", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    grid: dict[str, dict[tuple, int]] = {q: {} for q in queries}
    summary: dict[tuple, dict] = {}
    labels: dict[tuple, str] = {}
    for canon, pool, common, head in combos:
        key = (canon, pool, common, head)
        label = f"canon{canon:g}_pool{pool}_common{common:g}_head{head:g}"
        labels[key] = label
        print(f"→ CANONICAL_BOOST={canon} PREFETCH_MIN={pool} COMMON_BOOST={common} HEAD_BONUS={head}", flush=True)
        rows = run_headword(canon, pool, common, head, queries)
        meta = {"ts": stamp, "endpoint": QDRANT_URL, "points": points, "mode": "auto",
                "subsets": ",".join(subsets), "rewrite": QUERY_REWRITE,
                "CANONICAL_BOOST": canon, "PREFETCH_MIN": pool,
                "COMMON_BOOST": common, "HEAD_BONUS": head}
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
        print(format_category_table(rows), flush=True)
        if args.report:
            md_out, json_out = write_category_report(rows, meta, REPORTS_DIR)
            print(f"   → curated report: {md_out.relative_to(PROJECT_ROOT)} + {json_out.name}", flush=True)

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
# Mode comparison — text / hybrid / auto, rewrite off (no Groq calls).
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

K_VALUES = (1, 2, 3, 5)

IR_CONFIGS: dict[str, dict] = {
    "vector": {"mode": "vector", "rewrite_mode": "off"},
    "text (bm25)": {"mode": "text", "rewrite_mode": "off"},
    "hybrid": {"mode": "hybrid", "rewrite_mode": "off"},
    "hybrid + rewrite(heuristic)": {"mode": "hybrid", "rewrite_mode": "heuristic"},
    "auto + rewrite(heuristic)": {"mode": "auto", "rewrite_mode": "heuristic"},
    "hybrid + rewrite(auto/llm)": {"mode": "hybrid", "rewrite_mode": "auto"},
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
        # Per-category hits as well as MRR — the JA view (ja_words /
        # ja_hiragana / ja_katakana) and the per-category tables come from
        # these, so one run answers both questions.
        cat = per_cat.setdefault(g["category"], {"hits": dict.fromkeys(K_VALUES, 0), "rr": []})
        for kk in K_VALUES:
            cat["hits"][kk] += int(any(r <= kk for r in ranks))
        cat["rr"].append(rr)
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
        "mrr_by_category": {c: round(sum(v["rr"]) / len(v["rr"]), 3) for c, v in per_cat.items()},
        "hits_by_category": {
            c: {f"hit@{kk}": round(v["hits"][kk] / len(v["rr"]), 3) for kk in K_VALUES}
            for c, v in per_cat.items()},
        "avg_latency_ms": int(sum(latency) / len(latency)),
        "misses": misses,
    }


def default_config_name(configs: list[str]) -> str | None:
    """Config matching production defaults — mode=auto (search() default) and
    rewrite_mode=QUERY_REWRITE (env). None when it isn't among `configs`."""
    want = {"mode": "auto", "rewrite_mode": QUERY_REWRITE}
    return next((n for n in configs if IR_CONFIGS[n] == want), None)


def ir_markdown(results: list[dict], gold_n: int, k: int, default: str | None,
                meta: dict | None = None, title: str = "Retrieval evaluation",
                note: str = "") -> str:
    cats = sorted({c for r in results for c in r["mrr_by_category"]})
    cat_headers = " | ".join(f"MRR {c}" for c in cats)
    lines = [
        f"# {title}",
        "",
        f"Gold set: {gold_n} queries (`eval/gold_set.tsv`), top-k = {k}. "
        "Hit@k = share of queries with a relevant entry in the top k; MRR = mean reciprocal rank; "
        "NDCG = normalized discounted cumulative gain; MAP = mean average precision over all relevant IDs.",
    ]
    if note:
        lines.append(note)
    lines.append("")
    if meta:
        lines += [stamp_line(meta), ""]
    lines += [
        f"| Configuration | Hit@1 | Hit@2 | Hit@3 | Hit@5 | MRR | NDCG@5 | MAP | R@5 | avg ms | {cat_headers} |",
        "|---|" + "---|" * (9 + len(cats)),
    ]
    # Production default pinned to the top row; the rest keep run order.
    ordered = sorted(results, key=lambda r: r["config"] != default)
    # Best = top (mrr, hit@1); ties go to the default config, else lowest latency.
    top = max((r["mrr"], r["hit@1"]) for r in results)
    tied = [r for r in results if (r["mrr"], r["hit@1"]) == top]
    best = next((r for r in tied if r["config"] == default),
                min(tied, key=lambda r: r["avg_latency_ms"]))

    def label(r: dict) -> str:
        if r["config"] == default:
            return f"**{r['config']}** (default)"
        return f"**{r['config']}**" if r is best else r["config"]

    for r in ordered:
        cat_cells = " | ".join(f"{r['mrr_by_category'].get(c, 0):.2f}" for c in cats)
        lines.append(
            f"| {label(r)} | {r['hit@1']:.2f} | {r['hit@2']:.2f} | {r['hit@3']:.2f} | {r['hit@5']:.2f} | "
            f"{r['mrr']:.3f} | {r['ndcg@5']:.3f} | {r['map']:.3f} | {r['recall@5']:.2f} | "
            f"{r['avg_latency_ms']} | {cat_cells} |"
        )
    tie = ""
    if len(tied) > 1:
        why = "default config" if best["config"] == default else "lowest avg ms"
        tie = f" — {len(tied)}-way tie, {why} wins"
    lines += ["", f"Best configuration: **{best['config']}** (MRR {best['mrr']:.3f}){tie}.", ""]

    # Per-category Hit@1 — the JA view used to be a separate script for this
    # table; now it falls out of the same run.
    lines += ["## Hit@1 by category", "",
              "| Configuration | " + " | ".join(cats) + " |", "|---|" + "---|" * len(cats)]
    for r in ordered:
        lines.append("| " + label(r) + " | " +
                     " | ".join(f"{r.get('hits_by_category', {}).get(c, {}).get('hit@1', 0):.2f}"
                                for c in cats) + " |")
    lines.append("")

    for r in results:
        if r["misses"]:
            lines.append(f"<details><summary>Misses — {r['config']} ({len(r['misses'])})</summary>\n")
            lines += [f"- `{m['query']}` → `{m['rewritten']}` → got {m['got']}" for m in r["misses"]]
            lines.append("\n</details>\n")
    return "\n".join(lines)


def ir_suite(args) -> None:
    subsets = tuple(args.subsets or GOLD)  # IR suite covers all subsets by default
    gold = load_gold_qrels(subsets)
    if args.no_llm:
        configs = [c for c in args.configs if "auto/llm" not in c]
    else:
        configs = list(args.configs)
    print(f"{len(gold)} gold queries ({' '.join(subsets)}) · {len(configs)} configurations\n")

    results = []
    for name in configs:
        t0 = time.perf_counter()
        res = run_ir_config(name, IR_CONFIGS[name], gold, args.k)
        results.append(res)
        print(f"{name:34s} hit@1={res['hit@1']:.2f} hit@5={res['hit@5']:.2f} mrr={res['mrr']:.3f} "
              f"map={res['map']:.3f} ndcg@5={res['ndcg@5']:.3f} "
              f"({res['avg_latency_ms']} ms/query, {time.perf_counter() - t0:.0f}s)")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    meta = report_meta(endpoint=QDRANT_URL, points=qdrant_client().count(COLLECTION).count,
                       gold_queries=len(gold), top_k=args.k, subsets=",".join(subsets),
                       configs=",".join(configs), default_config=default_config_name(configs))
    # A Japanese-only run is the JA view of the same grid — same renderer, a
    # subset of the gold set and a different title.
    ja_only = set(subsets) <= {"ja_words", "ja_hiragana", "ja_katakana"}
    title = "Retrieval evaluation — Japanese subsets" if ja_only else "Retrieval evaluation"
    note = ("Companion to `retrieval_eval.md` (all 360 queries, per-category MRR only)."
            if ja_only else "")
    md = ir_markdown(results, len(gold), args.k, default_config_name(configs), meta, title, note)
    (RESULTS_DIR / "retrieval_eval.json").write_text(
        json.dumps({"meta": meta, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (RESULTS_DIR / "retrieval_eval.md").write_text(md, encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'retrieval_eval.md'}")
    if args.publish:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / f"{args.report_name}.json").write_text(
            json.dumps({"meta": meta, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
        (REPORTS_DIR / f"{args.report_name}.md").write_text(md, encoding="utf-8")
        print(f"Published → {REPORTS_DIR / (args.report_name + '.md')}")


# ---------------------------------------------------------------------------
# LLM suite — level-aware vs generic grammar prompt, Groq judge (opt-in).
# ---------------------------------------------------------------------------

LEVELS = ("N5", "N1")
PROMPTS = {"level-aware": True, "generic": False}

# Groq free tier caps at 30 RPM per model. Each eval row makes two calls on
# the primary pool (generation + judge), so we pace under that.
_LLM_MAX_CALLS_PER_MIN = 25
_LLM_MIN_INTERVAL = 60.0 / _LLM_MAX_CALLS_PER_MIN
_last_llm_call = 0.0

FALLBACK_SENTENCES = [
    {"japanese": "私は毎日日本語を勉強します。", "english": "I study Japanese every day."},
    {"japanese": "昨日、友達と映画を見に行きました。", "english": "Yesterday I went to watch a movie with a friend."},
    {"japanese": "日本語を勉強するのは楽しいです。", "english": "Studying Japanese is fun."},
    {"japanese": "彼の意見には賛成できない。", "english": "I cannot agree with his opinion."},
    {
        "japanese": "いかに困難であろうとも、最後までやり遂げなければならない。",
        "english": "No matter how difficult it may be, we must carry it through to the end.",
    },
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


def _llm_wait() -> None:
    """Sleep just enough to stay within the per-model rate limit."""
    global _last_llm_call
    if _last_llm_call:
        elapsed = time.perf_counter() - _last_llm_call
        if elapsed < _LLM_MIN_INTERVAL:
            time.sleep(_LLM_MIN_INTERVAL - elapsed)


def judge(sentence: str, level: str, explanation: str) -> dict:
    from app.grammar_explain import chat
    user = f"Learner level: {level}\nSentence: {sentence}\n\nExplanation:\n{explanation}"
    raw = chat(JUDGE_SYSTEM, user, max_tokens=900)  # cap must cover gpt-oss reasoning + the JSON verdict
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
                global _last_llm_call
                _llm_wait()
                t0 = time.perf_counter()
                text = explain_grammar(s["japanese"], s["english"], level, level_aware=level_aware)
                _last_llm_call = time.perf_counter()
                gen_ms = int((time.perf_counter() - t0) * 1000)
                _llm_wait()
                verdict = judge(s["japanese"], level, text)
                _last_llm_call = time.perf_counter()
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


def llm_markdown(rows: list[dict], summary: list[dict], meta: dict | None = None) -> str:
    lines = [
        "# LLM evaluation — level-aware vs generic grammar prompt",
        "",
        f"{len(rows) // (len(LEVELS) * len(PROMPTS))} sentences x levels {', '.join(LEVELS)} x 2 prompts. "
        "Judge = Groq (blind to prompt variant), scores 1-5.",
        "",
    ]
    if meta:
        lines += [stamp_line(meta), ""]
    lines += [
        "| Level | Prompt | avg words | avg jargon terms | analogy rate | judge: level fit | judge: accuracy |",
        "|---|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| {s['level']} | {s['prompt']} | {s['avg_words']} | {s['avg_jargon']} | {s['analogy_rate']:.0%} | "
        f"{s['judge_level_fit']} | {s['judge_accuracy']} |"
        for s in summary
    )
    lines += ["", "## Side-by-side outputs", ""]
    for sent in dict.fromkeys(r["sentence"] for r in rows):
        lines.append(f"### {sent}\n")
        for level in LEVELS:
            for prompt in PROMPTS:
                r = next(x for x in rows if x["sentence"] == sent and x["level"] == level and x["prompt"] == prompt)
                summary_line = (
                    f"**{level} · {prompt}** — fit {r['level_fit']}/5, accuracy {r['accuracy']}/5, "
                    f"{r['words']} words, {r['jargon_terms']} jargon terms · *{r.get('comment', '')}*"
                )
                lines += [summary_line, "", r["explanation"], ""]
    return "\n".join(lines)


def llm_suite(args) -> None:
    sentences = load_sentences(args.sentences)
    print(f"{len(sentences)} sentences x {LEVELS} x {list(PROMPTS)}\n")
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
    meta = report_meta(model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
                       judge="groq", sentences=len(rows) // (len(LEVELS) * len(PROMPTS)))
    (RESULTS_DIR / "llm_eval.json").write_text(
        json.dumps({"meta": meta, "rows": rows, "summary": summary}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (RESULTS_DIR / "llm_eval.md").write_text(llm_markdown(rows, summary, meta), encoding="utf-8")
    print(f"\nSaved → {RESULTS_DIR / 'llm_eval.md'}")


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    parser.add_argument("--subsets", nargs="+", default=None,
                        choices=[*GOLD, *SUBSET_ALIASES, "list"], metavar="NAME",
                        help="gold categories to evaluate — names, or the aliases "
                             "all / en-only / ja-only / list. Default: every category "
                             "except en_descriptive (the ranking categories)")
    parser.add_argument("--report", action="store_true",
                        help="write the curated category report to eval/reports/headword_eval.{md,json} "
                             "(add --subsets all to include the paraphrase suite)")
    parser.add_argument("--canon", type=float, nargs="+", default=[retrieval.CANONICAL_BOOST],
                        help="CANONICAL_BOOST values to sweep (default: committed %(default)s)")
    parser.add_argument("--pool", type=int, nargs="+", default=[retrieval.PREFETCH_MIN],
                        help="PREFETCH_MIN values to sweep (default: committed %(default)s)")
    parser.add_argument("--common", type=float, nargs="+", default=[retrieval.COMMON_BOOST],
                        help="COMMON_BOOST values to sweep (default: committed %(default)s)")
    parser.add_argument("--head", type=float, nargs="+", default=[retrieval.HEAD_BONUS],
                        help="HEAD_BONUS values to sweep (default: committed %(default)s)")
    parser.add_argument("--modes", action="store_true",
                        help="run the text/hybrid/auto mode comparison (rewrite off)")
    parser.add_argument("--ir", action="store_true",
                        help="run the retrieval-config IR suite (Hit@k/MRR/NDCG/MAP)")
    parser.add_argument("--publish", action="store_true",
                        help="--ir: also write the report to eval/reports/ (the committed copy)")
    parser.add_argument("--report-name", default="retrieval_eval",
                        help="--ir --publish: basename for the committed report (default: %(default)s)")
    parser.add_argument("--configs", nargs="+", choices=list(IR_CONFIGS), default=list(IR_CONFIGS),
                        help="--ir configurations to run (default: all)")
    parser.add_argument("--k", type=int, default=5, help="--ir top-k (default: %(default)s)")
    parser.add_argument("--no-llm", action="store_true",
                        help="--ir: skip configurations that call the Groq API")
    parser.add_argument("--llm", action="store_true",
                        help="run the grammar-explanation LLM-judge eval")
    parser.add_argument("--sentences", type=int, default=5,
                        help="--llm: sentences to evaluate (default: %(default)s)")
    args = parser.parse_args()

    if args.subsets and "list" in args.subsets:
        print_subset_catalog()
        return
    # One resolution for every suite: names + aliases → category names.
    args.subsets = resolve_subsets(args.subsets)

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
