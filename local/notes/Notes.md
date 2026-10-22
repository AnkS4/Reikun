# Notes

## pyproject.toml

### Build System
- `setuptools>=77`: needed for PEP 639 SPDX license strings (`license = "Apache-2.0"`) and `license-files` metadata.
- `packages.find` includes `app*` and `scripts*` so CLI/ingestion utilities are packaged.

### Runtime Dependencies
- `uvicorn==0.54.0` (no `[standard]`): prod container runs one worker; skipping `uvloop`/`httptools`/`watchfiles`/`websockets` saves ~25–30 MB. Dev uses `watchfiles` alone for `--reload` — the app has no websockets and prod doesn't run uvloop/httptools anyway.
- `sudachipy==0.7.0` + `sudachidict-small==20260723.1`: sentence segmentation (`SplitMode.B`) and `wf_score`. `small` (~110 MB) chosen over `core` (~200 MB); over-split compounds re-merged in `retrieval._segment_sudachi`. Dict format is coupled to the binding version — bump both together.

### Dependency Groups
- `ingest`: `wordfreq` (Zipf prior in `scripts/build_chunks.py`, Japanese path shimmed to `sudachipy`). Ingest-only — Dockerfile `INGEST_VIA_DOCKER=1` syncs just this group, keeping pytest/ruff out of the ingest image.
- `dev` (includes `ingest`): `watchfiles`, `pytest`, `ruff`.
- `uv run`/`uv sync` install `dev` (hence `ingest`) via `default-groups`; Docker builds use `--no-default-groups`.

### Why a dep is in `dependencies` vs a group
- `httpx`: main — not imported by `app/`; the Docker HEALTHCHECK execs `import httpx` directly.
- `groq`: main — powers the Grammar explain feature. Lazy-imported inside `_groq()` (`grammar_explain.py`) and `query_rewrite.py` so the import cost is paid only on use and retrieval-only environments tolerate its absence.
- `wordfreq`: `ingest` — needed once to build chunks, never at serve time.
- `watchfiles`, `pytest`, `ruff`: `dev` — never shipped to any image.

### Tests
- `pythonpath = ["."]`, `testpaths = ["tests"]` — import `app`/`scripts` from the working tree.

### Ruff (`[tool.ruff.lint]`)
- `select = ["E", "F", "I", "UP", "B", "C4", "PERF", "RUF"]`.
- Do NOT add `ignore` codes — fix the code instead. Only in a truly extreme case, with justification.
- Refactors that removed `ignore` entries:
  - `typing.Annotated` instead of `Query(...)` defaults (`B008`)
  - `strict=False` on `itertools.batched()` (`B911`)
  - dict literals over `dict()` calls (`C408`)
  - `list.extend()` over accumulation loops (`PERF401`)
  - cleaned `sys.path` hacks / stale `# noqa` (`RUF100`)
  - ASCII punctuation in comments/docstrings (`E501`, `RUF001–003`)

### Versioning — where the release version lives
- `pyproject.toml` `[project] version` — single source of truth.
- `app/config.py` — exposes it as `APP_VERSION` (tomllib read of pyproject); `app/api.py` passes it to `FastAPI(version=…)`, so `/openapi.json` follows automatically.
- `docs/api/openapi.json` — regenerate after a bump: `uv run python scripts/export_openapi.py`.
- `uv.lock` — `name = "reikun"` entry; `uv lock`/`uv sync` refreshes it (the editable install re-builds on the next `uv run`).
- `web/package.json` + `web/package-lock.json` — manual bump; the lockfile mirrors `version` twice (top-level and `packages[""]`).

