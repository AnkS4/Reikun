# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Privacy policy page**: a dedicated `/privacy` page on the full site and a mirrored `/lite/privacy` page, both English-only (legal text is not localised, like the footer) and linked from both footers, both About pages and the sitemap. The policy states what the service never collects (no cookies, no accounts, no IP/user-agent logging), what it records to improve the dictionary (search queries verbatim, feedback and explanation text as one-way hashes), what stays in the browser (recent searches, interface language), what reaches the third-party LLM provider when explanations or descriptive rewrites are requested, and how long data is kept.
- **Telemetry retention**: self-hosted SQLite telemetry gains a purge for rows older than `TELEMETRY_RETENTION_DAYS` — off by default (rows are kept forever: dictionary queries and hashed feedback are low-sensitivity data), and setting the variable to a positive number purges rows past that window once at sink init, then daily on a daemon thread. The purge reuses the sink's own connection and compares ISO-8601 `ts` strings lexicographically, so it costs no extra index and can never deadlock a first write. The stdout sink keeps nothing locally; server-log retention is the platform's (Cloud Logging's default is 30 days).
- **App version shown on the website**: the About page of both variants now displays the release version. The SvelteKit page reads it from a build-time `__APP_VERSION__` global (Vite `define` from `web/package.json`, kept equal to `pyproject.toml` by the release checklist) — inlined into the bundle, so rendering the version costs no API call and works offline. The lite About page server-renders `Reikun v{APP_VERSION}` under its Source section the same way. The API's `/health` response also gained a `version` field (`APP_VERSION`) as ops metadata for API consumers; the OpenAPI schema and `openapi.d.ts` mirrors were regenerated for it.

### Changed
- **Lite's top-right controls render without SVG**: hardened browser profiles (Tor Browser / LibreWolf "Safest") set `svg.disabled=true`, which blanks inline SVG too — so the icon cluster vanished exactly for the no-JS visitors lite serves. The full-version switch, theme toggle and language switch are now plain text labels ("Full", "Light"/"Dark", the SPA's 文A pair) and the dictionary status is a CSS-drawn dot; same 2rem round buttons, colors and tooltips. Both About pages and both footers keep their copy; the kanji stroke diagrams remain SVG (inherent to KanjiVG).
- **Lite's search row right-aligns every wrapped line**: the buttons previously right-aligned only via an auto margin on the first button inside the ≤680px media query, so any wrapped line that didn't start with Search sat at the left edge — on mid widths Random kanji/Furigana dropped to a left-aligned line, and with Android's larger font scales Furigana stranded alone. `justify-content: flex-end` on the form right-aligns every line; the input's flex-grow keeps full lines unchanged, so desktop is pixel-identical.
- **About page privacy section condensed**: the two-paragraph copy shrank to a two-sentence summary with a link to the new full privacy policy (`/privacy`), and the LLM-provider paragraph moved to that page, so the About page stays a short overview with the detail one click away.

## [1.2.0] - 2026-11-11

Lite-depth release: the lite UI becomes a first-class citizen — served from the same origin as the SPA behind the reikun.app Worker so the shared theme/language/recents cookies finally sync in production, shipped as one small HTML document plus an immutable hashed stylesheet with system fonts only, mirroring the SPA's design system and fully bilingual chrome. Random-kanji picks now land in Recent searches on both variants, and CI actions are pinned to immutable SHAs.

