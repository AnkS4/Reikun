# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-10-26

### Added
- Qdrant Cloud hosted inference: Optional `QDRANT_CLOUD_INFERENCE` flag enables Qdrant Cloud to handle embedding (dense + sparse) via `models.Document`, removing FastEmbed/ONNX from the container. When enabled, the API sends plain text to Qdrant instead of pre-computed vectors. Requires Qdrant Cloud (QDRANT_URL) and uses the free tier's request budget (~0.05–0.18 s/query observed). Model names must be fully qualified (e.g. `sentence-transformers/all-MiniLM-L6-v2`). Ingest scripts still use local FastEmbed, so query-side savings alone drops ~90 MB of models from the production image
- Multi-provider LLM support: Grammar explanations and query rewrites now support Groq, Gemini, Cohere, and Nebius via a unified OpenAI-compatible abstraction (`app/llm.py`). Switch providers with `LLM_PROVIDER` env var; each provider has default model(s) (primary plus an optional fallback) configurable via `LLM_MODEL` / `LLM_MODEL_FALLBACK` overrides; optional `LLM_BASE_URL` overrides the provider's endpoint (regional or self-hosted)
- Japanese-pivot rewrites: `QUERY_REWRITE=auto` now asks the LLM for one JSON object — a 1-3 word English gloss plus 1-3 ranked Japanese dictionary headwords — and the exact-Japanese route searches the headwords directly (the English gloss stays the display value and the fallback when no pivot resolves). The prompt carries dictionary-form and usage guidance (静か not 静かな, スーパー not 店, 嬉しい vs 幸せ…), and parsing tolerates code fences and non-JSON replies so small models degrade to the old single-gloss behaviour
- Descriptive-model sweep report: `eval/reports/descriptive_models.md` + `.json` score Hit@1/2/5 for every shipped provider/model pair over the 60 descriptive queries under the current Japanese pivot — Groq `openai/gpt-oss-120b` leads at 57/60 Hit@1; `eval/reports/README.md` indexes it as a sixth report family
- SvelteKit web container: Added a SvelteKit dev server to Docker Compose (`web` service) for local development at http://localhost:5173
- Provider display: Grammar explanations now show the LLM provider name alongside the model in the UI and SSE payload (`provider` field); the regenerated OpenAPI schema (`docs/api/openapi.json`) and web types carry it

