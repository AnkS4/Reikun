<p align="center">
  <img src="docs/logos/icon-rei-lens.png" alt="Reikun logo" width="128">
</p>
<h1 align="center">Reikun (例訓) — Semantic Japanese Dictionary</h1>

A Japanese reading assistant — search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji, and get grammar explanations tuned to your JLPT level.

## Demo

![Reikun demo — search, grammar explanation, kanji tooltip and card, sentence breakdown](docs/videos/demo_v3.gif)

Full recording: [docs/videos/demo_v3.mp4](docs/videos/demo_v3.mp4)

> **Try it live:** https://reikun.app/

## Features

- **Hybrid Search with query routing**: Dense vector embeddings (FastEmbed) + BM25 sparse vectors fused server-side in Qdrant (RRF). `mode=auto` routes the query: Japanese → BM25 + exact match, English word → hybrid + commonness prior, English sentence → dense-weighted fusion. Explicit `vector`/`text`/`hybrid` modes remain for evaluation
- **Query Rewriting**: Natural-language questions ("how do you say hospital") are normalised to dictionary glosses before retrieval — free regex heuristics by default, optional Cohere LLM rewriting for descriptive queries
- **Sentence Breakdown**: Paste Japanese text and Sudachi splits it into word units — furigana on top, gloss underneath, full breakdown on hover. Inflection tails merge into single chips and adjacent segments re-resolve into JMdict compounds
- **Kanji Lookup**: Deterministic kanji information (no LLM) — stroke-order diagrams (KanjiVG), readings, meanings, and common compound words
- **Grammar Explanations**: AI-generated grammar explanations calibrated to your JLPT level (N5–N1) using Cohere, on demand only
- **Feedback & Telemetry**: Thumbs-up/down feedback and query telemetry as JSON events (stdout sink, picked up by platform logs) or a local SQLite file; user-entered text is kept only as SHA-256 prefixes and rows auto-prune after ~90 days
- **Interface**: Search-first landing page, furigana (`<ruby>`) headwords, animated stroke order, light/dark themes, shareable URLs (`?q=猫&level=N3`), one-click level-aware grammar explanations
- **HTTP API**: FastAPI layer (`app/api.py`) over the same pipeline — standalone uvicorn service with routes at the root (what the Docker image serves); includes SSE streaming for explanations and JSON-shaped rendering (ruby parts, kanji card, segment chips, stroke data) for the web frontend

## Tech Stack

- **Frontend**: SvelteKit static SPA (`web/` → Cloudflare Workers static assets); Inter + Noto Sans JP web fonts
- **API**: FastAPI + Uvicorn (the production serving process; one worker)
- **Vector Database**: Qdrant (named dense + sparse vectors, server-side RRF hybrid)
- **Embeddings**: FastEmbed — `all-MiniLM-L6-v2` (dense, 384-dim) + `Qdrant/bm25` (sparse), ONNX-quantized for CPU
- **LLM**: Cohere `command-a-plus-05-2026` — grammar explanations, optional query rewriting and re-ranking, LLM-judged evals (all token-budgeted)
- **Ingestion pipeline**: `scripts/startup.py` can run wait-for-Qdrant → check-state → download → build → ingest with retries, then launch the app — opt-in via `INGEST_VIA_DOCKER=1` or `--ingest` (off by default; `--ingest-only` runs it without the UI). Populated collections get an incremental top-up instead — rsync delta + upsert of new/edited entries only
- **Monitoring**: JSON event telemetry (`app/telemetry.py`; optional SQLite sink in `scripts/feedback_log.py`)
- **Data Sources**: JMdict, KANJIDIC2, Tatoeba Corpus, KanjiVG
- **Containerization**: Docker & Docker Compose

## Installation

### Prerequisites

- **Docker and Docker Compose** (recommended path — runs the app + Qdrant)
- **Cohere API key** — powers grammar explanations, optional LLM query rewriting (`QUERY_REWRITE=auto`), and the LLM evaluation. Search and kanji lookup work without it.
- **Git** (to clone) and ~3 GB free disk (dictionary data + embedding models)

For local development only:

