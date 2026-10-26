# Configuration Reference

## LLM providers

Set `LLM_PROVIDER` to `groq` (default), `gemini`, `cohere`, or `nebius` and the matching `*_API_KEY` (`GROQ_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY`, or `NEBIUS_API_KEY`). Model defaults live in `app/llm.py`; override with `LLM_MODEL` / `LLM_MODEL_FALLBACK` only when you want non-default IDs (clear those when switching providers so defaults apply). Optional `LLM_BASE_URL` overrides the provider's OpenAI-compatible endpoint.

### Free-tier / quota notes

Tuned for tight free tiers (e.g. ~30 RPM / ~1,000 requests/day *per model*): explanations are on-demand only with bounded token budgets, and 429s honor the API's `retry-after` within a small retry budget. Rate limits are often per-model, so when the primary's daily cap is exhausted requests automatically fail over to `LLM_MODEL_FALLBACK`; if all candidates are down the API returns 502 rather than a fabricated answer. Gemini is the exception: it ships Flash-Lite only, because Gemini 3.5 Flash's free tier caps requests at 20/day and cannot serve as a fallback. `QUERY_REWRITE=auto` (default) adds one LLM call per long descriptive English query: the model returns an English display gloss plus ranked Japanese headwords, and retrieval tries the exact Japanese route first (English gloss as fallback). Set to `heuristic` for a free, instant-only rewrite path.

## Port Configuration

| Service     | Container | Host (Docker)                | Host (Local) |
|-------------|-----------|------------------------------|--------------|
| HTTP API    | 8000      | `APP_PORT` (default: 8000)   | 8000 (`uvicorn app.api:app`) |
| Qdrant      | 6333      | 6333                         | 6333         |
| Qdrant gRPC | 6334      | 6334                         | 6334         |

Docker maps `127.0.0.1:${APP_PORT:-8000}:8000` — change `APP_PORT` in `.env`, then `docker compose up -d`. All host ports are bound to loopback only (Qdrant has no auth by default), so nothing is reachable from the LAN; the app reaches Qdrant over the internal compose network.

## Other Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_PORT` | Port the API container is published on | 8000 |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant connection (local) | localhost / 6333 |
| `QDRANT_URL` / `QDRANT_API_KEY` | Override for Qdrant Cloud | - |
| `QDRANT_COLLECTION` | Qdrant collection name | jmdict_chunks |
| `EMBED_MODEL` | Dense embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `QUERY_REWRITE` | Query rewriting mode | `auto` (default, adds LLM pivot for long descriptive EN), `heuristic` (free, instant), or `off` |