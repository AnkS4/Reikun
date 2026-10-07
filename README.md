<p align="center">
  <a href="https://reikun.app/">
    <img src="docs/logos/icon-rei-lens.png" alt="Reikun logo" width="128">
  </a>
</p>

<h1 align="center">Reikun (例訓) — Semantic Japanese Dictionary</h1>

<p align="center">
  A Japanese reading assistant — search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji, and get grammar explanations tuned to your JLPT level.
</p>

<p align="center">
  <a href="https://github.com/AnkS4/Reikun/releases">
    <img src="https://img.shields.io/github/v/release/AnkS4/Reikun?style=flat&color=8b5cf6" alt="Release">
  </a>
  <a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/AnkS4/Reikun?style=flat&color=00a86b" alt="License">
  </a>
  <a href="https://reikun.app/">
    <img src="https://img.shields.io/badge/Try_it_live-reikun.app-3a86ff?style=flat" alt="Try it live">
  </a>
</p>

## Demo

![Reikun demo — search, grammar explanation, kanji tooltip and card, sentence breakdown](docs/videos/demo_v3.gif)

Full recording: [docs/videos/demo_v3.mp4](docs/videos/demo_v3.mp4)

## Features

- **Hybrid Search with query routing**: Dense vector embeddings (FastEmbed) + BM25 sparse vectors fused server-side in Qdrant (RRF). `mode=auto` routes the query: Japanese → BM25 + exact match, English word → hybrid + commonness prior, English sentence → dense-weighted fusion.
- **Query Rewriting**: Natural-language questions ("how do you say hospital") are normalised to dictionary glosses before retrieval — free regex heuristics by default, optional Groq LLM rewriting for descriptive queries
- **Sentence Breakdown**: Paste Japanese text and Sudachi splits it into word units — furigana on top, gloss underneath, full breakdown on hover. Inflection tails merge into single chips and adjacent segments re-resolve into JMdict compounds
- **Kanji Lookup**: Deterministic kanji information (no LLM) — stroke-order diagrams (KanjiVG), readings, meanings, and common compound words
- **Grammar Explanations**: AI-generated grammar explanations calibrated to your JLPT level (N5–N1) via Groq, on demand only, with a smaller fallback model if the primary is exhausted
- **Feedback & Telemetry**: Thumbs-up/down feedback and query telemetry as JSON events (stdout sink, picked up by platform logs) or a local SQLite file; search queries are logged verbatim (feedback/explanation text stays SHA-256-only) and rows are kept indefinitely
- **Interface**: Search-first landing page, furigana (`<ruby>`) headwords, animated stroke order, light/dark themes, shareable URLs (`?q=猫&level=N3`), one-click level-aware grammar explanations
- **HTTP API**: FastAPI layer (`app/api.py`) over the same pipeline — standalone uvicorn service with routes at the root (what the Docker image serves); includes SSE streaming for explanations and JSON-shaped rendering (ruby parts, kanji card, segment chips, stroke data) for the web frontend

## Tech Stack

- **Frontend**: SvelteKit static SPA (`web/`, adapter-static); Inter + Noto Sans JP web fonts
- **API**: FastAPI + Uvicorn (the production serving process; one worker)
- **Vector Database**: Qdrant (named dense + sparse vectors, server-side RRF hybrid)
- **Embeddings**: FastEmbed — `all-MiniLM-L6-v2` (dense, 384-dim) + `Qdrant/bm25` (sparse), ONNX-quantized for CPU
- **LLM**: Groq `openai/gpt-oss-120b` (→ `gpt-oss-20b` fallback) — grammar explanations, optional query rewriting, LLM-judged evals (all token-budgeted)
- **Ingestion pipeline**: `scripts/startup.py` can run wait-for-Qdrant → check-state → download → build → ingest with retries, then launch the app — opt-in via `INGEST_VIA_DOCKER=1` or `--ingest` (off by default; `--ingest-only` runs it without launching the API server). Populated collections get an incremental top-up instead — rsync delta + upsert of new/edited entries only
- **Monitoring**: JSON event telemetry (`app/telemetry.py`; optional SQLite sink in `scripts/feedback_log.py`)
- **Data Sources**: JMdict, KANJIDIC2, Tatoeba Corpus, KanjiVG
- **Containerization**: Docker & Docker Compose

## Installation