### Changed
- Gemini default model: removed `gemini-3.5-flash` (free tier is capped at 20 requests/day); the Gemini provider now defaults to `gemini-3.5-flash-lite` only
- LLM SDK migration: Replaced `groq` SDK with `openai` SDK (v3.36.1) for unified provider support across all backends
- In-container ingest control: `INGEST_VIA_DOCKER` moved from a Docker build arg to a runtime environment variable. Enable with `INGEST_VIA_DOCKER=1 docker compose up -d --build` (do not set in `.env` — it's a one-time boot flag)
- Dockerfile simplification: All images now include rsync and the ingest dependency group (previously conditional on `INGEST_VIA_DOCKER`), removing build-time branching
- Footer placement: Footer component moved from individual pages to the root layout (`+layout.svelte`) for consistent display across all routes
- .env.example reworked: LLM-provider block (`LLM_PROVIDER`, per-provider API keys, per-provider model override examples, `LLM_BASE_URL`), `QUERY_REWRITE` set to `auto` (the Japanese pivot), `QDRANT_CLOUD_INFERENCE` documented, and `INGEST_VIA_DOCKER` removed from the file with a note to pass it as a compose prefix
- Versions: API 0.9.0 (pyproject + openapi), web 0.9.0
- README restructure: Evaluation section split into ranking (300 queries) vs descriptive (60 queries) with a per-provider model table, environment variables consolidated into `docs/configuration.md`, Tech Stack trimmed, and the brand emblem (`assets/emblems/emblem.svg`) replaces the themed-logo picture block
- Dependency updates: qdrant-client 1.19.1 → 1.20.0, fastembed 0.9.0 → 0.9.1, openai 3.36.1 → 3.37.0, fastapi 0.159.1 → 0.162.0, starlette 1.9.0 → 1.10.0

### Fixed
- Duplicate footers: with the Footer moved into the root layout (`+layout.svelte`), the homepage, `/conjugations` and `/kanji-group` still imported and rendered their own `<Footer>` — those routes displayed the footer twice. The per-page copies are removed; the layout is the single renderer now
- Footer column: rendered as a sibling of `main`, the footer inherited no width constraint and stretched edge-to-edge across the viewport; it now carries the same centered 50rem column and side paddings as the page content (including the 680px breakpoint's tighter padding)
- Web Docker build: `npm run build` invoked `bash ../scripts/sync-assets.sh`, but the `web` image is Alpine (no bash) and the `web/`-only build context does not contain `../scripts` — the build aborted with `bash: not found`. The sycn is replaced with a portable Node step (`web/tools/sync-assets.mjs`) that copies brand assets when the repo-root `assets/` directory is inside the context and skips silently otherwise, since the synced files are committed to `web/static/`
- `web/.dockerignore` added: the host's `node_modules` (85 MB) was going into the build context and would have overridden the `npm ci`-installed, platform-specific packages; the context now carries source only

### Removed
- `local/` from the repository — notes, skills, benchmark results, the OCI-A1 retry runner and autorecord scripts had been tracked since 0.8.0 despite never being meant to ship. History since then is rewritten so no commit contains them (v0.8.0 / v0.9.0 are re-published at the rewritten commits), and `.gitignore` now ignores `local/` so it can never be tracked again

## [0.8.0] - 2026-10-21

### Added
- Category-wise headword report: `eval/eval.py --report` writes the curated per-category scores to `eval/reports/headword_eval.md` + `.json` (fixed-width score block, markdown table, and the miss list), and every headword run now prints the category breakdown. Default config on the 360-query gold set: Hit@1 97.3% over the 300 ranking queries (en_verbs 58/60, en_words 56/60, ja_hiragana 58/60, ja_words 60/60, ja_katakana 60/60), Hit@5 300/300
- Evaluation docs moved to `eval/reports/eval.md` (was the repo-root `eval.md`) and the README now carries the category-wise results table; the retrieval-config and JA reports were regenerated against the 360-query set — default config Hit@1 0.84 / MRR 0.861 (was 0.81 / 0.845)
- `eval/eval_ja.py` merged into `eval/eval.py`: the Japanese view was the IR suite over a slice of the same gold set with a forked metric loop and report writer. The IR suite now computes per-category Hit@k alongside MRR (so the JA view falls out of the same run), and `--ir --subsets ja-only --publish --report-name retrieval_eval_ja` produces the same curated report from one code path
- `eval/eval.py` subset selection: no flag now runs every category except `en_descriptive` (the 300 ranking queries), `--subsets all` covers all 360, and the aliases `en-only` / `ja-only` / `list` (category catalog) are available alongside the individual category names. `--help` gained a worked-examples block
- Every curated report now carries a provenance stamp (generated-at, app version, git commit, run configuration) on its first lines and in a JSON `meta` block, written by a shared `eval/report_meta.py` — and `eval/reports/README.md` indexes the reports: what each measures, how to regenerate it, and when it was last run
- Conjugation tables on word cards: JMdict's own verb/adjective class tags now generate a full inflection paradigm per entry (`app/conjugation.py` — godan 9-ending chart, ichidan with potential/passive merged, kuru double-stem 来ます/こない, suru noun+する, i-adjectives incl. the いい→よく irregulars, 行く's special 行った). Cards render a collapsible Conjugations table (form / written form / kana) and, when the search itself was an inflected form (走った), an info bar naming the row ("Past form of this word"). Archaic nidan, aru-class and auxiliary-only entries generate nothing
- Type-a-conjugation search: inflected surfaces go into a new `infl_forms` payload field, so 走った exact-matches 走る through the retrieval arm once the collection is re-ingested; against pre-reingest data the API degrades gracefully (one-time index probe, no 400s)
- Japanese-query ranking formula: the ja route now layers the same FormulaQuery priors the English route uses (commonness + canonical rule) on its fused BM25 pool, instead of bare frequency-blind RRF
- Gold-set additions to the headword benchmark: tomato, garlic, eraser, potato, apartment (en_words) and じてんしゃ (ja_hiragana)
- `--reuse-vectors` ingest mode: a payload-only refresh that transplants the stored dense/BM25 vectors back onto rebuilt points after verifying the embed inputs didn't drift (re-embedding only true drift), turning the post-0.8.0 field changes into a minutes-long `--update` instead of a ~1 hr full re-embed — snapshots transport existing vectors only, so this is the fast path without the ~1 hr cost

### Changed
- Canonical ranking boost is commonness-gated: `CANONICAL_BOOST × wf_score × first-sense × (0.7 + 0.3·commonness)` — untagged entries keep only 70% of their corpus-frequency prior, so polluted Zipf estimates for rare kanji spellings can no longer edge out the everyday word by a hair (消しゴム now beats 字消し for "eraser", 大蒜 beats に文字 for "garlic")
- Headword-index trie now stores each candidate's corpus frequency (`wf`) and ambiguous-candidate lists (segment tooltips) lead with the most common entry instead of ingest order; trie rebuilt 27→30 MB
- Search-row compact layout: shuffle / furigana / JLPT drop to one right-aligned utility strip with the row's standard gap — the auto margin used to sit on every button, splitting the free space and leaving a hole between shuffle and あ
- Furigana lives only on the search row's あ button now — the Appearance popover keeps theme as its single preference instead of duplicating the toggle
- Headline-gloss prior in the English ranking formula: a new `head_gloss_keys` payload field carries the gloss keys of an entry's *first gloss of its first sense* (JMdict orders a sense's glosses by centrality), and the en_word formula adds `HEAD_BONUS × wf_score` when the query is that headline translation. It separates a true translation pair from a broad sense that mentions the query late — 出る ("to leave" is gloss 1) now beats 行く (gloss 4), 問う/尋ねる ("to ask") beat 頼む (gloss 3), 海 beats 鱒 ("trout", "sea trout"), 生きる ("to live") beats 有る ("to be"), 求める ("to want") beats 要る ("to be needed")
- Simplified ranking formula: the canonical prior is now `CANONICAL_BOOST × wf_score × first-sense-match × commonness` — the commonness gate lost its floor (a `0.7 + 0.3c` shape scored identically but needed a second knob, so plain `commonness` does the same job with one number) — and the four retrieval arms are fused with **equal** RRF weights. Every weight shape measured (1.05/1/2.5/2, 1/1/2/2, 1/1/1.5/1.5, all-equal, asymmetric exact arms) scored identically: the formula's priors do the discriminating, the weights only decide which arm reaches the pool first
- The fused candidate list is now twice the per-arm cutoff (`FUSION_FACTOR = 2`): the arms still fetch 200 each, but the fusion returns 400, so entries that rank deep in *every* arm (時間 reaches the 4-arm RRF at ~rank 204, through the exact arms only) still reach the formula instead of falling out of the pool on a boundary tie — this is what keeps "time" in the top 2
- Retrieval pool raised to the level the benchmark measures (`PREFETCH_MIN` 100 → 200) — the API and the eval were previously running different pools
- Gold set expanded to 60 queries per category (360 total, up from 306): 54 new rows across en_words, en_verbs, en_descriptive, ja_words, ja_hiragana and ja_katakana, each validated against the dictionary (the expected headword exists, the English query is a gloss of it, the Japanese query resolves to its entry). The file now carries a counting rule at the top — the per-category counts are fixed, so the Hit@1 rates stay comparable across runs
- Gold set: Hit@1 137 → 149 of 156 (87.8% → 95.5%), Hit@2 154, Hit@5 156/156 — en_words 51/55, en_verbs 49/50, ja_hiragana 49/51
- Chunks schema bumped to 3 (new conjugation fields + gloss head-words) and again to 4 (new `head_gloss_keys` field); re-ingest required for the new payload data (`--update --reuse-vectors`)
- Python 3.14: `.python-version`, `requires-python`, ruff `py314`, Dockerfile base and CI all pinned to 3.14; free wins from the new runtime (PEP 649 deferred annotations for faster imports, the tail-call interpreter) without API changes
- Vite 8.3.5 (dev dependency) — clears the high-severity advisories in the dev server (cross-origin script execution via custom middleware, `server.fs` escapes, `launch-editor` flag handling on Windows). Dev-server only: the production bundle does not include Vite
- Versions: API 0.8.0 (pyproject + openapi), web 0.8.0