- **Python 3.13+** and **[uv](https://docs.astral.sh/uv/)** (dependency manager — `pip` works too)

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/AnkS4/Reikun
   cd Reikun
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your COHERE_API_KEY
   ```

### Running the Application

#### Option 1: Docker (Recommended)

First run — let the container self-provision (rsync + dev deps into the image, then download → build → ingest ~219k entries at boot; embedding takes ~1 hr):

```bash
INGEST_VIA_DOCKER=1 docker compose up -d --build
```

(or set `INGEST_VIA_DOCKER=1` in `.env` for the same effect on every `docker compose up --build`)

**Or**, if Qdrant is already populated — plain `up` serves whatever it already holds:

```bash
docker compose up -d

# View logs
docker compose logs -f app

# Stop services
docker compose down
```

The API will be available at `http://localhost:8000` (or the port specified in your `.env` file as `APP_PORT`) — Swagger docs at `/docs`. The frontend is the SvelteKit app in `web/` (see Option 2 to run it against the local API).

Alternatively, run the pipeline on the host instead of in the container (dev deps install via `uv sync`; ingestion is off by default without `INGEST_VIA_DOCKER`):

```bash
uv run python scripts/download_edrdg.py    # JMdict NG + KANJIDIC2 XML
uv run python scripts/download_kanjivg.py  # KanjiVG stroke-order SVGs
uv run python scripts/build_chunks.py      # writes data/processed/
uv run python scripts/ingest.py            # embed + load all ~219k entries
```

**Note:** a full ingest embeds ~219k entries (~1 hr); `--common` loads only the ~37k common-entries subset for a quick test. Data is cached in the `data/` directory for subsequent runs.

The embedding models are pre-downloaded into the image and live in a named volume (`models`), so `docker compose down -v` discards them and the next start re-copies them from the image. If external hostnames (HF Hub, ftp.edrdg.org, Cohere) fail to resolve from inside the container, copy `docker-compose.override.yml.example` to `docker-compose.override.yml` to pin public DNS resolvers.

#### Option 2: Local Development

For local development without Docker:

1. **Install Python dependencies** (creates `.venv` and installs locked deps):
   ```bash
   uv sync
   ```

2. **Download and process data**:
   ```bash
   # Sync JMdict NG + KANJIDIC2 XML from EDRDG (needs rsync), and KanjiVG SVGs
   uv run python scripts/download_edrdg.py
   uv run python scripts/download_kanjivg.py
   
   # Parse and chunk dictionary data
   uv run python scripts/build_chunks.py
   ```

3. **Start Qdrant**:
   ```bash
   docker compose up -d qdrant
   ```

4. **Ingest data into Qdrant**:
   ```bash
   # Ingest the processed data (this takes a few minutes)
   QDRANT_HOST=localhost uv run python scripts/ingest.py
   ```

5. **Run the HTTP API**:

   The API is the same FastAPI app the Docker image serves — `app/api.py`, routes at the root:
   ```bash
   uv run uvicorn app.api:app --reload          # Swagger UI at http://localhost:8000/docs
   ```
   Endpoints: `GET /health` (liveness), `GET /ready` (readiness — real Qdrant query), `GET /search?q=…&n=10&mode=auto`, `GET /kanji?chars=例訓` (batch hover cards), `GET /kanji/{char}?strokes=true`, `POST /explain`, `POST /explain/stream` (SSE), `POST /feedback`. OpenAPI is at `/openapi.json`; regenerate the committed schema + frontend types with `uv run python scripts/dump_openapi.py` then `npx openapi-typescript docs/api/openapi.json -o web/src/lib/openapi.d.ts`.

6. **Run the SvelteKit web frontend** (`web/` — needs the API running from step 5):

   ```bash
   cd web && npm install && npm run dev     # dev server → http://localhost:5173
   npm run check                            # svelte-check type diagnostics
   npm run build                            # static build → web/build/ (adapter-static)
   npm run preview                          # preview the production build
   ```

   The API base URL is baked in at build time via `PUBLIC_API_BASE` (schema: `web/src/env.ts`, default `http://localhost:8000`; see `web/.env.example`). Static output deploys to Cloudflare Pages/Workers as-is (`200.html` SPA fallback).

8. **(Optional) Lint**:
   ```bash
   uvx ruff check app scripts eval     # config in pyproject.toml [tool.ruff]
   uvx ruff check --fix app scripts eval
   ```
   Rules target Python 3.13. RUF001–003 (“ambiguous” Unicode) are disabled on purpose — full-width and CJK characters are the subject matter here, not typos.

### URL parameters

The Search page keeps its state in the URL, so results are shareable and the browser back button works:

| Param | Example | Meaning |
|---|---|---|
| `q` | `?q=食べる` | Runs the search on load |
| `level` | `?level=N3` | JLPT level used for grammar explanations (remembered until changed) |
| `kanji` | `?kanji=猫` | Opens the kanji detail dialog once |

## Project Structure

```
Reikun/
├── app/
│   ├── config.py            # Central env-driven configuration
│   ├── api.py               # FastAPI app — the serving entrypoint (/search, /kanji, /explain, /feedback, /health, /ready)
│   ├── render.py            # UI-agnostic JSON shaping (ruby parts, kanji card, chips, stroke data)
│   ├── telemetry.py         # Event logging interface (stdout JSON default, optional SQLite sink)
│   ├── retrieval.py         # Vector / BM25 / hybrid search, re-ranking pipeline
│   ├── query_rewrite.py     # Heuristic + optional LLM query rewriting
│   ├── kanji_lookup.py      # Deterministic KANJIDIC2 + KanjiVG lookup
│   ├── grammar_explain.py   # Cohere client, JLPT-level-aware prompts
│   └── embedder.py          # FastEmbed dense/sparse model wrappers
├── web/                     # SvelteKit static frontend (adapter-static → Cloudflare Workers static assets)
│   ├── src/routes/          # /  (search SPA shell)
│   ├── src/lib/             # openapi-fetch client (typed from openapi.d.ts), kanji-hover cache, theme
│   ├── src/env.ts           # PUBLIC_API_BASE schema — build-time public env var
│   └── wrangler.jsonc       # Cloudflare Workers static-assets deploy (SPA fallback)
├── docs/
│   ├── screenshots/         # UI captures (search, kanji card)
│   └── videos/              # Demo recording (gif + mp4)
├── eval/
│   ├── gold_set.tsv         # gold set — en_words/en_verbs (default), en_descriptive, ja_*
│   ├── eval.py              # unified eval: headword bench + knob sweep (default), --modes, --ir, --llm
│   ├── embed_model_bench.py # dense embedding model benchmark
│   └── results/             # generated reports
├── scripts/
│   ├── download_edrdg.py    # Sync JMdict NG + KANJIDIC2 XML from EDRDG (rsync)
│   ├── download_kanjivg.py  # Download KanjiVG stroke-order SVGs
│   ├── feedback_log.py      # SQLite telemetry sink (searches, feedback, kanji lookups, explanations)
│   ├── build_chunks.py      # Parse and chunk dictionary data
│   ├── ingest.py            # Embed (dense + sparse) and load into Qdrant
│   ├── dump_openapi.py      # Write docs/api/openapi.json for frontend type generation
│   └── startup.py           # Container entrypoint (execs uvicorn) + opt-in ingestion pipeline
├── .env.example             # Environment variable template
├── data/
│   ├── raw/                 # Downloaded dictionary files
│   ├── processed/           # Parsed chunks and kanji table
│   ├── kanjivg/             # Stroke-order SVGs
│   └── monitoring/          # SQLite telemetry database
├── models/                  # Cached embedding models (local runs; Docker uses a named volume)
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml.example  # optional host-specific overrides (e.g. DNS)
├── pyproject.toml           # pinned deps + dev group (ingest-only deps)
└── uv.lock                  # locked resolution (uv sync --frozen)
```

## Environment Variables

Create a `.env` file (see `.env.example`):

- `APP_PORT`: Port the API container is published on (default: 8000)
- `COHERE_API_KEY`: Required for grammar explanations (get at https://dashboard.cohere.com/api-keys)
- `COHERE_MODEL`: Cohere chat model (default: `command-a-plus-05-2026`)
- `QDRANT_HOST` / `QDRANT_PORT`: Qdrant connection (defaults: localhost / 6333); `QDRANT_URL` + `QDRANT_API_KEY` override for Qdrant Cloud
- `QDRANT_COLLECTION`: Qdrant collection name (default: jmdict_chunks)
- `EMBED_MODEL`: Dense embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `QUERY_REWRITE`: `heuristic` (default, free), `auto` (adds one Cohere call for long English queries — best MRR but uses trial-tier quota), or `off`

### Cohere free-tier notes

Tuned for a trial key (~10 calls/min): explanations are on-demand only with bounded token budgets and 429 retry/backoff. `QUERY_REWRITE=auto` adds one call per search — keep it off on the free tier.

## Port Configuration

| Service     | Container | Host (Docker)                | Host (Local) |
|-------------|-----------|------------------------------|--------------|
| HTTP API    | 8000      | `APP_PORT` (default: 8000)   | 8000 (`uvicorn app.api:app`) |
| Qdrant      | 6333      | 6333                         | 6333         |
| Qdrant gRPC | 6334      | 6334                         | 6334         |

Docker maps `127.0.0.1:${APP_PORT:-8000}:8000` — change `APP_PORT` in `.env`, then `docker compose up -d`. All host ports are bound to loopback only (Qdrant has no auth by default), so nothing is reachable from the LAN; the app reaches Qdrant over the internal compose network.

## Evaluation

Reproducible evaluation scripts live in `eval/`; reports are written to `eval/results/`.

| Script | What it measures | Required setup | Outputs | API calls | Typical runtime |
|---|---|---|---|---|---|
| `eval/eval.py` | Headword Hit@1/2/5 vs gold (default); `--canon/--pool/--common` sweep; `--modes` text/hybrid/auto; `--ir` Hit@k/MRR/NDCG/MAP grid; `--llm` judge eval | Qdrant running with `jmdict_chunks` indexed (`COHERE_API_KEY` for `--llm` and LLM `--ir` configs) | `eval_headword_*`, `eval_grid_*.csv`, `eval_modes_*`, `retrieval_eval.*`, `llm_eval.*` in `eval/results/` | None for headword/modes/`--ir --no-llm`; Cohere otherwise | headword ~30s; `--ir` full grid ~10–15min; `--llm` ~4–5min (10 calls/min cap) |
| `eval/embed_model_bench.py` | Dense embedding model throughput and retrieval accuracy (vector-only, in-memory) | `data/processed/chunks.json` and `eval/gold_set.tsv` | `eval/results/embed_model_bench.json` | None | ~20min (first run may download models) |

Runtimes are approximate on a modest CPU with local Qdrant; embedding-model and Cohere cold starts can add time on the first run.

**Gold subsets.** `eval/gold_set.tsv` holds 300 queries in 6 categories; `--subsets` selects them — default is `en_words` + `en_verbs` (the 100-query English-word benchmark):

```bash
# default: English words + verbs
uv run python eval/eval.py

# Japanese exact-lookup route (kanji / hiragana / katakana)
uv run python eval/eval.py --subsets ja_words ja_hiragana ja_katakana

# long descriptive queries (exercises the Cohere rewrite path)
uv run python eval/eval.py --subsets en_descriptive
```

Expected on the Japanese subsets (ja_words + ja_hiragana + ja_katakana, 150 queries): **Hit@1 ≈ 98%, Hit@2 = 100%** — the residual misses are rare BM25 near-matches (いいえ over 家, デュース over ジュース, 虚 over 空), not missing data.

Run the retrieval benchmark without any paid API calls:

```bash
# vector vs BM25 vs hybrid vs +heuristic rewrite (no Cohere)
uv run python eval/eval.py --ir --no-llm
```

Run the full grid, including `auto` LLM rewriting (uses Cohere quota):

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

Headline results (`eval/results/retrieval_eval.md`, 300-query gold set): auto + heuristic query rewriting wins — Hit@1 0.80, Hit@5 0.87, MRR 0.828. A re-ranking stage (local cross-encoder or Cohere) was evaluated, reduced MRR on this bilingual corpus, and was removed.

## Data Sources

- **JMdict**: Japanese-English dictionary data © Jim Breen & EDRDG (CC BY-SA 4.0)
- **KANJIDIC2**: Kanji dictionary data © Jim Breen & EDRDG (CC BY-SA 4.0)
- **Tanaka Corpus / Tatoeba**: Example sentences (CC BY 2.0 FR)
- **KanjiVG**: Kanji stroke order diagrams © Ulrich Apel (CC BY-SA 3.0)

## License

Code is licensed under [Apache-2.0](LICENSE). Dictionary data remains under its
source licenses (see [NOTICE](NOTICE)) — derived files under `data/` are
share-alike per CC BY-SA.
