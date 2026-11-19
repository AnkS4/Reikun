# Contributing

Thanks for taking a look. This is a small project with a strict local-mirror
discipline: both frontend variants are maintained in lockstep, and everything
that can drift behind a shared source does it.

## Layout

| Path | What it is |
|---|---|
| `app/` | FastAPI backend (API + server-rendered no-JS UI at `app/lite/`) |
| `web/` | SvelteKit SPA (`adapter-static`, deployed to Cloudflare) |
| `i18n/` | Shared translation tables (`en`/`es`/`hi`/`ja`/`mr`) — the single source for both variants; lite loads them at runtime, the SPA at build time |
| `kana.json` | Shared kana charts (single source for both variants) |
| `docs/api/openapi.json` | Generated OpenAPI schema (regenerated from `app/`) |
| `tests/` | pytest (no Qdrant or LLM needed) |

## Local development

```bash
docker compose build web app && docker compose up -d web app
```

SPA at http://127.0.0.1:5173, API/lite at http://127.0.0.1:8000.

## Checks (CI runs exactly these — keep them green)

```bash
uv sync --locked
uv run ruff check .
uv run ty check app                      # types (app/ only)
uv run pytest -q                         # no Qdrant/LLM required
uv run python scripts/check_i18n.py      # i18n key/placeholder parity
uv run python scripts/export_openapi.py && git diff --exit-code docs/api/openapi.json

cd web
npm ci
npm run check                            # svelte-check (types)
npm run build                            # full production build
npm run gen:api && git diff --exit-code src/lib/openapi.d.ts
```

## Rules that keep the repo sane

1. **One shared source for every duplicated thing.** UI strings: `i18n/`.
   Kana tables: `kana.json`. Icons: generated from `lucide-static` via
   `npm run sync:icons` (SPA) and `scripts/build_lite_icons.py` (lite subset
   font, byte-reproducible). lite's design tokens: generated from
   `web/src/app.css` by `scripts/sync_lite_tokens.py` (CI gates it).
2. **Both variants or neither.** Any user-visible feature lands in the SPA and
   lite, or it doesn't land. lite stays free of client-side JavaScript.
3. **Numbers go through the formatters** (`formatNumber` / `_fmt_count`) —
   Devanagari digits + Indian grouping for hi/mr.
4. **Conventional Commits, one logical change per commit**, with the prose
   in `CHANGELOG.md`'s `## [Unreleased]` section.
5. **Attribution**: third-party code/data stays covered by the repo-root
   `NOTICE` (icons ISC, fonts OFL-1.1, EDRDG data CC BY-SA 4.0, Tanaka Corpus
   CC-BY 2.0 FR, KanjiVG CC BY-SA 3.0).
6. `pyproject.toml`/`uv.lock` bumps ride in their own `chore(deps)` commit,
   like any dependency roll-up, and never mixed with feature work.

## Release

1. `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD` in CHANGELOG.md, add a
   fresh `## [Unreleased]` header.
2. Bump `pyproject.toml`, `web/package.json` (+ `npm version --no-git-tag-version`
   for the lockfile), and regenerate `docs/api/openapi.json`.
3. `gh release create vX.Y.Z --notes-file local/notes/releases/X.Y.Z.md`
4. `git push && gcloud run deploy reikun-api --source . --region europe-southwest1`
   then `local/scripts/deploy/prune-revisions.sh` (the API redeploy is manual;
   the web app deploys itself on push via Cloudflare).

