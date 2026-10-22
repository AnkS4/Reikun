# Deployment — production (Qdrant Cloud + Cloudflare Workers + Cloud Run)

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

Current production stack — three managed services, no VMs:

- **Vectors** — **Qdrant Cloud** free cluster; reachable via `QDRANT_URL`
  + `QDRANT_API_KEY`; collection `jmdict_chunks` is created by
  `ingest.py` on first populate.
- **API** — **Google Cloud Run** service `reikun-api`
  (europe-southwest1, 1 GiB, min 0 / max 3), built from the repo
  `Dockerfile`. Public URL: `https://reikun-api-cmudl7elbq-no.a.run.app`.
- **Web** — **Cloudflare Workers** static assets from `web/build/`
  (config: `web/wrangler.jsonc`, Worker name `reikun`), serving
  **reikun.app** via a Worker custom domain — the zone moved from
  name.com to CF nameservers at cutover; the Oracle VM stack
  (docker/Caddy) is stopped but retained as a frozen rollback backup.

The superseded free-tier Render walkthrough (cluster bootstrap,
per-variable notes, raw `curl` snapshot calls) is archived in
`Deployment_old.md`. The Docker/Compose packaging itself lives in
`Architecture.md` §6.

## Refresh map — the three moving parts

| Part | Needs a push when | Mechanism |
|---|---|---|
| **Qdrant Cloud** (collection) | **Rarely** — only on ingest/payload-schema or source-data changes. Survives every redeploy; a new image never touches it. | Local build (seed vectors in with `scripts/ingest.py --seed-from`, then snapshot push via `scripts/cloud_ingest.py` — see *Updating the vector collection*) |
| **Cloudflare** (web frontend) | Every `web/` change | **Automatic on `git push` to `main`** — the `reikun` Worker is git-connected to this repo: Cloudflare builds `web/` and deploys `build/` (PUBLIC_API_BASE comes from the project env, not the repo). Manual fallback: `npx wrangler deploy` after a local build |
| **Cloud Run** (`reikun-api`) | Every `app/`, `scripts/`, `Dockerfile`, or dependency change | **Manual** — no Cloud Build trigger is wired (**[LATER]**: continuous deployment, see Cloud Run section). `gcloud run deploy reikun-api --source . --region europe-southwest1` |

So a normal release is: push to `main` (frontend ships itself via the
git-connected build) → `gcloud run deploy` → verify. The collection only
enters the picture when the ingest pipeline or chunk schema changes.

## Cloud Run (API)

- Deploy: `gcloud run deploy reikun-api --source . --region
  europe-southwest1` from the repo root — Cloud Build builds the
  Dockerfile from the uploaded context (existing service → secrets and
  settings carry over; no env flags needed on redeploys). `.gcloudignore`
  mirrors `.dockerignore`, so only image inputs go on the wire.
- Post-deploy sanity: `curl -s $URL/ready` returns `{"status":"ready",…}`
  and `curl -s $URL/openapi.json | grep '"version"'` shows the new
  release — `app/config.py`'s `APP_VERSION` is read from pyproject.toml,
  so the schema can never lag a bump.
- A `git push` does **not** deploy — no Cloud Build trigger is wired. CI
  only validates (`.github/workflows/ci.yml`: ruff, pytest, OpenAPI +
  `openapi.d.ts` drift, svelte-check, vite build; Node 22 + Python 3.13;
  least-privilege `contents: read`; concurrency cancel-in-progress).