## Dockerfile
- `INGEST_VIA_DOCKER` (ARG+ENV): one flag, two effects — `=1` installs rsync + `--group ingest` at build, and the baked ENV makes `scripts/startup.py` run the pipeline at boot. `docker build --build-arg INGEST_VIA_DOCKER=1 .`, or set in `.env` for compose.
- `UV_PYTHON_DOWNLOADS=never`: without it uv silently downloads a standalone CPython (~30 MB) if interpreter discovery fails (base bump, requires-python change) — this turns that regression into a build error.
- `PYTHONDONTWRITEBYTECODE=1`: safe because everything is precompiled at build — `UV_COMPILE_BYTECODE` for deps, `compileall` for `app`/`scripts`.
- `UV_LINK_MODE=copy`: uv cache and `/app/.venv` are on different filesystems — hardlinks impossible, avoids warnings.
- Non-root `app` (UID 1000, matches typical first host user so `./data` bind mounts stay writable). `USER` is set *before* installs → correct ownership, no `chown -R` layer duplicating the ~600 MB venv.
- Two `uv sync` stages: deps layer (`--no-install-project`) caches on `uv.lock` only; project layer after source copy (editable install provides the `reikun` script).
- uv is pip-installed into `/tmp` and deleted in the same RUN — never lands in the image (`COPY --from` would persist ~56 MB in a layer). No BuildKit mounts: Cloud Build's stock builder.
- Runtime excludes dep groups (`--no-default-groups`); ingest builds add `--group ingest`, not `dev` — keeps pytest/ruff out.
- Ships `kanji_table.json` (~5 MB), `headword_index.marisa` (~26 MB), `strokes.json` (~9 MB) — committed runtime data, one COPY layer. `chunks.json` (~58 MB) excluded — ingest runs off-host.
- Model warm layer sits between deps and source layers: `warm_models()` downloads ~90 MB of ONNX models (`all-MiniLM-L6-v2` dense + `Qdrant/bm25` sparse) but imports only `app/embedder.py` → `app/config.py` (+ `__init__.py`), all rarely changing — so code edits don't re-download models. Importing `app.config` also creates `models/` + `data/` dirs as a side effect (hence no mkdir).
- `compileall -q app scripts` runs last: uv precompiles only deps, not the editable project.
- HEALTHCHECK hits `/health` (pure liveness, no deps) — container stays "healthy" while Qdrant is down, which is what orchestrators want; `/ready` is readiness. `start-period=10m` covers boot-time ingest. Uses `httpx` — already in the image.

## docker-compose.yml
- Qdrant ports bound to `127.0.0.1`: no auth — must not be LAN-reachable. App reaches it over the internal network (`QDRANT_HOST=qdrant`); 6333 REST (used), 6334 gRPC (local `prefer_grpc` ingest only).
- Qdrant healthcheck is a bash `/dev/tcp` connect — no wget/curl in the image; Qdrant only listens once ready.
- `env_file: .env` optional; only `QDRANT_HOST` is overridden — everything else (`GROQ_API_KEY`, `QUERY_REWRITE`, …) falls back to `app/config.py` defaults.
- `models` is a named volume on purpose: seeds pre-warmed ONNX models from the image on first create; a bind mount would mask them → re-download.
- App `restart: on-failure:3`, not `unless-stopped`: `startup.py` exits 1 on ingest failure — unless-stopped would retry forever, re-downloading JMdict every time.
- Ports: `APP_PORT` changes only the host side; the container side is fixed at 8000. `PORT` (read by `startup.py` and the HEALTHCHECK) is for non-compose platforms (Cloud Run) — setting it via compose/.env breaks the mapping.
- `docker compose down -v` discards the warmed `models` volume — the next start re-copies the pre-downloaded embedding models from the image.
- If external hostnames (HF Hub, ftp.edrdg.org, Groq) fail to resolve from inside the container, copy `docker-compose.override.yml.example` to `docker-compose.override.yml` to pin public DNS resolvers.
- Container is API-only (`/docs`, `/health`, `/ready`); frontend is the SvelteKit static site in `web/` (Cloudflare Workers assets).

## app/api.py (HTTP API)
- Endpoints: `GET /health` (liveness), `GET /ready` (readiness — real Qdrant query), `GET /search?q=…&n=10&mode=auto`, `GET /kanji?chars=例訓` (batch hover cards), `GET /kanji/{char}?strokes=true` (stroke order from the committed `data/processed/strokes.json`), `GET /kanji/random`, `POST /explain`, `POST /explain/stream` (SSE), `POST /feedback`. OpenAPI is at `/openapi.json`.
- Regenerate the committed schema + frontend types with `uv run python scripts/export_openapi.py` then `cd web && npm run gen:api` — CI fails if either drifts.
- The pipeline can also run on the host instead of in the container (ingestion is off by default without `INGEST_VIA_DOCKER`): `scripts/download_edrdg.py` → `scripts/download_kanjivg.py` → `scripts/build_chunks.py` → `scripts/ingest.py` (all via `uv run`).

