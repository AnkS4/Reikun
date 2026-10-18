# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
