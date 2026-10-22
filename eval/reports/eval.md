# Evaluation

Reproducible evaluation scripts live in `eval/`; runs write to `eval/results/` (gitignored) — curated headline reports are committed in this directory (`eval/reports/`). See [`README.md`](README.md) in this directory for the index of every report, what it measures, how to regenerate it, and when it was last run. Every report carries its own provenance stamp (generated-at, app version, commit, run configuration) on its first lines and in its JSON `meta` block.

| Script | What it measures | Required setup | Outputs | API calls | Typical runtime |
|---|---|---|---|---|---|
| `eval/eval.py` | Headword Hit@1/2/5 vs gold, **per gold category** (default); `--canon/--pool/--common/--head` sweep; `--report` curated category report; `--modes` text/hybrid/auto; `--ir` Hit@k/MRR/NDCG/MAP grid (optionally per subset, e.g. the Japanese view); `--llm` judge eval | Qdrant running with `jmdict_chunks` indexed (`GROQ_API_KEY` for `--llm` and LLM `--ir` configs) | `eval_headword_*`, `eval_grid_*.csv`, `eval_modes_*`, `retrieval_eval.*`, `llm_eval.*` in `eval/results/`; `--report`/`--publish` write the curated copies here | None for headword/modes/`--ir --no-llm`; Groq otherwise | headword ~30s (360 queries); `--ir` full grid ~2min (6 configs) + ~1min for the LLM config; `--llm` ~4–5min (30 calls/min cap) |
| `eval/embed_model_bench.py` | Dense embedding model throughput and retrieval accuracy (vector-only, in-memory) | `data/processed/chunks.json` and `eval/gold_set.tsv` | `eval/results/embed_model_bench.json` | None | ~20min (first run may download models) |

Runtimes are approximate on a modest CPU with local Qdrant; embedding-model and LLM cold starts can add time on the first run.

**Gold subsets.** `eval/gold_set.tsv` holds **360 queries in 6 categories, exactly 60 per category** — the count is fixed (the file carries a counting rule at the top: add a query, add one to the same category, never move the number), because the per-category rates are denominated by it.

| category | n | what it measures |
|---|---|---|
| `en_words` | 60 | common English nouns/adjectives → Japanese headword |
| `en_verbs` | 60 | "to X" English verb phrases → dictionary-form verb |
| `en_descriptive` | 60 | descriptive/paraphrased English → target word (rewrite path; reported apart from the ranking categories) |
| `ja_words` | 60 | Japanese kanji-form words → exact self-match (indexing completeness) |
| `ja_hiragana` | 60 | hiragana readings → kanji form (preferred) + hiragana self-match |
| `ja_katakana` | 60 | katakana loanwords → self-match |

`--subsets` takes category names and group aliases:

| token | covers |
|---|---|
| *(no flag)* | every category **except** `en_descriptive` — the 300 ranking queries |
| `all` | every category (360) |
| `en-only` | `en_words`, `en_verbs`, `en_descriptive` (180) |
| `ja-only` | `ja_words`, `ja_hiragana`, `ja_katakana` (180) |
| `list` | print the category catalog (counts + one-liners) and exit |

```bash
# the ranking categories (default)
uv run python eval/eval.py

# every category, with the curated per-category report written to eval/reports/
uv run python eval/eval.py --subsets all --report

# one language, or the category catalog
uv run python eval/eval.py --subsets en-only
uv run python eval/eval.py --subsets ja-only
uv run python eval/eval.py --subsets list

# Japanese exact-lookup route (kanji / hiragana / katakana) — dedicated JA report
uv run python eval/eval.py --ir --subsets ja-only --publish --report-name retrieval_eval_ja

# long descriptive queries (exercises the LLM rewrite path when QUERY_REWRITE=auto)
uv run python eval/eval.py --subsets en_descriptive
```

## Headline results — per category

Default config (`mode=auto`, `QUERY_REWRITE=heuristic`, `CANONICAL_BOOST=3.0`, `PREFETCH_MIN=200`, `COMMON_BOOST=1.0`, `HEAD_BONUS=1.5`) against the local collection of 218,786 points — full report: [`headword_eval.md`](headword_eval.md) (machine-readable: `headword_eval.json`):

```
  subset              n          Hit@1    Hit@2    Hit@5
  en_verbs           60   58 (96.7%)   59     60
  en_words           60   56 (93.3%)   59     60
  ja_hiragana        60   58 (96.7%)   60     60
  ja_katakana        60   60 (100.0%)   60     60
  ja_words           60   60 (100.0%)   60     60
  ----------------------------------------------
  en_descriptive     60    9 (15.0%)   13     22
  ----------------------------------------------
  ranking total      300   292 (97.3%)   298     300
```

Hit@1 **97.3%** over the 300 ranking queries, Hit@5 **300/300**, median ~15 ms per query. The Japanese exact-lookup route is at **Hit@1 100%** on `ja_words` and `ja_katakana`. `en_descriptive` is the paraphrase suite — it is a different kind of query and is reported separately (it is where the remaining headroom is).

The eight ranking misses are all synonym ambiguities rather than retrieval failures: `money` (金 above お金), `time` (時 above 時間), `table` (表 above テーブル), `library` (文庫 above 図書館), `to finish` (仕舞う/済む above 終わる), `to turn`, `かわ`, `ゆき`. Every one of them has a valid answer in the top 5.

Run the retrieval benchmark without any paid API calls:

```bash
# vector vs BM25 vs hybrid vs +heuristic rewrite (no LLM calls)
uv run python eval/eval.py --ir --no-llm
```

Run the full grid, including `auto` LLM rewriting (uses Groq quota):

```bash
uv run python eval/eval.py --ir
```

Embedding model benchmark (defaults to the two models in `eval/embed_model_bench.py`; add others with `--models`):

```bash
uv run python eval/embed_model_bench.py
```

LLM prompt evaluation (default 5 sentences; tune with `--sentences N`):

```bash
uv run python eval/eval.py --llm
```

## Other reports in this directory

- **Retrieval-config grid** (`--ir`, all 360 queries): Hit@k / MRR / NDCG / MAP per retrieval mode — default (`auto + rewrite(heuristic)`) **Hit@1 0.84 · Hit@5 0.90 · MRR 0.861**, vs hybrid 0.57, BM25 0.42, dense-only 0.06 — `retrieval_eval.md`
- **JA subsets** of the same grid (180 queries): Hit@1 **1.00** for every hybrid/auto config; BM25 alone 0.79, dense-only 0.00 — `retrieval_eval_ja.md`
- **LLM judge**: level-aware prompts produce much tighter answers (N1 ~39 vs ~152 words generic, less jargon) at comparable judge scores — `llm_eval.md`
- **Embedding models**: `embed_model_bench.json` — the September 4-model run, **not re-run** for 0.8.0 (the dense models are no longer cached and re-embedding them costs ~2 h). It is vector-only and never touches the formula, so the ranking work does not affect it; its `meta` block says so.

Remaining headroom is `en_descriptive` (MRR 0.05–0.30 across configs). A re-ranking stage (local cross-encoder) was evaluated, reduced MRR on this bilingual corpus, and was removed.

**On precision.** The ranking categories are stable run to run (Hit@1 292/300 in every 0.8.0 run). `en_descriptive` jitters by ±1 on Hit@1 between identical runs — its paraphrase queries have near-duplicate candidates and ONNX's float reductions differ slightly between runs, flipping their order. Read its Hit@1 as "≈9/60", not an exact figure.