## eval/
- Retrieval evaluation and model benchmarking (`eval/eval.py`, `eval/embed_model_bench.py`) run in the dev environment (`uv run`) — all their imports are runtime deps, so no extra group is needed.
- Everything they produce stays local: candidate model downloads land under `models/fastembed/` (git- and docker-ignored — never shipped) and run outputs in `eval/results/` (gitignored — curated headline reports are committed under `eval/reports/`). Only MiniLM + bm25 are baked into images; any other dirs under `models/fastembed/` are one-off bench leftovers, safe to delete (re-running the bench re-downloads them).

## web/ & Footer Licensing
- EDRDG Licence terms ([licence.html](https://www.edrdg.org/edrdg/licence.html) & [sample.html](https://www.edrdg.org/edrdg/sample.html)):
  - Web servers providing dictionary lookups must acknowledge JMdict/KANJIDIC on each screen/page foot, attribute EDRDG as property owner, and link to the project wiki pages, EDRDG homepage, and the licence statement.
  - Section 3.2.3 permits general acknowledgement when dictionary files are mixed with other sources (Tatoeba / Tanaka Corpus, KanjiVG).
  - `sample.html` explicitly allows flexibility: *"Any reasonable variant of the above is suitable."*
- Options considered for `Footer.svelte`:
  - **Compact parenthetical (chosen)**: `Dictionary data powered by JMdict and KANJIDIC2 (EDRDG, CC BY-SA 4.0)` where `EDRDG` links to `https://www.edrdg.org/` and `CC BY-SA 4.0` links to `https://www.edrdg.org/edrdg/licence.html`. Keeps the footer visually lean and structurally symmetric with neighboring attributions `(Tatoeba, CC-BY 2.0 FR)` and `(Ulrich Apel, CC BY-SA 3.0)`.
  - **Explicit phrasing variant**: `... (property of EDRDG, used under licence)` — slightly longer text, matches sample wording closer.
  - **Verbose multi-line sample**: Full boilerplate paragraph from `sample.html` — compliant but visually cluttered in the app footer.

## web/src/app.css (Design Language)
- The stylesheet blends three product references, kept out of code comments since they're brand names:
  - **Clay** — warm off-white canvas (`--bg: #fcfaf6`), rounded vibrant cards, controlled saturated accents.
  - **Cohere** — editorial restraint: serif/display headings, mono micro-labels (`--font-mono`), muted stats lines.
  - **Warp** — warm charcoal dark mode (`--bg: #0f1620`), compact precision controls, pill chips.
- Brand-name mentions were removed from in-file comments (palette chips, search pills, result cards, stats line) to keep source vendor-neutral; this section is the canonical record of the inspirations.

## Cloud Run deploy from GitHub Actions — deferred

- Cloudflare is **not** in `.github/workflows/ci.yml`. That file is validation-only (`contents: read`, ruff/pytest/OpenAPI + `openapi.d.ts` drift, svelte-check, vite build). The `reikun` Worker ships because the Cloudflare dashboard is git-connected to `main`.
- Cloud Run has no such hook: `gcloud run deploy reikun-api --source . --region europe-southwest1` is still manual. A `git push` never updates the API.
- Two ways to get push-to-`main` → live:
  - **Cloudflare analog** — Cloud Run console **Set up continuous deployment** (Cloud Build trigger on `main`, GitHub↔GCP OAuth, no repo secrets). Restrict included files to `app/** scripts/** pyproject.toml uv.lock Dockerfile .gcloudignore data/processed/**`. Does **not** wait for `ci.yml` unless branch protection requires it. This is the **[LATER]** path in `Deployment.md`.
  - **GitHub Actions + Workload Identity Federation** — a `deploy-api` job with `needs: [backend, frontend]`, `id-token: write`, path filters, then the same `gcloud run deploy --source .`. No JSON key in secrets. Draft: [`ci.yml.tmp`](ci.yml.tmp) (copy over `.github/workflows/ci.yml` if this is ever wired). One-time GCP: WIF pool + OIDC provider (condition on `OWNER/Reikun` + `refs/heads/main`) + `github-deploy@reikun` SA with `run.developer`, `iam.serviceAccountUser`, `cloudbuild.builds.editor`, bound as `workloadIdentityUser`.
- **Not doing either now.** API Python changes rarely enough that a local `gcloud run deploy` is fine; the target is an Oracle always-free instance anyway, so Cloud Run CD setup (WIF ceremony or a Cloud Build trigger) would be throwaway.
- Do not add deploy to the current CI jobs as they stand — they run on every PR with `contents: read`. A JSON service-account key in GitHub secrets is the rejected path.
