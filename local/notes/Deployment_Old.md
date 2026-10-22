# Deployment (old) — Render + Qdrant Cloud

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

> **Superseded.** The free-tier Render path below is kept as reference —
> the current production stack (Qdrant Cloud + Cloudflare Pages + Cloud
> Run) is documented in `Deployment.md`. The Qdrant-cluster and
> snapshot-transfer sections remain accurate — the vector store did not
> change.

Cloud deployment notes for the API + vector store. The Docker/Compose
packaging itself lives in `Architecture.md` §6.

Free-tier stack: **Render Web Service** hosts the app (0.5 GB RAM, 1 GB
disk), **Qdrant Cloud** hosts the vectors (1 GB RAM, 4 GB disk). Render's
512 MB can't fit ingestion (~90 MB of XML + embedding 218,786 chunks, ~1 hr),
so ingestion runs off-Render and the container boots straight into
the API: `check_state()` sees the populated collection plus the
`kanji_table.json` baked into the image and reports `ready`. Prerequisites:
a GitHub repo push, a Groq API key, free accounts on both services.

## Qdrant Cloud cluster
1. cloud.qdrant.io → new **Free** cluster, region near the Render one; wait
   for **Healthy**.
2. Copy the cluster URL (`https://….cloud.qdrant.io:6333`) → `QDRANT_URL`;
   create an API key → `QDRANT_API_KEY`. No manual collection — `ingest.py`
   creates `jmdict_chunks` on first run.

## Render Web Service
New → Web Service → connect the repo: Runtime `Docker`, Dockerfile path
`Dockerfile`, no start command (the image `CMD` runs `reikun` →
`scripts/startup.py`),
Free plan, same region as the Qdrant cluster.

## Environment variables (Render → Environment)
```bash
QDRANT_URL=…          QDRANT_API_KEY=…        QDRANT_COLLECTION=jmdict_chunks
GROQ_API_KEY=…        # console.groq.com/keys
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
QUERY_REWRITE=heuristic # recommended on the free tier
GITHUB_TOKEN=github_pat_… # see note
```
- `GITHUB_TOKEN`: `download_kanjivg.py` calls `api.github.com`;
  unauthenticated calls are capped at 60 req/hr per IP and Render's shared
  egress IPs hit that constantly (`403 rate limit exceeded`). Any
  fine-grained PAT with **no permissions** suffices (repo is public) —
  github.com/settings/personal-access-tokens. JMdict/KANJIDIC2 rsync from
  `ftp.edrdg.org` and need no token.
- Groq free tier (30 RPM / ~1,000 RPD per model): keep
  `QUERY_REWRITE=heuristic` — `auto` adds one call per search.
- Don't change `QDRANT_COLLECTION` post-deploy unless `app/config.py`
  changes too. Render free services sleep after 15 min idle (~30–60 s
  cold start).

## One-time ingestion (off-Render)
Vectors live in Qdrant Cloud, so every later deploy finds the collection
populated and skips straight to the app:
```bash
python scripts/download_edrdg.py    # JMdict NG + KANJIDIC2 XML (delta syncs)
python scripts/download_kanjivg.py  # KanjiVG SVGs
python scripts/build_chunks.py      # skips if data/processed/ exists
export QDRANT_URL=… QDRANT_API_KEY=… GITHUB_TOKEN=…
python scripts/startup.py --ingest-only
```
Warning: `ingest.py` **drops and recreates** the collection — ~1 hr of
downtime on the first load is fine; for updates use the snapshot-transfer
section below instead.

## Updating the cloud collection — snapshot transfer
No re-embedding — a file upload (~2 min for ~630 MB). Requires cloud Qdrant
≥ the local version (snapshots restore old → new only).
[`scripts/cloud_ingest.py`](../../scripts/cloud_ingest.py) automates the
whole flow (create → download → upload → delete, `--force` to overwrite a
non-empty target, `--source-url`/`SOURCE_QDRANT_URL` so `.env`'s cloud
`QDRANT_URL` can stay pointed at the target); the equivalent raw calls:
```bash
curl -X POST http://localhost:6333/collections/jmdict_chunks/snapshots
curl -o snap.snapshot \
  http://localhost:6333/collections/jmdict_chunks/snapshots/<name>.snapshot
curl -X POST "$QDRANT_URL/collections/jmdict_chunks/snapshots/upload?priority=snapshot" \
  -H "api-key: $QDRANT_API_KEY" -F "snapshot=@snap.snapshot"
curl -X DELETE "$QDRANT_URL/collections/jmdict_chunks/snapshots/snap.snapshot" \
  -H "api-key: $QDRANT_API_KEY"
```
- Uploaded snapshots persist until deleted (~660 MB each on the 4 GiB free
  disk) — keep 1–2, rotate by deleting the old after the new lands.
- `?priority=snapshot` makes the upload win all conflicts — full overwrite.
- Cloud `strict_mode` needs an index on every filtered/formula field; after
  a restore index data can be stale — rebuild payload indexes if queries
  400 with `Index required but not found` (see `Architecture.md` §2.2 note).
- For frequent refreshes a full snapshot is wasteful — an incremental diff
  (upsert changed `ent_seq`s, delete removed) is the better tool; see
  `Issues.md`.

## Frontend
The SvelteKit SPA builds to static assets (`cd web && npm run build` →
`web/build/`) and deploys to **Cloudflare Workers static assets** via
`web/wrangler.jsonc` (`not_found_handling: single-page-application` —
SPA fallback). `PUBLIC_API_BASE` is baked in at build time
(`web/src/env.ts`, `web/.env.example`) and must point at the deployed API.

## Deploy & verify
- `data/processed/kanji_table.json` is force-committed despite `data/` being
  gitignored — the Dockerfile copies it into the image. Push, then Manual
  Deploy → watch logs for `Data already ingested — nothing to do.` +
  the uvicorn startup line on `$PORT` (Render/Cloud Run inject it).
- Container disk is ephemeral — runtime downloads under `data/` are wiped
  each deploy; vectors live in Qdrant Cloud, `kanji_table.json` and the
  committed `strokes.json` KanjiVG diagrams are baked into the image
  (a missing diagram is an absent card, not a network call).
- Verify: open the service URL, search `cat`, click a thumbs button
  (feedback DB write).
- Troubleshooting: `403 rate limit exceeded` → set `GITHUB_TOKEN` and
  redeploy; `Out of memory (used over 512Mi)` during ingest → expected —
  ingest belongs off-Render (see *One-time ingestion* above); `No search
  results` → check `QDRANT_URL`/`QDRANT_API_KEY` and that `jmdict_chunks`
  has points.
