# Configuration Reference

## LLM providers

Set `LLM_PROVIDER` to `nebius` (default), `groq`, `gemini`, or `cohere` and the matching `*_API_KEY` (`NEBIUS_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY`). Model defaults live in `app/llm.py`; override with `LLM_MODEL` / `LLM_MODEL_FALLBACK` only when you want non-default IDs (clear those when switching providers so defaults apply). Optional `LLM_BASE_URL` overrides the provider's OpenAI-compatible endpoint. To run without an LLM key, set `QUERY_REWRITE=heuristic` or `off`; `auto` requires the active provider's key at startup.

### Free-tier / quota notes

Tuned for tight free tiers (e.g. ~30 RPM / ~1,000 requests/day *per model*): explanations are on-demand only with bounded token budgets, and 429s honor the API's `retry-after` within a small retry budget. Rate limits are often per-model, so when the primary's daily cap is exhausted requests automatically fail over to `LLM_MODEL_FALLBACK`; if all candidates are down the API returns 502 rather than a fabricated answer. Gemini is the exception: it ships Flash-Lite only, because Gemini 3.5 Flash's free tier caps requests at 20/day and cannot serve as a fallback. `QUERY_REWRITE=auto` (the value shipped in `.env.example`; the code fallback when unset is `heuristic`) adds one LLM call per long descriptive English query: the model returns an English display gloss plus ranked Japanese headwords, and retrieval tries the exact Japanese route first (English gloss as fallback). `heuristic` is free and instant, but only strips question scaffolding (`how do you say X in japanese` → `X`) — long descriptive phrases reach retrieval as typed. `off` disables rewriting entirely.

## Port Configuration

| Service     | Container | Host (Docker)                | Host (Local) |
|-------------|-----------|------------------------------|--------------|
| HTTP API    | 8000      | `APP_PORT` (default: 8000)   | 8000 (`uvicorn app.api:app`) |
| Qdrant      | 6333      | 6333                         | 6333         |
| Qdrant gRPC | 6334      | 6334                         | 6334         |

Docker maps `127.0.0.1:${APP_PORT:-8000}:8000` — change `APP_PORT` in `.env`, then `docker compose up -d`. All host ports are bound to loopback only (Qdrant has no auth by default), so nothing is reachable from the LAN; the app reaches Qdrant over the internal compose network.

## Retrieval and storage

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PORT` | Host port published by Docker Compose | 8000 |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant connection when `QDRANT_URL` is unset | localhost / 6333 (`qdrant` / 6333 in Compose) |
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud endpoint and key; the URL takes precedence over host/port | - |
| `QDRANT_COLLECTION` | Qdrant collection name | `jmdict_chunks` |
| `QDRANT_TIMEOUT` | Qdrant request timeout in seconds | 30 |
| `QDRANT_CLOUD_INFERENCE` | Let Qdrant Cloud embed queries; requires `QDRANT_URL` | `false` |
| `EMBED_MODEL` | Dense embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `SPARSE_MODEL` | Sparse embedding model | `Qdrant/bm25` |
| `MODELS_DIR` | Local FastEmbed model cache | `models/fastembed` |
| `QUERY_REWRITE` | Query rewriting mode | `auto` in `.env.example` (adds an LLM pivot for long descriptive EN); `heuristic` when unset (free, instant); or `off` |

## Serving, telemetry, and rate limits

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEMETRY` | Event sink: `stdout` or `sqlite` | `stdout` |
| `MONITORING_DB` | SQLite path when `TELEMETRY=sqlite` | `data/monitoring/reikun.db` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | `*` (development; pin the site origin in production) |
| `RATE_LIMIT_EXPLAIN` | `/explain*` requests per minute per client; 0 disables | 10 |
| `RATE_LIMIT_SEARCH` | `/search` requests per minute per client; 0 disables | 120 |
| `TRUSTED_PROXY_HOPS` | Trusted reverse-proxy hops used to select the client from `X-Forwarded-For` | 1 |
| `PORT` | API listen port injected by non-Compose hosts; leave unset locally | 8000 |

Rate limits are in-memory and per API instance. `INGEST_VIA_DOCKER` is deliberately not an `.env` setting: pass it as a one-shot Compose prefix as shown in the README. The frontend's build-time `PUBLIC_API_BASE` is documented in `web/.env.example`.