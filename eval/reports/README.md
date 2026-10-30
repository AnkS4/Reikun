# Curated evaluation reports

Six report families. Five have a Markdown twin and a machine-readable JSON twin; the embedding family is JSON-only — hence eleven files. Every report carries its own provenance stamp on the first lines (and in the JSON `meta` block):

```
generated=<YYYY-MM-DD HH:MM UTC> · version=<app version> · commit=<git sha>[+dirty] · <run configuration>
```

`version` is the release version from `pyproject.toml`; `commit` is the short git SHA (`+dirty` = the worktree differed from it when the report was produced).

| report | files | what it measures | regenerate with |
|---|---|---|---|
| **Headword (category report)** | `headword_eval.md` · `headword_eval.json` | Hit@1/2/5 per gold category on the 360-query set — the headline ranking number | `uv run python eval/eval.py --subsets all --report` |
| **Retrieval grid** | `retrieval_eval.md` · `retrieval_eval.json` | Hit@k / MRR / NDCG / MAP per retrieval mode (vector, BM25, hybrid, auto) over all 360 queries | `uv run python eval/eval.py --ir --subsets all --publish` (add `--no-llm` to skip the Groq config) |
| **JA subsets** | `retrieval_eval_ja.md` · `retrieval_eval_ja.json` | the same grid over the 180 Japanese exact-lookup queries | `uv run python eval/eval.py --ir --subsets ja-only --publish --report-name retrieval_eval_ja` |
| **LLM judge** | `llm_eval.md` · `llm_eval.json` | level-aware vs generic grammar prompts, judged by Groq | `uv run python eval/eval.py --llm` |
| **Embedding models** | `embed_model_bench.json` | dense-model throughput and vector-only retrieval accuracy | `uv run python eval/embed_model_bench.py` (JSON only — no markdown twin) |
| **Descriptive model sweep** | `descriptive_models.md` · `descriptive_models.json` | Hit@1/2/5 across the 60 descriptive queries for every shipped provider/model pair (current Japanese pivot) | per provider/model: `uv run python eval/eval.py --subsets en_descriptive` |

One script drives the two retrieval reports: the JA view is the same IR suite over a slice of the same gold set, so `--subsets ja-only` + `--publish` produces it from the same code path. `uv run python eval/eval.py --subsets list` prints the category catalog.

Plus `eval.md` in this directory: how to run everything, and what each number means.

**Which reports are current.** The retrieval reports (headword, grid, JA), the LLM judge report, and the descriptive-model sweep were regenerated for 0.8.0; the sweep's Nebius rows were refreshed for 1.0.2 when the deprecated Token Factory models were replaced. `embed_model_bench.json` is the **September run, not re-run** — the four dense models it compares are no longer in the local cache and re-embedding them costs ~2 h, so it is kept as the original measurement with a note saying so (see its `meta` block). The retrieval-formula work does not affect it: it is vector-only, in-memory, and never touches the FormulaQuery.

**On the numbers.** The ranking categories are stable run to run (Hit@1 292/300 in every run since 0.8.0). `en_descriptive` jitters by ±1 on Hit@1 between identical runs — the paraphrase queries have near-duplicate candidates (浴室/お風呂/浴場), and ONNX's float reductions differ slightly between runs, which flips their order. Treat its default heuristic Hit@1 as "≈9/60", not an exact figure. With `QUERY_REWRITE=auto`, the current Japanese-pivot rewrite is reported separately in the descriptive-model sweep; see [`descriptive_models.md`](descriptive_models.md).
