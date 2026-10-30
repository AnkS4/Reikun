# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-10-30

### Documentation
- Screenshot sheet re-captured on the v1.0 UI (8 shots, `docs/screenshots/`): `03-kanji-hover` now hovers the **食** headword card's kanji from a 食べる word search (meanings, ON/KUN readings, strokes · Grade 2 · JLPT N5 · frequency), giving the sheet two distinct kanji demos — the anchored 国 card from 04's typed kanji search plus this word-result hover — and `01`/`02`/`07`/`08`/`09`/`10` all re-verified against current behavior
- Demo video gains a compact tight crop for text-dense playback: `demo_v1.0_tight.mp4` (920×1080, the content column cropped symmetrically from the 1920×1080 master — header icons and the back-to-top button fall outside the measured content window at x 528–1367) and `demo_v1.0_tight.gif` (560 px / 2× / 8 fps, under 5 MB); the README hero now embeds the tight GIF, the master `demo_v1.0.mp4/gif` and the vertical/zoom variants stay unchanged
- README carries a Momentum Guide: Nebius & NVIDIA section: Token Factory as the shipped default LLM provider (`LLM_PROVIDER=nebius`, `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`) powering grammar explanations and Japanese-pivot rewrites, Nemotron's 93.3% Hit@1 on descriptive queries with reasoning-free warm calls under 1 s (`chat_template_kwargs: {"enable_thinking": false}`), and Groq/Gemini/Cohere as one-env-var alternates with production on Nebius + Nemotron
- Devpost submission thumbnail added under versioned assets: `assets/images/devpost-thumbnail.svg` (1200×800, 3:2, the OG lockup recentered for the new frame) + rendered `devpost-thumbnail.png` (65 KB)

- Versions: API 1.0.1 (pyproject + openapi), web 1.0.1

## [1.0.0] - 2026-10-30