### Added
- **One origin for everything in production**: the reikun.app Cloudflare Worker now reverse-proxies the API (`/api/*`, prefix stripped — the SPA bakes `PUBLIC_API_BASE=/api`) and the lite UI (`/lite*`) to Cloud Run instead of the SPA calling run.app cross-origin. Serving both variants from `reikun.app` is what makes the shared cookies actually work in the cloud deployment: the theme choice and recent searches now follow a visitor across variants on the web too, and lite's full-version switch points at the same site rather than redirecting to a different domain. The Worker passes 303 cookie-setting redirects through untouched (`redirect: manual` — following them would swallow the `Set-Cookie`), and it signs the real client IP (`X-Reikun-Client` + a shared `PROXY_IDENTITY_TOKEN` secret) that the API's rate limiter trusts ahead of `X-Forwarded-For`, because behind the proxy the XFF chain ends with one Cloudflare egress address shared by every visitor.
- **Lite now says what it is**: a small "Lite mode" note under the hero tagline links to a new "Lite vs full" section on the About page, so switching variants is not a silent downgrade — the page states up front that Lite is static (no animations, no interactive popovers) and lists what the full version adds.
- **Dictionary status and language switch in the lite UI**: the top-right cluster now mirrors the full version's order — variant switch, status, theme, language. The status chip is a minimal pill (a coloured dot plus "Ready"/"Offline") with the live entry count on its native title tooltip — no hover popup, since Lite has no popovers. It is rendered from the last known snapshot, so a page view never waits on Qdrant; the probe (2 s timeout) runs as a background task after the response and refreshes the snapshot at most once a minute. Pages that would report offline are not shared-cached. The language switch shows the target language's own name (日本語 / English) and flips the shared `lite_lang` cookie via `/lite/lang`, which the SPA mirrors in its locale store (`web/src/lib/i18n.svelte.ts`) so one choice follows you across both variants. Lite chrome is now fully bilingual (en/ja), reusing the SPA's message values where the label matches; the about page and the footer stay English by design (legal/credit lines are not localised).