### Prerequisites

- **Docker and Docker Compose** (recommended path — runs the app + Qdrant)
- **Groq API key** — powers grammar explanations and optional LLM query rewriting; search and kanji lookup work without it
- **Git** (to clone) and ~3 GB free disk (dictionary data + embedding models)
- Local development only: **Python 3.13+** and **[uv](https://docs.astral.sh/uv/)** (dependency manager — `pip` works too)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AnkS4/Reikun
   cd Reikun
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

### Running the Application

#### Option 1: Docker (Recommended)

First run — let the container self-provision and ingest all ~219k entries at boot (embedding takes ~1 hr):

```bash
INGEST_VIA_DOCKER=1 docker compose up -d --build
```

(or set `INGEST_VIA_DOCKER=1` in `.env` for the same effect on every `docker compose up --build`)

Once Qdrant is populated, plain `up` serves whatever it already holds:

```bash
docker compose up -d        # API at http://localhost:8000 (or APP_PORT), Swagger docs at /docs
docker compose logs -f app
docker compose down
```

The frontend is the SvelteKit app in `web/` (see Option 2, step 6, to run it against the local API).

#### Option 2: Local Development

For local development without Docker:

1. **Install Python dependencies** (creates `.venv` and installs locked deps):
   ```bash
   uv sync
   ```

2. **Download and process data**:
   ```bash
   uv run python scripts/download_edrdg.py    # JMdict NG + KANJIDIC2 XML from EDRDG (needs rsync)
   uv run python scripts/download_kanjivg.py  # KanjiVG stroke-order SVGs
   uv run python scripts/build_chunks.py      # parse + chunk → data/processed/
   ```

3. **Start Qdrant**:
   ```bash
   docker compose up -d qdrant
   ```

4. **Ingest data into Qdrant** (~219k entries; `--common` loads a ~37k quick-test subset; cached in `data/`):
   ```bash
   QDRANT_HOST=localhost uv run python scripts/ingest.py
   ```

5. **Run the HTTP API** — the same FastAPI app the Docker image serves (`app/api.py`, routes at the root):
   ```bash
   uv run uvicorn app.api:app --reload          # Swagger UI at http://localhost:8000/docs
   ```

6. **Run the SvelteKit web frontend** (`web/` — needs the API running from step 5):
   ```bash
   cd web && npm install && npm run dev     # dev server → http://localhost:5173
   npm run check                            # svelte-check type diagnostics
   npm run build                            # static build → web/build/ (adapter-static)
   ```

   The API base URL is baked in at build time via `PUBLIC_API_BASE` (default `http://localhost:8000`; schema in `web/src/env.ts`, see `web/.env.example`). The static output deploys to any static host as-is.

7. **(Optional) Lint + tests** (CI runs the same — `.github/workflows/ci.yml`):
   ```bash
   uv run ruff check .
   uv run pytest -q                        # API + telemetry tests; no Qdrant needed
   ```

### URL parameters

The Search page keeps its state in the URL, so results are shareable and the browser back button works:

| Param | Example | Meaning |
|---|---|---|
| `q` | `?q=食べる` | Runs the search on load |
| `level` | `?level=N3` | JLPT level used for grammar explanations (remembered until changed) |
| `kanji` | `?kanji=猫` | Legacy deep link — redirects to a single-kanji `?q=` search |

## Project Structure

```
Reikun/
├── app/
│   ├── config.py            # Central env-driven configuration
│   ├── api.py               # FastAPI app — the serving entrypoint (/search, /kanji, /explain, /feedback, /health, /ready)
│   ├── render.py            # UI-agnostic JSON shaping (ruby parts, kanji card, chips, stroke data)
│   ├── telemetry.py         # Event logging interface (stdout JSON default, optional SQLite sink)
│   ├── retrieval.py         # Vector / BM25 / hybrid search, routing, ja sentence segmentation
│   ├── headword_index.py    # marisa-trie headword index (form → entries) for segmentation
│   ├── query_rewrite.py     # Heuristic + optional LLM query rewriting
│   ├── kanji_lookup.py      # Deterministic KANJIDIC2 + KanjiVG lookup
│   ├── grammar_explain.py   # Groq client (primary→fallback chain), JLPT-level-aware prompts
│   └── embedder.py          # FastEmbed dense/sparse model wrappers
├── web/                     # SvelteKit static frontend (adapter-static → web/build/)
│   ├── src/routes/          # /  (search SPA shell)
│   ├── src/lib/             # openapi-fetch client (typed from openapi.d.ts), kanji-hover cache, theme
│   ├── src/env.ts           # PUBLIC_API_BASE schema — build-time public env var
│   └── wrangler.jsonc       # static-assets deploy config (SPA fallback)
├── docs/
│   ├── api/                 # Committed openapi.json (frontend type generation; CI drift check)
│   ├── logos/               # Reikun logo assets (png/svg)
│   ├── screenshots/         # UI captures (search, kanji card)
│   └── videos/              # Demo recording (gif + mp4)
├── eval/
│   ├── gold_set.tsv         # gold set — en_words/en_verbs (default), en_descriptive, ja_*
│   ├── eval.py              # unified eval: headword bench + knob sweep (default), --modes, --ir, --llm
│   ├── eval_ja.py           # JA-subset Hit@k report → eval/reports/retrieval_eval_ja.*
│   ├── embed_model_bench.py # dense embedding model benchmark
│   ├── reports/             # curated headline reports (committed)
│   └── results/             # generated run outputs (gitignored)
├── scripts/
│   ├── download_edrdg.py    # Sync JMdict NG + KANJIDIC2 XML from EDRDG (rsync)
│   ├── download_kanjivg.py  # Download KanjiVG stroke-order SVGs (packs strokes.json)
│   ├── feedback_log.py      # SQLite telemetry sink (searches, feedback, kanji lookups, explanations)
│   ├── build_chunks.py      # Parse and chunk dictionary data
│   ├── ingest.py            # Embed (dense + sparse) and load into Qdrant
│   ├── cloud_ingest.py      # Snapshot-transfer a local collection to Qdrant Cloud
│   ├── export_openapi.py    # Write docs/api/openapi.json for frontend type generation
│   └── startup.py           # Container entrypoint (execs uvicorn) + opt-in ingestion pipeline
├── .env.example             # Environment variable template
├── data/
│   ├── raw/                 # Downloaded dictionary files
│   ├── processed/           # Parsed chunks, kanji table, packed stroke data (strokes.json)
│   ├── kanjivg/             # Stroke-order SVGs (build input only; not shipped)
│   └── monitoring/          # SQLite telemetry database
├── models/                  # Cached embedding models (local runs; Docker uses a named volume)
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml.example  # optional host-specific overrides (e.g. DNS)
├── pyproject.toml           # pinned deps + ingest/dev dep groups
└── uv.lock                  # locked resolution (uv sync --frozen)
```

## Environment Variables

Create a `.env` file (see `.env.example`):

- `APP_PORT`: Port the API container is published on (default: 8000)
- `GROQ_API_KEY`: Required for grammar explanations (get at https://console.groq.com/keys)
- `LLM_MODEL` / `LLM_MODEL_FALLBACK`: Groq chat models — primary and failover (defaults: `openai/gpt-oss-120b` / `openai/gpt-oss-20b`)
- `QDRANT_HOST` / `QDRANT_PORT`: Qdrant connection (defaults: localhost / 6333); `QDRANT_URL` + `QDRANT_API_KEY` override for Qdrant Cloud
- `QDRANT_COLLECTION`: Qdrant collection name (default: jmdict_chunks)
- `EMBED_MODEL`: Dense embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `QUERY_REWRITE`: `heuristic` (default, free), `auto` (adds one Groq call for long English queries — best MRR but uses free-tier quota), or `off`

### Groq free-tier notes

Tuned for the free tier (30 RPM / ~1,000 requests/day *per model*): explanations are on-demand only with bounded token budgets, and 429s honor the API's `retry-after` within a small retry budget. Rate limits are per-model, so when the primary's daily cap is exhausted requests automatically fail over to `LLM_MODEL_FALLBACK`; if both are down the API returns 502 rather than a fabricated answer. `QUERY_REWRITE=auto` adds one call per long English query — heuristic rewriting is the free default.

## Port Configuration

| Service     | Container | Host (Docker)                | Host (Local) |
|-------------|-----------|------------------------------|--------------|
| HTTP API    | 8000      | `APP_PORT` (default: 8000)   | 8000 (`uvicorn app.api:app`) |
| Qdrant      | 6333      | 6333                         | 6333         |
| Qdrant gRPC | 6334      | 6334                         | 6334         |

Docker maps `127.0.0.1:${APP_PORT:-8000}:8000` — change `APP_PORT` in `.env`, then `docker compose up -d`. All host ports are bound to loopback only (Qdrant has no auth by default), so nothing is reachable from the LAN; the app reaches Qdrant over the internal compose network.

## Evaluation

Reproducible evaluation scripts live in `eval/`; runs write to `eval/results/` (gitignored) — curated headline reports are committed in `eval/reports/`.

| Script | What it measures | Required setup | Outputs | API calls | Typical runtime |
|---|---|---|---|---|---|
| `eval/eval.py` | Headword Hit@1/2/5 vs gold (default); `--canon/--pool/--common` sweep; `--modes` text/hybrid/auto; `--ir` Hit@k/MRR/NDCG/MAP grid; `--llm` judge eval | Qdrant running with `jmdict_chunks` indexed (`GROQ_API_KEY` for `--llm` and LLM `--ir` configs) | `eval_headword_*`, `eval_grid_*.csv`, `eval_modes_*`, `retrieval_eval.*`, `llm_eval.*` in `eval/results/` | None for headword/modes/`--ir --no-llm`; Groq otherwise | headword ~30s; `--ir` full grid ~10–15min; `--llm` ~4–5min (30 calls/min cap) |
| `eval/eval_ja.py` | JA-subset view of the IR grid: Hit@1/2/3/5 + MRR per config, overall and per `ja_*` subset | Qdrant running with `jmdict_chunks` indexed | `retrieval_eval_ja.*` in `eval/reports/` | None | ~1min |
| `eval/embed_model_bench.py` | Dense embedding model throughput and retrieval accuracy (vector-only, in-memory) | `data/processed/chunks.json` and `eval/gold_set.tsv` | `eval/results/embed_model_bench.json` | None | ~20min (first run may download models) |

Runtimes are approximate on a modest CPU with local Qdrant; embedding-model and LLM cold starts can add time on the first run.

**Gold subsets.** `eval/gold_set.tsv` holds 300 queries in 6 categories; `--subsets` selects them — default is `en_words` + `en_verbs` (the 100-query English-word benchmark):

```bash
# default: English words + verbs
uv run python eval/eval.py

# Japanese exact-lookup route (kanji / hiragana / katakana) — dedicated JA report
uv run python eval/eval_ja.py

# long descriptive queries (exercises the LLM rewrite path when QUERY_REWRITE=auto)
uv run python eval/eval.py --subsets en_descriptive
```

On the Japanese subsets (ja_words + ja_hiragana + ja_katakana, 150 queries) the default config scores **Hit@1 = 100%** — the auto route's exact-match arm pins headwords (`retrieval_eval_ja.md`). BM25 alone still shows the weakness it masks: katakana Hit@1 0.38, compounds like テレビスクリーン outranking bare テレビ.

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

Headline results (`eval/reports/`, 300-query gold set + 150-query JA subsets):

- **Default config (auto + heuristic rewrite)**: Hit@1 0.81, Hit@5 0.90, MRR 0.845 — `retrieval_eval.md`
- **JA subsets**: Hit@1 1.00 on ja_words, ja_hiragana and ja_katakana — `retrieval_eval_ja.md`
- **LLM judge**: level-aware prompts produce much tighter answers (N1 ~39 vs ~152 words generic, less jargon) at comparable judge scores — `llm_eval.md`

Remaining headroom is `en_descriptive` (MRR 0.05–0.30 across configs). A re-ranking stage (local cross-encoder) was evaluated, reduced MRR on this bilingual corpus, and was removed.

## Data Sources

- **JMdict**: Japanese-English dictionary data © Jim Breen & EDRDG (CC BY-SA 4.0)
- **KANJIDIC2**: Kanji dictionary data © Jim Breen & EDRDG (CC BY-SA 4.0)
- **Tanaka Corpus / Tatoeba**: Example sentences (CC BY 2.0 FR)
- **KanjiVG**: Kanji stroke order diagrams © Ulrich Apel (CC BY-SA 3.0)

## License

Code is licensed under [Apache-2.0](LICENSE). Dictionary data remains under its
source licenses (see [NOTICE](NOTICE)) — derived files under `data/` are
share-alike per CC BY-SA.
