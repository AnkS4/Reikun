# Configuration Reference

## Groq Free-Tier Notes

Tuned for the free tier (30 RPM / ~1,000 requests/day *per model*): explanations are on-demand only with bounded token budgets, and 429s honor the API's `retry-after` within a small retry budget. Rate limits are per-model, so when the primary's daily cap is exhausted requests automatically fail over to `LLM_MODEL_FALLBACK`; if both are down the API returns 502 rather than a fabricated answer. `QUERY_REWRITE=auto` adds one call per long English query — heuristic rewriting is the free default.

## Port Configuration

| Service     | Container | Host (Docker)                | Host (Local) |
|-------------|-----------|------------------------------|--------------|
| HTTP API    | 8000      | `APP_PORT` (default: 8000)   | 8000 (`uvicorn app.api:app`) |
| Qdrant      | 6333      | 6333                         | 6333         |
| Qdrant gRPC | 6334      | 6334                         | 6334         |

Docker maps `127.0.0.1:${APP_PORT:-8000}:8000` — change `APP_PORT` in `.env`, then `docker compose up -d`. All host ports are bound to loopback only (Qdrant has no auth by default), so nothing is reachable from the LAN; the app reaches Qdrant over the internal compose network.