- **[LATER] Continuous deployment** — Cloud Run's native "set up
  continuous deployment" (console wizard on the service) creates a
  Cloud Build trigger on `main` that rebuilds the Dockerfile and
  deploys on each push; auth is GitHub↔GCP OAuth + the Cloud Build SA
  (wizard auto-grants `run.admin` + `serviceAccountUser`), so zero
  secrets touch the public repo and build logs stay private in GCP.
  After creating, edit the trigger's **included files** to
  `app/** scripts/** pyproject.toml uv.lock Dockerfile .gcloudignore
  data/processed/**` so web/docs-only pushes skip it; `[skip ci]` in a
  commit message also skips. Trade-offs vs the rejected alternative
  (GitHub Actions + Workload Identity Federation): no gating on
  `ci.yml` — mitigate with branch protection requiring CI green; no
  post-deploy `/ready` assertion — Cloud Run's own health check still
  keeps a broken revision from taking traffic (rollback = Revisions →
  Manage Traffic); build minutes bill at a few cents each (default
  machine isn't the free-tier `e2-medium`).
- `PORT` is injected by Cloud Run and read by `scripts/startup.py` —
  never set it manually (local/compose stay on the 8000 default).
- Secrets via **Secret Manager**: `QDRANT_URL`, `QDRANT_API_KEY`,
  `GROQ_API_KEY`, and `CORS_ORIGINS` (must match the frontend origin
  `https://reikun.app` exactly).
- Ingestion does **not** run on Cloud Run — the instance class can't fit
  it (~90 MB of XML + embedding ~219k chunks). The container boots
  straight into the API once the collection is populated
  (`check_state()` → `ready`); `kanji_table.json`,
  `headword_index.marisa`, and `strokes.json` are baked into the image,
  so a cold start needs only Qdrant Cloud.
- Cost shape: request-based CPU billing + `minScale=0` +
  `cpu-throttling` → **€0 at idle**; CPU is billed only while a request
  is in flight. Oct 2026 bill: 575 vCPU-s → €0.01 gross, fully covered
  by the free-tier credit (console headline is pre-discount — check the
  "Other savings" column in Billing Reports). Free tier/mo: 2M
  requests, 180k vCPU-s, 360k GiB-s — ~300× current usage.
- Worst case if bots saturate `maxScale 3` 24/7 ≈ **~€70/mo**;
  `gcloud run services update reikun-api --max-instances 1` caps that at
  ~€25 and still serves the app fine. GCP has **no native hard spend
  cap** — set a €5 budget alert (Billing → Budgets, emails at
  50/90/100%); a true kill switch needs budget → Pub/Sub → function
  setting `maxScale=0` (~30 min setup, overkill at this scale).
- **[LATER] bot/abuse mitigation** — no native Cloud Run rate limiting;
  Cloud Armor is €5+/mo, not worth it. Cheap options if traffic
  appears: in-app token-bucket middleware returning 429 *before* the
  embedding+Qdrant work (request-count billing still applies but it's
  the small part), or a CF Worker proxy in front for free rate-limit
  rules + response caching (dictionary queries are highly cacheable).

## Cloudflare Workers (web)

- **Deploys run on `git push` via the Worker's GitHub connection** —
  Cloudflare watches `main`, runs the build in its own CI, and publishes
  `web/build/`; nothing in-repo orchestrates it (`.github/workflows/ci.yml`
  is validation-only). `PUBLIC_API_BASE` is set in the Worker's project
  env, which is what points the production build at the Cloud Run URL.
- **`cd web && npx wrangler deploy` is the manual fallback**: it reads
  `web/wrangler.jsonc` and uploads `web/build/` verbatim to the `reikun`
  Worker, which serves `reikun.asatbhai.workers.dev` and the `reikun.app` custom
  domain. There is no build step inside wrangler — it ships whatever
  `build/` contains.
- Auth is one-time and browser-based: `npx wrangler login` (OAuth);
  `npx wrangler whoami` to check. Without it deploy fails with "not
  authenticated".
- `npm run build` → `web/build/` must run **first**. The committed
  `wrangler.jsonc` stops wrangler's SvelteKit auto-config from converting
  the project to adapter-cloudflare; `not_found_handling:
  single-page-application` is the SPA fallback (same role `200.html`
  plays on classic Pages).
- **`PUBLIC_API_BASE` is baked at *build* time, not deploy time** —
  `vite` compiles it into the JS bundle (`web/src/env.ts` schema,
  `web/.env.example`), so it must be set on `npm run build`. Setting it
  on `wrangler deploy` does nothing.
  - Footgun: a build with no env set silently bakes
    `http://localhost:8000` (the `env.ts` default) — deploying that
    breaks every API call on the live site. Pre-deploy check:
    `grep -rl "localhost:8000" web/build/` must print nothing.
  - Option: a gitignored `web/.env` with the prod URL makes deploy builds
    reproducible — but then local `vite build`/`preview` also calls prod.
- CORS: `CORS_ORIGINS` on Cloud Run must match the frontend origin
  exactly (`https://reikun.app`; keep `*.workers.dev` while preview
  stays useful) — scheme + host, no trailing slash.

## Updating the vector collection

The collection lives in Qdrant Cloud and survives every redeploy.

**Preferred clean re-ingest: build locally, push a snapshot.** Schema
changes, re-embeds, and any sweeping refresh should never upsert a big
wave straight at the live cloud — that wedged it once (2026-10-21:
three ingest passes left tombstone churn, a collection stuck
mid-optimization 5+ h, and the 0.7.x API serving degraded results the
whole time). Instead build the finished collection on local Docker,
seed it with the cloud's stored vectors, and snapshot-push: the cloud
then runs no index build of its own — it receives the collection fully
built (green, indexes included) and the swap is a file transfer
(~1–2 GB, a couple of minutes):

1. Fresh local Qdrant, version-matched to the cluster, own port (the
   compose stack owns :6333):

   ```
   docker run -d --name reikun-qdrant-seed -p 16333:6333 \
     -v $HOME/qdrant-seed:/qdrant/storage qdrant/qdrant:v1.19.1
   ```

2. Seed (vectors transplanted from the cloud onto current chunks.json
   payloads — no local embedding; anything the drift check can't
   verify re-embeds locally so the snapshot ships proven fingerprints):

   ```
   CLOUD_URL=$(grep '^QDRANT_URL=' .env | cut -d= -f2- | tr -d '"')
   set -a; source .env; set +a
   export QDRANT_URL=http://localhost:16333 \
          QDRANT_SOURCE_API_KEY="$QDRANT_API_KEY"; unset QDRANT_API_KEY
   uv run python scripts/ingest.py --seed-from "$CLOUD_URL"
   ```

   (`.env`'s `QDRANT_HOST` is a compose hostname, not a URL — the cloud
   source is `QDRANT_URL`, and its key travels separately in
   `QDRANT_SOURCE_API_KEY`.)

3. Wait for local status `green` (`GET /collections/jmdict_chunks`);
   a snapshot freezes whatever index state exists, so never snapshot a
   yellow/grey collection.
4. Snapshot on source → download (sha256-verified) → multipart upload
   with `?wait=true`, which replaces the target collection wholesale —
   this also clears stuck optimizer state — then re-verifies point
   counts:

   ```
   uv run python scripts/cloud_ingest.py --source-url http://localhost:16333 --force
   ```

5. Verify target: count matches, `green`, spot-check a known payload
   and that indexed payload fields report `points > 0`; re-run the eval
   suite. Old cloud snapshots (e.g. 2026-10-03) remain as fallback.
6. `docker rm -f reikun-qdrant-seed` (keep the `$HOME/qdrant-seed`
   volume around if a retry is plausible).

[`scripts/cloud_ingest.py`](../../scripts/cloud_ingest.py) automates
create → download → upload → delete (`--force` to overwrite a non-empty
target; `--source-url`/`SOURCE_QDRANT_URL` so `.env`'s cloud
`QDRANT_URL` can stay pointed at the target). Small top-ups with no
vector change can still go direct to the live cloud —
`scripts/ingest.py --update --reuse-vectors` (minutes, no snapshot,
no re-embed) — but keep those to payload-only diffs; a fresh embed or
schema change belongs in the snapshot flow above.

- Raw `curl` equivalents and snapshot-housekeeping notes:
  `Deployment_old.md` (*Updating the cloud collection*).
- Caveat: cloud `strict_mode` rejects any filter/formula field lacking
  an index — rebuild payload indexes if queries 400 with `Index required
  but not found` (`Architecture.md` §2.2).

## Deploy & verify

1. `git push` to `main` — repo CI validates; the git-connected Cloudflare
   build ships the frontend on its own (watch the Worker's build log in
   the CF dashboard if `web/` changed).
2. `gcloud run deploy reikun-api --source . --region europe-southwest1`.
   Watch logs for `Data already ingested — nothing to do.` + the uvicorn
   startup line on `$PORT`.
3. Manual frontend redeploy only if the connected build needs a kick:
   `cd web && PUBLIC_API_BASE=<cloud-run-url> npm run build && npx wrangler deploy`.
   The env var belongs on the **build**, not the deploy (see above);
   grep `build/` for `localhost:8000` first.
4. Verify: open https://reikun.app, search `cat`, click a thumbs button
   (feedback event).
5. Troubleshooting: `No search results` → check `QDRANT_URL` /
   `QDRANT_API_KEY` and that `jmdict_chunks` has points; CORS errors →
   `CORS_ORIGINS` must equal the frontend origin (scheme + host, no
   trailing slash); cold starts (~seconds) are normal with min 0.