### Changed
- Nebius explanations/rewrites run thinking-free: `Provider` gained an `extra_body` field (`app/llm.py`) merged into every `chat.completions.create` call by `grammar_explain._complete`, and the Nebius entry sends `chat_template_kwargs: {"enable_thinking": false}`. Nemotron-3 models reason by default, and reasoning tokens consumed each JLPT level's token budget before prose began — explanations truncated (`finish_reason=length`), retried at a 1.5× budget, and could silently hand off to the fallback model (production call timing went 43–85 s). Nebius ignores `reasoning_effort`, so the chat-template flag is the supported off-switch (probe: 0.34 s, `reasoning: null`; prod verification: warm call 0.9 s, first post-deploy call 27.5 s before settling). Local picks this up on process restart, production on redeploy. The eval sweeps ran thinking-on (see `eval/reports/descriptive_models.md` note)
- Nebius ships as the default LLM provider: `LLM_PROVIDER` defaults to `nebius` with `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` in `app/config.py`/`app/llm.py`; README and configuration docs follow, and eval metadata reports `LLM_MODEL` plus the active provider (`LLM_PROVIDER`) instead of a hardcoded Groq id. Groq remains a one-env-var switch (the production service keeps its `groq-api-key` secret wired)
- Explanation brevity is enforced end-to-end: level ceilings tightened (N5 4 bullets × 30 words / 160 total, down to N1 3 × 18 / 70), `_BASE_RULES` forbids punctuation-only bullets, fragment revisits and analysis mirroring ("context to LOCATE forms, never a checklist"), and a deterministic `tidy_bullets` post-pass (`app/grammar_explain.py`) dedupes fragments, drops punctuation bullets, strips redundant parentheticals (`**は** (は)` → `**は**`) and enforces the bullet cap on `/explain` (including the stream endpoint's blocking fallback); the live SSE stream now applies the same per-line rules as the text arrives (`_tidy_stream`, line-buffered, sharing the `_BulletTidier` state machine with `tidy_bullets`), so echo parentheticals like `**が** (が)` / `**を** (を)` and repeated-pattern bullets are stripped mid-stream and never paint in the web UI (de-parenthesising also eats the adjacent space, so the result is `**が** —`, not `**が**  —`). Prior degenerate outputs (20+ bullets, fragments repeated 3–4×) now land at ≤ 4 bullets / ~50 words / ~1–3 s. The rules' example bullets are now filled-in sentences — the old `〜ている … — …` scaffold shape invited placeholder replies (an N1 call returned three pattern-name skeletons ending `— …`); `tidy_bullets` now also drops such contentless scaffolds, strips tilde-blind repeats (`**〜たい** (たい)` → `**〜たい**`), and falls back to the model's original text if everything would be tidied away
- Homepage example chips rotated (same five kinds, fresh content): `water`, `日`, `食べる`, `How do you say front door in Japanese` (→ 玄関, common, first card), `あの店のケーキはとても美味しいです。` (`web/src/routes/+page.svelte`)
- Branding unified on the subtext **“Semantic Japanese Dictionary & Reading Assistant”** — the header hero badge, page titles and OG/Twitter/JSON-LD metadata, README, `pyproject.toml`, and the FastAPI description now use the same line, with **Reikun (例訓)** as the wordmark; the OG image follows the homepage hero arrangement — the standalone emblem sits inline with the wordmark and the kanji (**例訓** in Noto Sans JP, the muted-ink treatment of `.hero-heading`'s `.brand-kanji`), the subtext rides the mono badge pill like `.hero-badge-tag`, and the feature lines (conjugation tables included) are centred beneath with the frame's margins balanced on both axes — re-rendered from the SVG to the 1200×630 PNG in Chromium with the brand fonts loaded (Space Grotesk / JetBrains Mono / Inter / Noto Sans JP)
- Interface chrome localized (English and Japanese): a typed `web/src/lib/i18n.svelte.ts` dictionary with a persisted `reikun-locale` choice (language popover next to the theme picker; `<html lang>` kept in sync) covers the header/status, search chrome, result cards, sentence segments, kanji card/tooltips, conjugations, kanji groups, about page, footer, and the grammar-explanation labels; JMdict glosses, examples and the explanation prose stay English content by design, while client-side API error messages (unreachable/timeout/gateway) are localized — server `detail` text stays English
- SQLite telemetry keeps the raw search text: `searches.query` / `rewritten_query` store the verbatim query alongside the existing SHA-256 hashes (`scripts/feedback_log.py`), and `_migrate` re-adds the raw columns to a hash-only database and rehashes any pre-hash rows in place — old raw text is not recoverable
- About-page privacy copy now says **no cookies** rather than no first-party cookies — verified against the shipped code: preferences and recent searches use `localStorage`, the API sets no cookies, and the Cloudflare analytics beacon is cookieless
- Web Svelte 5 pass: raw state for API responses/records (`$state.raw`), `$derived`/keyed `each` where values were recomputed or unkeyed, the tooltip clamp converted from a `use:` action to an attachment, and the back-to-top scroll listener moved to `<svelte:window>` — bundle behavior unchanged (marked/DOMPurify stay lazy)
- Demo media re-recorded with Cap for Agents, replacing the interim headless injected-pointer recorder. Docs media overall was refreshed for the v1.0 UI: the screenshot sheet was regenerated first — `04-kanji-dialog` is now `04-kanji-card` (the card is anchored inline, not a dialog), dashboard shots retired (no dashboard since the Streamlit removal), two new pages added (`08-conjugations`, `09-kanji-group`) plus `10-no-furigana` (the sentence-breakdown view with readings hidden via the toolbar toggle) — and the videos were then re-recorded with Cap for Agents: a real X pointer (xdotool eased tweens, 90 ms click dwell) drives kiosk Chrome on a private Xvfb display, `cap record` captures it natively (XSHM + XFixes cursor), and the take is finished with Cap Studio polish — spring-smoothed cursor and click ripples; the base takes carry no zoom segments (the old per-click auto-zoom read as glitchy and over-widened the portrait framing), and an optional second landscape export adds content-following, held manual glides at 1.5× — native-resolution, because landscape is captured at 2880×1620 with CSS zoom 1.5 and exported at 1080p — then headless-exported at `--quality web --optimize-filesize`. Chrome runs with hidden scrollbars (flag + a persisted style) so the capture's right edge stays clean, and the portrait CSS zoom is installed from document start (an init script that waits for `documentElement`, plus a post-navigation re-assert), so the mid-tour full-page homes never flash the unzoomed desktop layout. The tour drills into the sentence breakdown (the 美味しい chip jumps to its card, then the 美 and 味 kanji tips are hovered; the old separate 店 hover is gone), focuses the search box through CDP for the soy-sauce/water beats (typing starts immediately instead of idling out the post-navigation input dead zone), and the Explain beat waits for actual prose before moving on. Same seven beats (sentence pill → breakdown → card drill-down → Explain → conjugations → soy-sauce rewrite → 日 strokes → JLPT grid → water → related-word closer), now ~44 s landscape / ~45 s portrait at 60 fps: `demo_v1.0.mp4` (1920×1080, 1.5 MB), `demo_v1.0_vertical.mp4` (1080×1920, 2.6 MB), the landscape-only zoom-glide variant `demo_v1.0_zoom.mp4` (four held manual glides at 1.5×, 2.0 MB), and both GIFs regenerated (README hero `demo_v1.0.gif` at 768 px / 2× / 12 fps, 3.0 MB; vertical at 432 px, 6.8 MB). The tour exits its subpages the way a viewer does: the header Reikun logo returns home from `/conjugations`, and the kanji-group grid is wheeled to its bottom actions where **← Back** lands back on the 日 results before the water search runs; the closer is the two-hop related-word chain water → 水着 (bathing suit) → 水泳 (swimming); all of it supersedes the `demo`/`v2`/`v3`/`v4` variants
- Conjugation coverage is back in sync with the spec published under 0.8.0: the widened modern-class engine (`app/conjugation.py`, ~50 rule rows — 問う/乞う u-class 問うた/問うて, the ある aru-class subset, kureru, zuru (信ずる), vs-s special class (愛する), vs-i phrase verbs on a safe subset (気がします/気がしない), compound kuru (連れてくる), and yoi/ii adjectives) had dropped out of the source in the commit-history rewrites while the 0.8.0 entry kept documenting it, so tables silently narrowed to plain families; the full engine is restored (+186 lines), with the same guardrails — honorific ます-class verbs and 御座る keep the suspect い-insertion cells out, archaic nidan and auxiliary-only entries generate nothing
- `/kanji/group` raised its `value` cap 30 → 50 (`app/api.py`): stroke counts above 30 failed query validation outright, so the highest-stroke kanji (鱻, 麤, 龗) 422'd instead of listing; a bounds test covers both ends and the bogus `by` (`tests/test_api.py`)
- SSE bodies ship raw UTF-8: the `/explain` payload and its streamed chunk frames are json-encoded with `ensure_ascii=False` (`app/api.py`), so Japanese reads as 日本語 in `curl`/log inspection instead of `\uXXXX` escapes, without the per-character ASCII bloat
- Search loading feels intentional instead of glitchy: skeletons are delay-gated (`SKELETON_DELAY_MS` at 250 ms in `web/src/routes/+page.svelte`), so fast answers — above all the random-kanji path — paint the real cards with no placeholder flash, while slow searches fall back to the same skeleton cards after the gate; result cards then enter with a short staggered fade-up (`card-in` in `web/src/app.css`, ~40 ms per sibling capped at the 9th, driven by a forwarded `style` prop on `ResultCard`) under `animation-fill-mode: backwards` so the animation never pins the hover transform, and `prefers-reduced-motion` skips it
- Sentence breakdown keeps the copula as its own chip after a content word: the Sudachi grouping no longer folds です/だ into a preceding noun/pronoun/adjective/na-adjective (`美味しいです` → `美味しい` + `です`, `学生です` → `学生` + `です`, `何ですか` → `何` + `です` + `か`), because the copula is a word, not an inflection tail. The split is deliberately narrow — after an auxiliary/particle or the continuative/attributive forms the local grouping is unchanged (んです, 行きませんでした, 学生じゃないです, 2日です keep their old chips; 静かな stays whole in 静かな部屋です), and copulas are matched by conjugation type (`助動詞-デス`/`助動詞-ダ`) so the past-tense auxiliary だ (`休んだ`, `助動詞-タ`) and ます/た/ない (食べました) still merge; a 30-case test matrix covers the split/merge boundary. The standalone 美味しい chip now maps to the 美味しい result card instead of relying on index alignment

- Versions: API 1.0.0 (pyproject + openapi), web 1.0.0

### Fixed
- Telemetry can no longer fail a request it observes: the SQLite sink wrapped the API call sites unprotected, so a sink error (unwritable database, locked file — the `scripts/feedback_log.py` writers raise raw sqlite errors) turned a successful `/search` into a 500, and inside the `/explain/stream` generator the call sat outside the try, killing the closing `done:` frame after a streamed explanation. `_never_raises` (`app/telemetry.py`) now wraps the `_SqliteTelemetry` methods — a sink error logs one scraper-safe `telemetry_error` JSON line and reads as 'not recorded' (`None`), the same shape as a sink without row ids; the stdout sink needed no wrapper since the logging framework swallows handler errors. Feedback POSTs were already best-effort client-side, so this only ever removed a failure mode
- The conjugation arm's index probe (`app/retrieval.py` `_infl_indexed`) is `@cache`d once per process as its own docstring always claimed: previously every `_exact_filter()` call — two or more per hybrid search — paid a Qdrant `get_collection` round-trip. Either answer latches (the schema is fixed at ingest time and ingest completes before the API boots), so the not-re-ingested state also stops relisting Qdrant on every query, and a transport blip at first use still degrades to "conjugation arm off" rather than erroring
- Docker `web` service shipped a dead API base: `PUBLIC_API_BASE` is baked into the static bundle at build time (`$app/env/public` is `static: true`, and the build image never received the variable — runtime `environment:` values reach nothing at build), so the compose value never landed in the bundle — and its `http://app:8000` would have been unresolvable from a host browser anyway. The service now passes `PUBLIC_API_BASE: http://127.0.0.1:${APP_PORT:-8000}` as a build arg (the app service's published loopback port), and `web/Dockerfile` forwards the `ARG`/`ENV` before `npm run build` (empty falls back to `env.ts`'s `http://localhost:8000` default). Verified in the built bundle: `127.0.0.1:8000` present, `app:8000` gone
- `segment_japanese` shadow-imported `re` over the module-level import and recompiled its mixed-text `_JA_PATTERN` on every call; the pattern is now the hoisted module constant `_JA_RUN`
- Japanese chrome copy points where the English copy points (`web/src/lib/i18n.svelte.ts`): the about-page rewrites sentence reads in passive voice (…書き換えられます), the license sentence uses ライセンスの下で, the not-a-word hint refers to the 「よく使う語」 row actually shown above (`上の「よく使う語」をご覧ください`) instead of a paraphrase that didn't match the visible heading, the approximate-match badge reads おおよそ (title 代替の分割方法 — a different tokenization, not a "splitter tool"), and the recent-searches aria-label is 最近の検索一覧 so it no longer repeats the visible 最近の検索 heading; both locales' copy tip describes the `word【reading】— meaning` format instead of the hardcoded 高い sample word, and the missing-conjugation message uses typographic quotes
- Japanese-route detection strips leading brackets/quotes/punctuation, not just whitespace, before the script check (`_STRIP_PUNCT` in `app/query_rewrite.py`): pivot candidates like 「醤油」 failed `is_japanese` on the leading 「 and were dropped as implausible, silently degrading those queries to the English display gloss

### Documentation
- README carries the defaults end-to-end: Nebius as the default LLM provider, the no-key path called out explicitly (search and kanji work without an LLM when `QUERY_REWRITE=heuristic` or `off`), `npm ci` for the web install, and the demo media swapped to the v1.0 recordings
- `docs/configuration.md` expanded into the env-var reference: a full LLM-provider matrix (provider + key names, model defaults/overrides, running without an LLM) plus variable tables for retrieval/storage (`QDRANT_*`, `SPARSE_MODEL`, `MODELS_DIR`) and serving/telemetry/rate limits (`TELEMETRY`, `CORS_ORIGINS`, `RATE_LIMIT_*`, `TRUSTED_PROXY_HOPS`, `PORT`)
- `.env.example` comments: `QDRANT_HOST` notes the Compose override to `qdrant`, `PORT` says it is host-injected and never set manually for local/Compose runs; `web/.env.example` wording clarifies where the build-time API base applies for production static hosts
- `eval/gold_set.tsv` header comments trimmed to repo-visible references, keeping the fixed per-category counting rule intact

### Removed
- Copy-Japanese button on example rows (`web/src/lib/components/ExampleRow.svelte`); the search-result copy-word control and the share button are untouched
- Superseded demo media: `docs/videos/{demo,demo_v2,demo_v3*,demo_v4*}` variants and the old sheet shots `04-kanji-dialog.png`, `05-dashboard-1.png`, `06-dashboard-2.png`

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
- Internal scratch directory purged from repository tracking: notes, skills, benchmark results, the OCI-A1 retry runner and autorecord scripts had been tracked since 0.8.0 despite never being meant to ship. History since then is rewritten so no commit contains them (v0.8.0 / v0.9.0 are re-published at the rewritten commits), and `.gitignore` now ensures untracked local files can never be committed again

## [0.8.0] - 2026-10-21

### Added
- Category-wise headword report: `eval/eval.py --report` writes the curated per-category scores to `eval/reports/headword_eval.md` + `.json` (fixed-width score block, markdown table, and the miss list), and every headword run now prints the category breakdown. Default config on the 360-query gold set: Hit@1 97.3% over the 300 ranking queries (en_verbs 58/60, en_words 56/60, ja_hiragana 58/60, ja_words 60/60, ja_katakana 60/60), Hit@5 300/300
- Evaluation docs moved to `eval/reports/eval.md` (was the repo-root `eval.md`) and the README now carries the category-wise results table; the retrieval-config and JA reports were regenerated against the 360-query set — default config Hit@1 0.84 / MRR 0.861 (was 0.81 / 0.845)
- `eval/eval_ja.py` merged into `eval/eval.py`: the Japanese view was the IR suite over a slice of the same gold set with a forked metric loop and report writer. The IR suite now computes per-category Hit@k alongside MRR (so the JA view falls out of the same run), and `--ir --subsets ja-only --publish --report-name retrieval_eval_ja` produces the same curated report from one code path
- `eval/eval.py` subset selection: no flag now runs every category except `en_descriptive` (the 300 ranking queries), `--subsets all` covers all 360, and the aliases `en-only` / `ja-only` / `list` (category catalog) are available alongside the individual category names. `--help` gained a worked-examples block
- Every curated report now carries a provenance stamp (generated-at, app version, git commit, run configuration) on its first lines and in a JSON `meta` block, written by a shared `eval/report_meta.py` — and `eval/reports/README.md` indexes the reports: what each measures, how to regenerate it, and when it was last run
- Conjugation tables on word cards: JMdict's own verb/adjective class tags now generate a full inflection paradigm per entry (`app/conjugation.py` — godan 9-ending chart, ichidan with potential/passive merged, kuru double-stem 来ます/こない, suru noun+する, i-adjectives incl. the いい→よく irregulars, 行く's special 行った). Cards render a collapsible Conjugations table (form / written form / kana) and, when the search itself was an inflected form (走った), an info bar naming the row ("Past form of this word"). Archaic nidan and auxiliary-only entries generate nothing; the ある/である-family gets only its safe subset (あり-insertion ます forms, whole-tail negative ある→ない, no potential/passive/causative/imperative), and 御座る (JMdict-tagged plain v5r but ございます-class) generates nothing
- Conjugation coverage widened to JMdict's modern class strings, which the first pass had been silently skipping: `suru verb - special class` (愛する and the 圧する family get the full paradigm), `suru verb - included` (気がする-style phrase verbs get a safe predicate subset — 気がします/気がしない/気がした/気がして, never 気ができる or 気がしろ), `Ichidan verb - zuru verb` (信ずる conjugates like 信じる while the dictionary row keeps ずる), `Ichidan verb - kureru special class` (plain ichidan except the imperative is くれ), `Godan verb with 'u' ending (special class)` (問う/乞う/請う keep the う in 問うた/問うて), `Godan verb with 'ru' ending (irregular verb)` (ある/である/Xがある — あります/ありません, 意味がない, 意味があった), `adjective (keiyoushi) - yoi/ii class` (いい/かっこいい and phrase adjectives such as 仲の良くない), and compound kuru entries (連れて来る / 連れてくる with split き/こ stems, 連れてくれば). Also fixes 来る's conditional reading (くれば, not きれば). Validated corpus-wide: every generated surface round-trips through Sudachi (dictionary/reading-form match, ~560k rows) and the old-vs-new diff is limited to the intended additions (853 entries gain tables, 75 ある-family entries lose the invented cells, 御座る is the one deliberate removal). `chunks.json` was rebuilt and the local collection refreshed payload-only (`--update --reuse-vectors`, 931 upserts; 1 drifted embed re-embedded) — production needs the data ingested into the Qdrant collection (snapshot push or a hosted re-ingest) before the new tables appear there
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