## [0.7.0] - 2026-10-21

### Added
- Inflection-aware results: searching an inflected form (走った) now shows the ROOT entry in the results list — 走る【はしる】 with commonness, examples and level — instead of a pseudo-entry for the conjugated surface. The segment chips keep the surface form; verified across polite/negative/causative/passive forms (`tests/test_segmentation.py`)
- Related words: result cards render a searchable row of words that share a kanji with the headword (走る → 滑走, 滑走路, 完走…), ranked by the kanji table's frequency-ordered common-word data; shipped inside `/search` payloads (`SearchResult.related`), no extra client round-trips
- Clickable kanji metadata: the kanji card's strokes / grade / JLPT badges are now links to a paginated kanji-grid page (`/kanji-group?by=&value=&page=`) listing every kanji sharing that attribute, frequency-ranked, with Previous/Next paging — kanji themselves, not words
- Number×counter reading table: fused counter chips carry the contextually correct reading (2日【ふつか】, 13日【じゅうみっか】, 20日【はつか】, 1人【ひとり】, 4人【よにん】, 4時【よじ】, 20歳【はたち】, 10分【じゅっぷん】); untabled regular combinations show no furigana rather than a wrong one
- Counter query alias: digit-typed counter queries (25日, 1人) resolve to their kanji-spelled JMdict headwords (二十五日, 一人) so bare searches land the real entry cards
- Furigana toggle: a visible あ button in the search row (plus Show/Hide in the Header's Appearance popover) turns all ruby off for reading practice; preference persists per browser
- Qdrant keep-alive: a daily Cloudflare Workers cron (`web/worker.js`, `17 9 * * *`) pings `/ready` so the free vector cluster doesn't auto-pause; optional `ALERT_WEBHOOK` secret for failure pings; configured via `web/wrangler.jsonc` (`main` + `triggers.crons` + `vars.API_URL` + observability)
- Cloudflare Web Analytics: cookieless JS beacon, injected when `PUBLIC_CF_ANALYTICS_TOKEN` is set in the web build env (get the token from the CF dashboard: Web Analytics → add reikun.app)
- Kanji group API: `GET /kanji/group?by=strokes|grade|jlpt&value=&n=&offset=` returns paged kanji entries with a `total` count

### Changed
- `/search` results carry a `related` word list per entry; `/kanji/group` reshaped from word list to kanji list with pagination — `docs/api/openapi.json` and `web/src/lib/openapi.d.ts` regenerated together
- The Header's theme popover is retitled "Appearance" and also holds the furigana Show/Hide control

## [0.6.0] - 2026-10-18

### Added
- Asset sync automation: Added `scripts/sync-assets.sh` to automatically copy brand assets from `assets/` to `web/static/` during build
- Asset organization: Created `assets/images/` subfolder for OG images (og-image.png/svg)
- CHANGELOG.md: Added changelog documentation following Keep a Changelog format
- SEO meta tags: Canonical link, OG + Twitter card tags, WebApplication JSON-LD
- Prerendered /about page with sitemap inclusion
- Global SSR: All routes prerender with real HTML for crawlers
- Keyboard navigation and recent searches
- Loading skeletons for better UX
- Accessibility improvements
- Search button redesign with glass-face CTA and inner lip
- Safe localStorage wrapper
- Mixed-language search improvements
- Refined sharing and controls
- Stroke playback improvements
- Rate limiting: Per-client request limits for `/explain` and `/search` endpoints to protect Groq quota and CPU resources
- GZip middleware: Automatic compression for responses (excluding SSE streams)
- Wake banner: Server wake-up indicator for cold-start scenarios
- Backend state management: Shared API health state tracking
- Security headers: X-Frame-Options, CSP, Permissions-Policy, COOP for enhanced security

### Changed
- Build process: Updated `web/package.json` to run asset sync automatically during `npm run build`
- Asset structure: Moved OG images from root `assets/` to `assets/images/` subfolder
- OG image paths: Updated meta tags in `web/src/app.html` to reference `/images/og-image.png` instead of `/og-image.png`
- Asset sync script: Moved from root directory to `scripts/` directory for better organization
- Dependency bumps across web and backend
- API error handling: Improved error normalization and retry logic
- Storage: localStorage operations wrapped in safeStorage to handle blocked storage
- API client: Shared ready promise for status indicator, automatic retries with exponential backoff
- SSE stream parsing: More robust frame parsing with error recovery

### Fixed
- Browser storage hardening
- API error handling
- Kanji-tip whitespace
- Random kanji button: Added loading state to prevent duplicate requests
- SSE stream: Better error handling for malformed frames and unexpected stream termination

### Removed
- Unused production assets: Removed `web/static/emblems/` and `web/static/logos/` directories (not referenced in web application)
- Old logo files: Consolidated brand assets into `assets/` directory structure

### Documentation
- Updated README.md to document the new asset structure and automated sync process
- Added note about manual sync capability via `bash scripts/sync-assets.sh`

## [0.5.0] - 2026-10-07

### Added
- Sudachi-grounded grammar hints: Morpheme-level surface → lemma (POS, conjugation) hints ground conjugation identification for LLM
- JA eval suite: `eval_ja.py` for Japanese subset Hit@k reporting (ja_words / ja_hiragana / ja_katakana)
- Web refresh: Design-language refresh with custom center-anchored tooltips
- Keyboard shortcuts: "/" and ⌘K focus shortcuts for search input
- Per-phase latency breakdown: Rewrite/embed/retrieve/segment timing displayed in search meta
- robots.txt and sitemap.xml for deployed site SEO
- Dependency group split: `ingest` group carved out of `dev` for Docker optimization

### Changed
- Grammar explain: Shared create() wrapper for retry logic; token budgets increased (llm_rewrite 150→500, eval judge 400→900)
- Retrieval: segment_ms measured and surfaced in meta/SearchMeta; dataclasses get slots=True
- API: Annotated Query params (B008), explicit rewrite payload, version from config.APP_VERSION
- Dockerfile: Model-warm layer moved ahead of source copy to avoid re-downloading ONNX weights on code edits
- Eval: eval/results → eval/reports (curated reports committed, run outputs gitignored)
- Linting: All ruff ignores removed (E501, RUF001-003, B008, B911, C408, PERF401, RUF100)
- Web: Tooltip edge-clamp to stay in-viewport and clear sticky search bar
- Version: pyproject.toml is single source of truth (config.APP_VERSION reads via tomllib)

### Fixed
- Kana exact-match fix in search routing
- Kanji-tip whitespace fix

### Removed
- Cohere LLM dependency (replaced by Groq in v0.4.0)
- Cohere-era `thinking_budget` kwarg from grammar_explain

## [0.4.0] - 2026-10-05

### Added
- Groq grammar explanations: Cohere replaced by Groq — openai/gpt-oss-120b primary, gpt-oss-20b fallback
- Retry classification: 429 retry-after honored, long quota waits fail over immediately, permanent errors bail
- Query rewrite and eval judge moved to Groq
- Input validation: validate_input() caps sentence/meaning/hint → 422 on both /explain routes
- Comprehensive test suite: 33 tests for failover, retry classes, stream failover, input caps, prompt-shape regression
- .gcloudignore for Google Cloud deployment

### Changed
- Prompts: English-only prose, bullets anchored to surface fragments, per-level max bullets/words-per-bullet/total caps
- Token budgets: Sized by measured reasoning usage
- Web: Sentence chips equalize heights, search pills refreshed
- Grammar explain: lru_cache on level system prompts, explanations deliberately not cached
- Dependencies: groq is the only LLM SDK (runtime), cohere dropped

### Fixed
- Long quota waits now fail over immediately instead of hanging
- CI test hermeticity: test_make_groq_client_hermetic (no GROQ_API_KEY in CI)

## [0.3.0] - 2026-10-04 (Untagged release between v0.2.0-streamlit and v0.4.0)

### Added
- SvelteKit 3 SPA frontend with adapter-static (Cloudflare Pages/Vercel ready)
- FastAPI HTTP API with standalone routes (asgi_app.py removed)
- New GET /kanji (batch), /kanji/random?level=, strokes in /kanji/{char}
- JSON shaping for furigana/ruby, kanji card, segment chips, batched hover, structured KanjiVG strokes
- Telemetry: telemetry.py swaps feedback sink between stdout JSON and SQLite
- OpenAPI schema committed + generated TS types
- URL-driven search and kanji card
- Streamed grammar explain
- Theme picker (light/dark/system)

### Changed
- API: api.py owns routes directly (lifespan warmup, /health vs real /ready, CORS via env, typed responses)
- Dockerfile: Slim image (627 MB), no Streamlit, non-root, /health probe
- Startup: startup.py execs uvicorn
- Dependencies: UI deps moved to uv 'ui' group

### Removed
- Streamlit UI (moved to separate frontend)

## [0.2.0-streamlit] - 2026-09-24

### Added
- Initial Streamlit-based release
- Hybrid search with query routing (dense vector embeddings + BM25 sparse vectors)
- Query rewriting with heuristic and optional LLM support
- Sentence breakdown with furigana and word-by-word gloss
- Kanji lookup with stroke-order diagrams (KanjiVG)
- Grammar explanations calibrated to JLPT levels (N5–N1)
- Feedback and telemetry system
- Docker and Docker Compose support
- Evaluation scripts for retrieval accuracy and embedding model benchmarking
