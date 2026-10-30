# Descriptive-query model sweep — current Japanese pivot

All rows use the current Japanese-pivot rewrite. 60 `en_descriptive` queries · 218,786-point local collection · `mode=auto` · `QUERY_REWRITE=auto` · `temperature=0`. Sorted by Hit@1, then Hit@2/Hit@5.

Rows are single runs; one-query gaps are within the paraphrase suite's ±1 jitter. Exception: Groq `openai/gpt-oss-20b` is unstable across identical-config re-runs (60 → 21 → 14 Hit@1; this table records the sweep's 21), so treat its row as indicative rather than exact.

Post-2026-10-26: `app/llm.py` sends `chat_template_kwargs.enable_thinking=false` for Nebius (Nemotron reasoning was eating every level's token budget — see the comment there). These rows were measured thinking-on, so re-run the Nebius rows with the current code before treating gaps as real.

Post-2026-10-30: Nebius models migrated to non-deprecated replacements (Token Factory deprecation notice Nov 9, 2026): `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` → `nvidia/Nemotron-3_5-Lightning`, `nvidia/nemotron-3-super-120b-a12b` → `nvidia/Nemotron-3.5-Super-VL`. New models benchmarked on 2026-10-30 with thinking-free configuration. Deprecated models retained in dataset for historical comparison.

| provider | model | Hit@1 | Hit@2 | Hit@5 |
|---|---|---|---|---|
| Groq | `openai/gpt-oss-120b` | 57 (95.0%) | 57 | 57 |
| Nebius | `nvidia/Nemotron-3_5-Lightning` | 56 (93.3%) | 56 | 56 |
| Nebius* | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 56 (93.3%) | 56 | 56 |
| Nebius | `nvidia/Nemotron-3.5-Super-VL` | 55 (91.7%) | 55 | 55 |
| Nebius* | `nvidia/nemotron-3-super-120b-a12b` | 54 (90.0%) | 54 | 54 |
| Cohere | `command-r-plus-08-2024` | 53 (88.3%) | 53 | 54 |
| Cohere | `command-a-plus-05-2026` | 49 (81.7%) | 51 | 52 |
| Gemini | `gemini-3.5-flash-lite` | 46 (76.7%) | 46 | 48 |
| Groq | `openai/gpt-oss-20b` | 21 (35.0%) | 26 | 33 |

*Deprecated by Nebius Token Factory (Nov 9, 2026); retained here for comparison with the replacements (Nemotron-3_5-Lightning, Nemotron-3.5-Super-VL). The historical single-gloss sweep below only lists models actually measured in that pre-pivot mode.

Excluded — `gemini-3.5-flash`: removed from the shipped defaults (see the comment in `app/llm.py`); its free tier allows only 20 requests/day, so the 60-query suite cannot complete. Quota-cut partial runs before removal: 9/60 Hit@1 in the pivot sweep above, 20/60 Hit@1 in the historical single-gloss sweep (16/44 rewrites). All listed rows (both sweeps) completed every rewrite.

## Historical single-gloss sweep (pre-pivot)

| provider | model | Hit@1 | Hit@2 | Hit@5 |
|---|---|---|---|---|
| Groq | `openai/gpt-oss-20b` | 34 (56.7%) | 40 | 49 |
| Nebius* | `nvidia/nemotron-3-super-120b-a12b` | 34 (56.7%) | 39 | 48 |
| Groq | `openai/gpt-oss-120b` | 33 (55.0%) | 40 | 49 |
| Gemini | `gemini-3.5-flash-lite` | 33 (55.0%) | 39 | 50 |
| Cohere | `command-r-plus-08-2024` | 33 (55.0%) | 37 | 45 |
| Cohere | `command-a-plus-05-2026` | 32 (53.3%) | 38 | 47 |
| Nebius* | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 32 (53.3%) | 38 | 47 |

## Heuristic baseline

`heuristic only` — 9/60 Hit@1 · 14/60 Hit@2 · 24/60 Hit@5.

## Regenerate

```bash
uv run python eval/eval.py --subsets en_descriptive
```

Run it again with each provider's model override (`LLM_PROVIDER`, `LLM_MODEL`) and copy the Hit@1/2/5 lines into the table above.