### Changed
- Lite's ETag/304 handling moved from an app-wide HTTP middleware into the lite router's route class: it hashes the finished HTML string instead of re-reading the response stream, and the JSON API and the SSE stream no longer pass through it (about 0.7 ms less per API request in local measurement). 304s now also carry `Cache-Control`.
- **Lite is now a static page, not a styled document**: the stylesheet moved out of the HTML into `app/static/lite.css`, served from `/lite/static/lite.css` with a content hash and `Cache-Control: public, max-age=31536000, immutable` — a page is one small HTML string (≈4.6 KB) plus one request the browser keeps forever. The palette moved into that file too (light tokens by default, dark on a dark OS preference or an explicit `data-theme="dark"` on `<html>`), so the theme is no longer a per-request inline `<style>` block. The CSS is minified at import (23 KB source → 20 KB, 4.6 KB gzipped) and every `color-mix()` was replaced with a static token, which is both cheaper to compute and works in older browsers. Lite's HTML also gained `ETag`/`304` handling: an unchanged page revalidates to a 304 instead of a full body.
- **Lite furigana/theme/language toggles no longer corrupt the query**: `_current_path` no longer re-encoded an already-encoded URL through `urlencode` (which turned a literal `+` into `%2B` and then back into a literal `+` in the search box); those redirects now build their `next` parameter with `quote(..., safe='')` and round-trip the original URL verbatim.
- **Lite drops webfonts entirely**: system font stacks only (`system-ui` for Latin, the OS's Japanese gothic faces for Japanese) — zero font requests, zero external connections, first paint on the first packet. Sizes and spacing are unchanged, so the layout still matches the SPA.
- Lite's chrome strings moved to `app/lite/i18n.py` and the asset helpers to `app/lite/assets.py`, so `app/lite.py` is a package (`app/lite/`) rather than one long module.
- Lite's body column is now 60rem (960px) on all viewports (was 50rem below 1024px), matching the SPA's main container, so the kanji card, strokes page, conjugations, kanji-group and search form are as wide as the SPA's search panel on every screen size. Footer width follows the SPA's 50rem → 60rem responsive rule. Tagline max-width corrected to 38rem (was 42rem on large screens).
- Lite's top-right control cluster now matches the full version's metrics exactly (0.6rem top, 0.85rem right, 0.15rem gap, 2rem round buttons), so switching variants no longer shifts the chrome. The full-version switch now uses a `layout-dashboard` glyph (panel layout) instead of the open-in-new arrow, for a clearer "full interface" affordance. The SPA's about page now renders the same header, so its top-right controls stay visible like everywhere else.
- Lite's chrome now shares the SPA's design system: the same sizes, spacing and layout, warm-washi surface tokens and elevation steps, 12px search controls with the indigo primary Search button, pill/badge/reading-chip treatments, and result/seg/kanji cards with the SPA's radii, borders and shadows. Lite also follows the SPA's responsive 50rem→60rem column and 680px breakpoint, and its conjugation / about / kanji-group pages use the same 42rem / 38rem / 60rem measures, mono stats line, pager label, faint metadata tone, example-row layout, conjugation chip and button backs. The kanji-group list also lost its browser bullets, and its card anchor now stacks glyph/gloss/meta like the SPA card. The home-page tip paragraph and the unused `level=N5` hidden input were removed (neither exists in the SPA), and the Random kanji button now draws from the whole kanji table instead of the N5 subset.
- Lite search is AI/LLM-free by construction: the query rewriter is pinned to `heuristic` regardless of the deployment's `QUERY_REWRITE`, so a Lite session never calls the LLM (conjugation lookups already used `rewrite_mode="off"`).
- Variant switching is now context-aware: clicking the full-version switch in Lite (or the lite switch in the SPA) lands on the equivalent page in the other variant instead of always the home page — kanji, search, conjugations, kanji-group, about (SPA) and home/search are all mapped, with query strings preserved.
- Lite's kanji page now carries a search row (with the Furigana toggle in it) at the top, matching the SPA's panel layout, and the redundant Furigana link that used to sit below the kanji card was removed. The back link now threads its predecessor's context (`from` + `chain`) so "← Back" walks the full chain of visited kanjis instead of skipping to the search page.
- Lite's Random kanji button now threads the originating page (`from` + `next`) into the kanji page, so "← Back" returns to the page the user was on (home, a search, or another kanji) instead of always showing "Back to search". The SPA's Random button now navigates directly to `/kanji/{char}` (showing only the kanji card, no search results/breakdown/info bar) for consistency and speed.
- The SPA's kanji-page back button now threads the current kanji as `from` when clicking Random, so the next kanji page's back button reads "← Back to {char}" (mirroring Lite's back-link threading) instead of a generic label. When no `from` context exists it still reads "← Back to search", matching Lite's fallback.
- The SPA's kanji page (`/kanji/{char}`) now carries the full sticky search row (search input, clear button, submit, random-kanji button with spinner, furigana toggle, and JLPT level popover) so the search panel stays visible and fixed when navigating to a kanji — including via the Random button — instead of disappearing. Matches the home page's search row exactly.
- The SPA's Random kanji button no longer dips 3px on press (`:active` `translateY(var(--lip))` removed via a `no-press` class) — the press animation on top of the search-row transition read as a page jitter. The spinner was also resized to match the 17px shuffle icon (was 1.1em) so the button doesn't resize while busy.
- Re-added `scrollbar-gutter: stable` on `html` (prevents the centered page content from shifting sideways when the scrollbar appears/disappears on search) and compensated the fixed chrome (`header-controls`, `floating-buttons`) with `margin-right: -15px` so they stay 14px / 24px from the viewport edge instead of gaining a phantom 15px gap. Verified: main content at left=153/right=168 on both home and results pages.
- The lite hero note and the About "Lite vs full" section were refreshed for accuracy: the note is localised (en/ja) like the rest of the lite chrome and now says Lite is the same dictionary served as plain pages, while the comparison names the concrete Full-only extras (hover kanji tips, stroke-order replay, JLPT grammar explanations, AI-assisted rewrite, feedback and sharing) and the search pipeline plus cookie sync both variants share.

### Fixed
- Lite kanji pages rendered with furigana hidden (`lite_furi=0`) were sent as `public`, so a shared cache that ignores `Vary: Cookie` could serve that copy to other visitors; they are `private` now, like pages with a pinned theme or Japanese chrome.
- The lite status icon now uses the full version's colours: the idle colour is the quieter faint tone, and in dark mode Ready/Offline use the OLED theme's green and red (the "common" badge follows the same green).
- The full version's lite switch now opens `/lite` on the same site when the API is reached through the same-origin proxy (`PUBLIC_API_BASE=/api`). It used to prefix the API base, which gave `/api/lite`, and a build with `/api` failed prerendering because the crawler followed `/api` and `/lite` links that only the Worker serves. Those proxy paths are now skipped during prerender, and every other broken link still fails the build. The API `preconnect` hint is emitted only for a cross-origin API.
- Random kanji picks now reach the homepage's Recent searches in both variants — the one lookup path that never did: the SPA's shuffle buttons (home and kanji page) call `pushRecent`, and lite's `/lite/kanji/random` redirect prepends the picked character to the shared `lite_recent` cookie the SPA reads.

### Security
- CI actions are pinned to immutable commit SHAs instead of mutable major tags, and `.github/dependabot.yml` keeps those pins (plus npm and uv dependencies) fresh via monthly update PRs — a compromised upstream action can no longer silently change what CI runs.
- The web preview image now runs as the unprivileged `node` user (uid 1000) instead of root, matching the backend image's `app` user; `vite preview` needed `node_modules` writable for its temp config bundle, so `/app` is chowned after the build.
- `TRUSTED_PROXY_HOPS` documentation now states that directly-exposed deployments must set it to `0` — with hops > 0 and no proxy in front, a caller-supplied `X-Forwarded-For` is trusted and can spoof the rate-limit identity.

- Versions: API 1.2.0 (pyproject + openapi), web 1.2.0

## [1.1.0] - 2026-11-08

Lite release: a JavaScript-free, server-rendered UI at `/lite` mirroring the full interface, with the theme choice and the recent-searches list shared across the two variants through cookies. Also lands the ty type gate on the backend pipeline, two search-surface fixes, in-range dependency updates, and a refreshed example-search set.

### Added
- **The `/lite` variant** (`app/lite.py`): a DuckDuckGo-Lite-style counterpart of the SvelteKit interface served by the FastAPI app — home (hero, example/recent pills, random-kanji button, furigana toggle), search with the full auto pipeline (single-kanji queries pin a compact two-column kanji card in the SPA's structure; sentences render a Sentence Breakdown card of word-over-gloss tiles), kanji card/group browse pages, verb conjugations and an about page. Plain f-string HTML with inline-Lucide SVG icons: every interaction is a link or a `GET` form, so it works with JavaScript disabled, in text browsers and on slow connections, and reuses the same retrieval/render layer the JSON API wraps (schema-hidden, so the HTTP surface is unchanged). Tests cover pages, cookies, toggles and error/empty-page chrome from committed data — no Qdrant or LLM required.
- **Variant switches both ways**: lite's top-right icon controls (theme sun/moon + "open full interface") take `WEB_BASE_URL` (docker-compose sets it; empty hides the switch for lite-only deployments), and the full version's header gains a matching feather icon button linking to the lite URL. Titles/aria-labels carry the meaning the icons substitute.
- **Cross-variant theme sync**: the shared `lite_theme` cookie is authoritative in both directions (cookies are not port-scoped), so switching the theme in either variant applies to both on the next load. lite's single dark maps onto the SPA's dark/oled flavour, preserving an existing dark/oled choice; system mode deletes the cookie so both ends follow the OS. The SPA's pre-paint inline script performs the same cookie-first resolution before first paint.
- **Cross-variant recent searches**: one shared `lite_recent` cookie holds both variants' recent-search pills (8 entries, 150 chars each, and a ~2.4KB percent-encoded budget under the browser's 4KB per-cookie cap on both writers). The SPA reads the cookie first and mirrors it to localStorage (kept as the fallback for blocked-cookie browsers); an absent cookie with local history seeds the shared list once, and an explicit empty list is the "cleared" tombstone every reader honours — a *deleted* cookie would read as "no shared state", resurrecting a lite-cleared list from the local fallback.

### Fixed
- The kanji card pulled the entry that *is* the kanji to the top of its common-word list after sorting only the first 8 pool entries, so on a frequent kanji the exact word could sit past the cut and be missing from the card entirely while a rarer compound took its slot (`app/render.py`); the whole frequency-ranked pool is scanned before cutting to 8.
- Cached search responses carried the cache key's normalized text in `rewrite.original` (lowercase, collapsed whitespace — not what the user typed; the rewritten `query`, the value the pipeline actually searched, was unaffected) (`app/retrieval.py`); cache-served responses re-stamp the user's exact input.
- Invalid integer env values (`QDRANT_TIMEOUT`, the rate limits) died at import time with a bare unattributed `ValueError`; `_env_int` names the offending variable and value (`app/config.py`).

### Changed
- The backend's type gate is now `ty` (Astral's checker, same toolchain as uv/ruff): pinned `ty==0.0.96` in the dev group, scoped to `app/` via `[tool.ty]`, and run by CI (`uv run ty check app`) after ruff and before pytest. The one real finding it exposed (dict invariance in `conjugation._V5_ROWS`) came with an accompanying behavior-neutral annotation sweep across `app/`, and `app/api.py`'s use-`assert` drift checks are explicit `RuntimeError`s now so optimized (`-O`) deploys keep the gate. The marisa-trie unresolved import (upstream ships no stubs) is the only allowed suppression.
- In-range dependency updates: `openai` 3.42.0 → 3.46.0, `pydantic` 2.14.2 → 2.14.3, `fastapi` 0.162.0 → 0.162.2. As a side effect of the pydantic update's Pydantic v2 idiom (a `default_factory` instead of a shared default instance), the `SearchResponse.meta` schema field drops its stale inline default and is properly optional.
- The footer is intentionally English-only: copyright, license and the EDRDG/Tatoeba/KanjiVG attributions are legal/credit lines and left the i18n dictionaries, rendered verbatim by both the full version's footer component and lite's.
- Example-search pills are refreshed to a shared seven-query set, identical in both variants and strictly alternating Japanese/English (single kanji, English noun, kanji+okurigana verb, English infinitive, two-kanji compound, natural-language question, Japanese sentence) — `app/lite.py`'s `_EXAMPLES` and the web app's `EXAMPLES` cross-reference each other.

- Versions: API 1.1.0 (pyproject + openapi), web 1.1.0

## [1.0.3] - 2026-11-01

Hardening release: two critical backend fixes (search error path, rate-limit identity), the SvelteKit stale-response/hover-cache fixes, a second bug sweep's findings (recovery-ingest indexing, wheel-safe version read, bounded request bodies, CORS wildcard guard, SSE reader release), and in-range web dependency patches.

### Fixed
- `/search` error handling actually worked again: the endpoint's `log: bool` query parameter (`app/api.py`) shadowed the module logger, so the `except` branch around retrieval called `log.exception(...)` on a boolean — every search failure died with `AttributeError: 'bool' object has no attribute 'exception'` inside the handler, surfacing as a raw 500 instead of the intended clean 502 and losing the full traceback to logs. The module-level logger variable is renamed to `logger`; the public API (`?log=`) is unchanged.
- The rate limiter can no longer be sidestepped with a forged short `X-Forwarded-For`: `client_ip()` (`app/ratelimit.py`) fell back to the header's leftmost entry when it held fewer addresses than `trusted_hops` — the leftmost entry is client-supplied and spoofable, so one header (`X-Forwarded-For: 1.2.3.4`) rotated per request defeated per-client limits entirely (each forged address got a fresh bucket). An incomplete header is now trusted not at all and the socket peer keys the bucket, which is what the module docstring always claimed ("entries further left are client-supplied and spoofable, so they are ignored"); the existing rightmost-entry behavior for fully-populated headers is unchanged, and a regression test covers the shortfall case.
- Stale-response races on two SvelteKit pages (`web/src/routes/`): the conjugations fallback fetch and the kanji-group pagination fetch both adopted the `.then()` result unconditionally, so the *slowest* in-flight request won the render. On the conjugations page a quick word change could show the previous word's table under the new word's heading (a metric card spoof, not a crash), and on kanji-group a fast Next/Prev could land page N's grid under page N+1's controls; the loser's `.finally` also cleared the other request's spinner in both. Both fetch effects now capture a `dropped` flag flipped by the `$effect` cleanup (runs before each re-run), so out-of-order responses and the stray busy-flags are ignored — the same guard the homepage already applies with its `reqSeq` counter and the kanji card with its `char === c` check, now consistent across every fetching page.
- Failed kanji hover batches no longer poison the cache: `flush()` (`web/src/lib/hover.svelte.ts`) cached `null` for every char of a failed `/kanji` batch call, and `wantKanji`'s `hovers.has(c)` check honored it permanently — one dropped request (e.g. server hiccup) left *all* tips on the session's pages as plain text until reload. Failures now clear the keys instead, so a later re-render (back navigation, new search re-using the chars) retries the lookup; the per-microtask batching still bounds it to one round-trip.
- `ingest.py --update` against a missing collection no longer leaves it unindexed: the update path falls into the fresh-collection branch (which creates with HNSW indexing off for bulk load) but the re-enable step only ran for a full ingest, so a recovery update — including the `startup.py` in-place refresh when the live collection has vanished — produced a fully populated collection that answered every search with a full scan. The re-enable now keys off "created fresh in this run" as well as "full ingest", with the comment's old "update mode touches a small delta" assumption corrected.
- `APP_VERSION` (`app/config.py`) no longer dies on non-editable installs: it read `pyproject.toml` unconditionally, which a wheel does not ship, so `import app.api` raised `FileNotFoundError` outside the repo/editable/Docker layouts. It still prefers `pyproject.toml` (one source of truth for the schema) and falls back to `importlib.metadata` distribution metadata, then `0.0.0`.
- Request bodies are bounded before parsing: `ExplainRequest` gained transport-level `maxLength` caps (8× the handler's whitespace-normalised 200/400-char limits, so whitespace-heavy input still reaches the real validator) and `FeedbackRequest.query` is capped at 512 chars — previously Starlette buffered and Pydantic parsed an arbitrarily large body before the handler-side caps could reject it, and `/feedback` stored whatever it was given.
- `/feedback` is rate-limited: it had no limiter while `/explain` and `/search` did, so the one endpoint that writes a telemetry row per call was also the uncapped one. New `RATE_LIMIT_FEEDBACK` env var (default 60/min, 0 disables) reuses `rate_limited`; the UI sends a handful per session, so the cap only catches scripted spam.
- CORS wildcard guard covers mixed lists: `allow_credentials` was disabled only for the exact singleton `["*"]`, so `CORS_ORIGINS="*,https://example.com"` enabled credentials with a wildcard present — an invalid combo Starlette resolves by echoing the request origin with credentials. The check now looks for `"*"` anywhere in the list.
- `/kanji/random`'s unchecked fallback sits inside its `try` (and logs a warning when the headword probe fails): a Qdrant outage used to escape through the trailing `return` and 500 instead of answering from the local table.
- The kanji-group page validates its URL params (`web/src/routes/kanji-group/+page.svelte`): a missing/non-numeric `value` or `page` used to be sent as `0`/`NaN`, 422 into the generic failure banner, and propagate into pagination links; the `$derived` descriptor now rejects them, so the page renders the dedicated "unknown group" notice and links stay well-formed.
- The SSE reader is released on failure (`web/src/lib/api.ts`): an error frame or mid-stream throw skipped `reader.cancel()`, leaving the connection to GC; the catch now cancels and the finally releases the lock (success path included).

### Changed
- Web dependency patches (`web/package.json`/lockfile): `@sveltejs/kit` 3.1.0 → 3.1.1, `@sveltejs/adapter-static` 4.0.0 → 4.0.1, `tslib` 2.8.1 → 2.9.1; all in-range, no behavior change. TypeScript stays at 6.0.3 — 7.0.2 (the native compiler) is out but both consumers pin `^6` (`@sveltejs/kit` peer-dependency and `svelte-check`, the latter breaking at `svelte-kit sync` / `npm run check` even before typechecking) and are already at their latest releases, so there is no TS7-compatible stack to move to yet.

- Versions: API 1.0.3 (pyproject + openapi), web 1.0.3

## [1.0.2] - 2026-10-30

### Changed
- Nebius models migrated to non-deprecated replacements: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` → `nvidia/Nemotron-3_5-Lightning` (default), `nvidia/nemotron-3-super-120b-a12b` → `nvidia/Nemotron-3.5-Super-VL` (fallback). This addresses the November 9, 2026 Token Factory Serverless model deprecation notice. The `extra_body` thinking-free configuration remains unchanged for the new models; both replacements were benchmarked on the 60-query descriptive suite under the current Japanese pivot (Lightning 56/60 Hit@1, Super-VL 55/60), and the retired IDs stay in the report for comparison. `.env.example`, `README.md`, `app/llm.py`, and `eval/reports/descriptive_models.{md,json}` follow.

- Versions: API 1.0.2 (pyproject + openapi), web 1.0.2

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
