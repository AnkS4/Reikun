# Plan — backlog

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

The implemented items originally tracked here (exact-match `gloss_keys`,
commonness/canonical priors, routing, embed-text slimming, prefetch pool,
ja compound segmentation, the EDRDG-XML migration, the Hit@1 ranking work)
have been folded into the as-built record in `Architecture.md`. The
data-source catalog and pipeline reference material moved to `Issues.md`
(*Data-source reference & follow-ups*); what remains is the TODO backlog.

## TODOs

Bracketed tags mark status/priority — `[RESEARCH]` needs investigation,
`[DECIDE]` needs a call, `[PENDING]`/`[OPTIONAL]`/`[CONSIDER]`/`[LATER]`/
`[FUTURE]` are priority hints; untagged bullets are plain TODOs.

### Branding
- Try to simplify the title either keep the Japanese one or English one instead of full: Reikun (例訓)
- [LATER] Add About page

### Improvements
- [DONE — runtime, 2026-10-21] Python 3.14: `.python-version` → 3.14, `requires-python = ">=3.14"`, ruff `py314`, Dockerfile base `python:3.14-slim-trixie`, CI 3.14; lock re-resolved clean on 3.14.8 (all wheels available), 102 tests pass on the new interpreter (warm suite 1.89 s — same as 3.13; cold first-run overhead was venv bytecode compilation). Free runtime wins, no code changes: PEP 649 deferred annotations trim import cost, and the new tail-call interpreter speeds API-bound loops.
- [DONE — UI, 2026-10-21] Compact search-row alignment: the wrapped utility strip (shuffle / あ / JLPT) keeps the row's standard gap and right-aligns as a group — `margin-left: auto` now sits only on the first utility button (`.search-row > .btn-3d:not(.furi-toggle)`); putting it on every button split the free space between them and left a hole between shuffle and あ.
- [DONE — ranking, 2026-10-21] Search ranking misses: the reported queries (tomato/garlic/eraser/じてんしゃ/potato/apartment/家族) went into `eval/gold_set.tsv` for regression, then two formula changes fixed the underlying causes with NO re-ingest (payloads already carry `wf_score`/`commonness`):
  1. **Canonical gate** — `CANONICAL_BOOST × wf_score × first-sense × (0.7 + 0.3·commonness)`: the corpus Zipf estimate is polluted for untagged kanji spellings the wordfreq lexicon barely knows (字消し 3.43 edged out the everyday 消しゴム 3.35 by 0.02 — the eraser bug; に文字「garlic」4.02 out of a particle's frequency — the garlic bug). An untagged entry keeps 70% of its wf_score. eraser → 消しゴム ✓, garlic → 大蒜 ✓, tomato/potato/dog/train/to-eat all unchanged; eval Hit@1 139/156 → 139/156 with the two gold set additions.
  2. **Formula layer on the ja route** — BM25-RRF was frequency-blind, so shared kana queries surfaced rare homographs (じてんしゃ → 次点者 over 自転車). The ja arm now runs the same FormulaQuery (commonness + canonical rule) on the fused pool: じてんしゃ → 自転車 ✓, and the whole ja_hiragana subset re-ordered itself the right way (せんせい→先生, びょういん→病院, こん? …).
  Remaining: 'apartment' — アパート's first sense is glossed only with 2-word phrases ("apartment building") so bare `apartment` missed the canonical boost while マンション (one-word gloss) got it; fixed ingest-side by indexing phrase head-words (`_gloss_head_words` in build_chunks: "apartment building" → also "apartment"), live after the next re-ingest. 'family/money/happy' misses are the known diluted-entry pattern (a minor sense of a frequent kanji entry beats the dedicated word) — unchanged, tracked in Issues.md S7.
- [DONE — ops, 2026-10-21] Much-faster re-ingest (`--update --reuse-vectors` in `scripts/ingest.py`): a payload-only refresh — scrolls the live dense/BM25 vectors back onto rebuilt points when the embed inputs verify as unchanged, re-embedding only true drift. The 0.8.0 field changes (conjugation tables, gloss head-words) don't touch anything the vectors encode (`text`/`meanings`/forms), so the ~1 hr re-embed became minutes. A Cloud snapshot was evaluated and rejected: snapshots transport existing vectors between instances, and these vectors only live on the Cloud cluster — snapshotting locally would mean embedding everything first. Future runs: points ingested by the current builder carry `inflected_forms` and must pass the strict payload recomposition, so form-sensitive drift still re-embeds; pre-0.8.0 payloads (older list shape) are accepted on the dense + display-text evidence — a 43-point wire test (random corpus sample + the report words) re-encoded `sparse_text` and matched the stored vectors exactly (43/43 index sets).
- [PENDING] Explain-side follow-ups (hooks already exist in `grammar_explain.py`):
  - Per-IP rate limit on /explain + /explain/stream — the only public endpoints that spend quota.
  - eval --llm: add objective format checks (bullets ≤ max, words/bullet cap, `**pattern** (fragment)` shape, no JA-only prose) + a confusion-pair regression set (ことになる vs ことにする, ので vs から, passive vs causative-passive, progressive vs resultative ている).
- [CONSIDER] Tag patterns with JLPT level — rejected in the prompt rewrite (LLM-assigned levels are confidently wrong); if wanted, inject levels from a vetted list via `hint`.
- [NO] Add ability to search from romaji (English writing of Japanese words) like 'kami' (かみ), 'mizu' (みず/水), etc. — **decided NO (2026-10-21)**: users who can type Japanese (IME) already get kana/kanji search; users who can't are better served by learning the IME than by a romaji layer whose Hepburn edge cases (long vowels, ん → n/m, gemination) would add a confusable rewrite that fires on *every* English query. The kana→dictionary path all exists today (type みず).
  Original plan, kept for reference: small romaji→kana converter (syllable table + Hepburn variants/long vowels) generating candidate kana, validated against `headword_index()`; rewrite to kana inside `rewrite_query()` so the `ja` route handles it.
  Disambiguation: keep Latin query English when it exact-matches a `gloss_keys` gloss (sake→酒, name→名前 still work); only reroute to kana when it doesn't (kami→かみ). Needs a gloss-key set — extend the `headword_index()` scroll.
- [LATER] Use non-incorporated data from JMDict & kanjidic2 further improve and adding extra details
  - `nanori` — name-only readings (太 → おお/たか/ひろ; most kanji have none). Impl: `rm.findall("nanori")` in `build_kanji_table()` → third row in `_readings_section()`.
  - `radical` — Kangxi radical no. 1–214 (太 → 37 = 大). Impl: parse `radical/rad_value[@rad_type='classical']`, map via embedded 214-entry table → meta badge.
  - `freq` — newspaper-survey rank, only top ~2,501 ranked (太 → #552); absent = rare. Already handled by omission (no badge, excluded from shuffle pool) — nothing to do.
- [LATER] [FUTURE] Proper-name entries via ENAMDICT/JMnedict (人名・地名・作品名 — the named-entity data JMdict deliberately omits). If adopted, also swap `sudachidict-small` → `sudachidict-full`: full adds the same named-entity coverage, so names would both *segment* correctly and *gloss* via the new index. Pointless today — full's extra entities have no JMdict entry to display.
- [LATER] 音訓 reading-based kanji search — "find the kanji (or its words) by ANY of its readings": type おこす → 興す, おこる → 興る/起床… Current state: readings are only *displayed* back (kanji card shows 音/訓 chips); searching them hits the headword index only when a word with that reading exists. Impl plan:
  - Build a reading→literal index from `kanji_table.json`'s on_yomi/kun_yomi (preprocess okurigana dots `た.べる` → stem `た`) into a small marisa or a static JSON sidecar at build time — same repo, no Qdrant change.
  - New route `/kanji/by-reading?reading=&n=` (declared before `/kanji/{char}`), new chips row on kanji cards, or interleave group results into the regular search reading… Decide UI later.
  - Ranking: freq first; group same-reading homographs (こう → 光/校/行) by JLPT then freq; badge the 音/訓 origin per hit.
- [LATER] Localization of UI chrome — translate the SPA's static labels (nav, buttons, empty states, about page) to non-English UI languages (likely candidates: Japanese first, then es/fr/de…). `$lib/i18n` with tiny per-locale JSON + a persisted locale switch next to the theme picker. NOT gloss/explanation content: JMdict glosses are English-authored data and grammar explanations prompt for English — translating those means multilingual data sources (wadokujt / jr-edict / CC-CEDICT listed in Issues.md) or a separate LLM prompt per target language. Do chrome-i18n first, content later.

### Streamlit → SvelteKit migration
Shipped: SvelteKit static on Cloudflare Workers (Vercel backup) → FastAPI on Cloud Run → Qdrant Cloud. Remaining cutover items:

#### Phase 3 — Hosting & cutover
- Test on real browsers (iOS Safari/Android)
  - iOS Safari specifics: `-webkit-backdrop-filter` on the frosted search bar, `<ruby>` rendering, `dvh` viewport units + safe-area insets, tap behaviour on hover tooltips (kanji dotted underlines — needs a tap-to-open path, not hover-only), stroke SVG animation, OLED theme contrast on OLED screens.
  - Android Chrome: same surface plus CJK Ext-B font coverage and dark-mode `theme-color` (#000000) in the address bar.
  - No-device options: BrowserStack free tier / LambdaTest; Playwright `webkit` emulation catches layout but not real-Safari quirks; borrowed iPhone for a 10-min pass is the cheap option.
- [DONE] Keep-alive for Qdrant: ONE hit to `/ready` every day — implemented as a `scheduled` cron handler (`web/worker.js`) on the existing `reikun` static-assets Worker (`web/wrangler.jsonc`: `main` + `triggers.crons: ["17 9 * * *"]` + `vars.API_URL`). Live via the git-connected CF build on next push. Details:
  - **Cron fix vs original plan** — `17 */48 * * *` is not valid cron (hours only cycle 0-23; a 48-hour step can't be expressed), so it's a daily ping: still far under the multi-day pause threshold and free everywhere (Workers Free allows cron triggers; one Cloud Run request/day is noise at min_instances=0; Qdrant free doesn't bill wake-ups). Do NOT escalate to a sub-day cron.
  - HTTP traffic never reaches the worker script (assets router + SPA fallback serve everything); no fetch handler is exported.
  - Optional alerting: `ALERT_WEBHOOK` secret (`wrangler secret put ALERT_WEBHOOK`) → non-2xx/unreachable /ready POSTs a status line; unset → console.error only. `observability.enabled` gives the logs (Workers/Failures tab).
  - The GH Actions alternative stays an option if CF crons ever need to go.
  - (Original warnings still stand: never a 5-min uptime monitor — Cloud Run min-instances billing.)
- [DONE] Cutover: `reikun.app` added as Worker custom domain — the switch is live. Remaining checklist below (verify, www, VM teardown window).
  - Prereq: `reikun.app`'s zone must be in this Cloudflare account (Worker custom domains need a CF zone). If the registrar still points at other nameservers: add the zone, swap NS at the registrar, wait for Active — do this well before cutover day.
  - Before switching: record the VM's A record + TTL (rollback needs the IP); drop TTL to ~5 min ahead of time; keep the VM serving for a few days after.
  - Gotcha hit during cutover: "Hostname already has externally managed DNS records" — CF auto-imports existing records into the zone at setup, so `reikun.app` still carries the A record → VM IP *inside CF* (deleting records at the registrar doesn't touch this; saw 3 imported A records sharing the VM IP — apex + www + another name). Fix: DNS → Records → confirm each IP == VM IP, delete apex A/AAAA/CNAME (and www's if attaching it), then attach. Leave MX/TXT/CAA and any mail-related names alone. Attach under the **Worker** (`reikun`, Settings → Domains & Routes), not a Pages project.
  - After: CF issues the cert automatically (minutes); verify HTTPS on apex (and `www` redirect if wanted — add a bulk redirect or a second custom domain); rollback = remove the custom domain binding and re-create the A record (DNS-only) at the noted IP.
  - VM teardown: do NOT stop docker/Caddy at cutover — resolvers caching the old A record keep hitting the VM until TTL expiry (some ignore it), so a stopped Caddy = connection refused for stragglers, and a live VM is the instant rollback target. It serves zero real traffic post-cutover anyway. After a few quiet days: `docker compose stop` (keeps containers + `qdrant_data`/`caddy_data` volumes — a frozen backup, restart is instant); `down -v` or VM deletion only after the managed stack proves out for weeks.
  - CORS already covers `reikun.app` + `*.workers.dev` — no API change needed.
  - CF AI bot controls (applied at zone onboarding): Search allowed (required — Search Console/sitemap indexing), non-ad Agents allowed (AI-answer engines citing the site = free referral channel), Training blocked (no upside). Edge-enforced, requests never reach origin. The SPA shell is thin crawlable content regardless — dictionary data sits behind runtime API calls bots don't make.
- Verify the site renders in Google's URL Inspection (Search Console); submit sitemap
  - [SKIPPED] Search Console verification — domain-property DNS step not completed (user declined the Cloudflare OAuth/manual TXT). Google indexing is now organic only; the stale Streamlit snippet stays until natural re-crawl. Revisit later if wanted — domain property covers all subdomains/protocols.
  - Current Google index is stale — still shows the old Streamlit snippet ("Streamlit reikun.app / You need to enable JavaScript to run this app"). The new site already ships proper `<title>` + meta description; URL Inspection → Request Indexing forces the re-crawl that replaces it.
  - [DONE] CF **Crawler Hints** enabled — auto-pings IndexNow on content changes (Bing, Yandex, Naver, Seznam; DuckDuckGo/Ecosia ride on Bing's index). Covers the non-Google indexing channels without a Bing WMT account.
  - `robots.txt` + `sitemap.xml` added to `web/static/`. robots.txt also declares the AI-training opt-out (GPTBot/ClaudeBot/CCBot/Google-Extended/Applebot-Extended/Meta/Bytespider `Disallow: /`) to match the CF edge block; search + non-ad agents stay allowed.
  - [DONE] `/about` page (`web/src/routes/about/`) — prerendered, linked from the footer license line, added to the sitemap.
  - [DONE] SSR is now global (`+layout.ts` `ssr = true` + `prerender`) — `/` prerenders real landing content (tagline/hero) instead of an empty shell, and every route bakes its own `<title>` + per-route canonical into the HTML (layout svelte:head via `page.url.pathname`). Removed the static `<title>` from app.html (it duplicated on `/about` — first tag wins for non-JS parsers) and the per-route `about/+page.ts` override. Only wrinkle: `page.url.searchParams` throws during prerender, so the `level` derived guards with `browser` (defaults N5 in HTML; hydration re-evaluates).
  - [DONE] app.html: canonical link (also dedupes `reikun.asatbhai.workers.dev`, which serves the same build), OG + Twitter card tags (og:image → `web/static/logo.png`, 512² — a 1200×630 card would unfurl better), WebApplication JSON-LD. Fixed a real gap: `+page.svelte` only emitted `<title>` after a committed search, so the landing shell had no title — now defaults to "Reikun (例訓) — Semantic Japanese Dictionary".
  - Note: opengraph.xyz's scanner is CF-blocked (asks to whitelist 74.220.48.0/24 + 74.220.56.0/24) — skipped; real unfurlers (Twitterbot/Slackbot/Discordbot/facebookexternalhit) all pass with 200, verified by UA curl.
  - [DONE] app.html: canonical link (also dedupes `reikun.asatbhai.workers.dev`, which serves the same build), OG + Twitter card tags (og:image → `web/static/logo.png`, 512² — a 1200×630 card would unfurl better), WebApplication JSON-LD. Fixed a real gap: `+page.svelte` only emitted `<title>` after a committed search, so the landing shell had no title — now defaults to "Reikun (例訓) — Semantic Japanese Dictionary".

#### Phase 4 — Remove dashboard, private stats
- [DONE] Cloudflare Web Analytics (2026-10-21): cookieless beacon wired into `+layout.svelte` — on app mount, if `PUBLIC_CF_ANALYTICS_TOKEN` (web build env, `web/src/env.ts`, optional, default '') is set, injects `https://static.cloudflareinsights.com/beacon.min.js` with `data-cf-beacon`. The beacon auto-tracks SPA route changes; the empty token means the branch is dead-code-eliminated at build. No CSP in web/ for it to collide with. **To activate:** CF dashboard → Web Analytics → add reikun.app → copy the token → set `PUBLIC_CF_ANALYTICS_TOKEN` in the CF Pages/Workers build env for web/ → rebuild. No consent banner needed (cookieless).
  - Zone-level extras (cache status, Web Vitals) are available once the site is verified in the same dashboard; no code change.
- [LATER] Structured logs; private /admin (token or Cloudflare Access) only if needed
  - Web Analytics: free, cookieless JS beacon — works on `workers.dev` today via snippet, gets zone-level extras (cache status, Web Vitals) once `reikun.app` is on CF. Answers the "did anyone come / from where" questions from the tracking section without cookies or a consent banner. (Implemented 2026-10-21 — see Phase 4 above.)
  - Structured logs: `TELEMETRY=stdout` already lands in Cloud Logging; add log-based metrics (searches/day, p95 latency, 5xx rate) + an email alert on "service is down"/error spike (Cloud Monitoring, free). Only add a BigQuery sink if SQL over events is actually needed — `gcloud logging read` covers ad-hoc queries.
  - Private stats/admin: cheapest is no UI — `gcloud logging` queries on demand. If a page is wanted: it's a static site, so /admin would be an API route — put Cloudflare Access (Zero Trust free ≤50 users, Google OTP) in front of it, or a FastAPI dep checking a shared-secret `Authorization` header. CF Access needs the api hostname on the CF zone — the `api.reikun.app` mapping was skipped, so Access would require reviving it; the shared-secret header works with run.app as-is.
  - Watch: don't let a stats page recreate the privacy surface the dashboard deletion removed — aggregate counts only, no raw queries on an admin page (raw text stays in Cloud Logging behind GCP IAM).

#### Phase 5 — Hardening
- [LATER] eval Hit@k in CI — needs Qdrant + models + secrets; stays a manual gate. Playwright smoke — needs a deployed URL + browser install; add post-cutover against reikun.app

##### Larger, riskier thinning
- Remove fastembed/ONNX entirely via Qdrant Cloud hosted inference, if the free cluster allows it. This is the biggest single saving but needs the research spike first.

### Research / later
- [RESEARCH] Qdrant Cloud hosted inference: if allowed on the free cluster, drop fastembed from the image; check limits first
  - **SPIKE RAN 2026-10-21 against the production free cluster — query AND insert inference both work:**
    - `cloud_inference=True` client + `models.Document(text=…, model=…)` in `query_points`: dense (`sentence-transformers/all-MiniLM-L6-v2`) ✓, sparse (`qdrant/bm25`) ✓, and *mixed dense+BM25 RRF fusion in one call* ✓ — fused call returned real `jmdict_chunks` points (愛犬), so the existing collection serves inference queries with **no re-ingest**.
    - Insert-side (throwaway `_inference_spike` collection, deleted after): upsert with `models.Document` in both named vectors ✓ (~0.3 s per small batch); stored dense vector 384 dims + bm25 sparse indices correct; roundtrip query ✓.
    - Model names MUST be fully qualified — bare `all-MiniLM-L6-v2` → 400 "Unsupported model".
    - Client-API note: `create_collection`/`SparseVectorParams` need keyword args (`modifier=`) in qdrant-client 1.19.
  - **How to proceed next** (if adopting): 1) flip `app/config.py`'s client factory to `cloud_inference=True` behind a `QDRANT_CLOUD_INFERENCE` env flag; 2) switch `embedder.embed_query()` dense+sparse arms to `models.Document`; 3) verify ranking parity first on a sample — compare local-fastembed vs cloud-embedded query vectors against the same points (same model; drift only if Qdrant's model version/tokenization differs); 4) benchmark /search latency (spike: 0.05–0.18 s/query on free cluster). Only *query-side* matters for the image: ingest scripts run on dev, so fastembed can leave the API container even if ingest keeps computing vectors locally. 5) Watch the free-tier request budget — 1 fused inference call per /search is small for a dictionary app's traffic.
  - If adopted: `embedder.py` embed_query → send `Document` text instead of vectors, image drops fastembed+ONNX (~90 MB models warm-layer, ~100-200 MB RSS, and the whole `[DEPLOY]` thread-pool capsule work) — biggest single container saving. Risk mostly retired by the spike; remaining unknowns are bulk-ingest throughput (irrelevant if ingest stays local) and the free-tier request budget.
- [RESEARCH] Dense search for word queries: test exact+BM25 vs hybrid; if equal, lazy-load the model only for sentences
- [LATER] Accounts, saved-word lists, PWA (service worker + manifest)
- [DONE — 2026-10-21] Ranking: wf_score IS stored in the trie (`add_entry` carries `wf`, `PAYLOAD_FIELDS` updated, trie rebuilt 27→30 MB) and `_ambiguous()` orders contested candidates by (is_common, wf) instead of ingest order — Issues.md S2's "still left" closes. Verb inflection index DONE — see Verb option (a) below. Known ranking misses fixed — see Improvements above.
- [LATER] Rate-limit and cap /explain (slowapi, length cap), cache by (sentence, level), friendly 429 handling
- [DONE] 2026-10-21 Add a toggle to turn off furigana — persisted `reikun-furigana` localStorage flag (`src/lib/furigana.svelte.ts`, safeStorage-guarded) read inside `Ruby.svelte`, so results, examples, segment chips and kanji-card word rows all obey one switch; the visible あ button in the search row is the single control (the Appearance popover copy from 0.7.0 was removed same-day per user feedback — two controls for one preference). Default on, server-safe (prerender paints with readings, hydration re-evaluates).
- [DONE] 2026-10-21 Number×counter reading table (S3 fix): `retrieval._counter_reading` table + composed -3/-4 rule for 日, fused chips get the right reading (2日→ふつか, 20日→はつか, 1人→ひとり…) and untabled combos keep no furigana; plus `_counter_alias` — digit-typed counter searches (25日, 1人, 4時) rewrite to their kanji-spelled headword (二十五日/一人/四時) when that's a real entry, so bare digit queries land the actual card. Details + test coverage in `Issues.md` S3; CHANGELOG 0.7.0.
- [LATER] Mirror ingest inputs in Cloudflare R2 — JMdict raw (100M), ONNX models (1.7G), `data/processed` (222M), `data/kanjivg` (41M). Makes rebuilds reproducible and independent of ftp.edrdg.org / HF Hub uptime; useful for CI and disaster recovery. Zero egress, free tier covers it.
- [RESEARCH] Improve the ranking as there are issues with following words not having expected word at the top sometimes even being the common word:
  (家族, 2nd entry), apartment (アパート, 4th entry), ...
- When docker is run it could query the example pills from search as health check and cache the results from these example pills.
- [DEPLOY — before moving off the 4-CPU host] Cap ONNX thread pools for the free tier (0.1 CPU, 512MB): onnxruntime sizes `intra_op_num_threads` from *host* cores, so on a shared host it spawns dozens of threads fighting the fraction-of-a-core quota — slower than 1 thread. Fix: `threads=1` on `TextEmbedding`/`SparseTextEmbedding` in `app/embedder.py` (`dense_model()`/`sparse_model()`), plus env `OMP_NUM_THREADS=1`, `TOKENIZERS_PARALLELISM=false`. Done already for RAM: `sudachidict-small` (~110MB vs ~200MB) and the marisa-trie headword index (~5MB RSS vs ~340MB dict) — remaining budget is just ONNX sessions ~100–200MB (Streamlit's ~150MB went with Phase 4).

### Features

#### Text assistant
- Test the Japanese sentence parser on many examples — needs a broad pass before calling it done.
  - Verified so far: 日本は中国の東に位置しています, 昨日すき焼き/精進料理/寿司を食べました, 明日かっぱ巻きを食べたいです (ambiguous surface joins a compound — かっぱ+巻き → かっぱ巻き resolves it contextually; ambiguous summary glosses now follow index order, not alphabetical), 読んでしまった, 食べて寝た (connector て unmerged), 山、川に行った (punctuation boundary), 白鳥→はくちょう, 電気自動車 (rescue chain), 飲み物/書き方/卵焼き/車椅子/万年筆/悪人/朝食/三人 (compounds), 静かな場所 (形状詞+な tail).
  - Known limits to keep an eye on: same-reading homographs list all options rather than a single gloss (いる → 居る/射る/入る/要る…); proper names unresolvable since JMdict has none (山川さん-type merges are honest ambiguity, see the ENAMDICT item above); conjunctive-vs-case で now glosses "particle" vs "location / means" correctly.
  - Suggested corpus: the Tatoeba ja examples already ingested — the earlier 100-sentence analyzer benchmark sampled them deterministically; reuse that for a regression sweep covering conjugations, particles, compounds, mixed script, punctuation. Check both the chip row and the promoted-results cards.
  - [DECIDE] `MAX_JA_QUERY_CHARS` — raised to 100 (was 80). Measured cost of allowing longer ja input (warm process):
    - Sudachi tokenize: 0.2–0.4 ms even at 161 chars; full `segment_japanese` (parse + index lookups): ~15–35 ms — linear, negligible.
    - The real cost is the Qdrant sparse retrieve + sparse embed on the long query: ~50–230 ms — and for sentence-length input those hits are mostly noise anyway (a 102-char query returned 2 marginal results).
    - Corpus stats (31,974 Tatoeba ja sentences): median 19, p95 40, p99 55, max 103 — 80 already covers ~100% of real single sentences.
    - Raising to ~120 costs only the extra parse ms and would cover long multi-clause input like the 80/102-char examples above; past 150 also requires bumping `MAX_QUERY_CHARS` (raw guard fires first — it bounds English embed/DB cost too).
    - Alternative worth considering: for ja queries over ~N chars, skip the Qdrant retrieve entirely and just return the parse — saves the 50–200 ms and the noise results.
    - Refs: Kanshudo avg ~18 chars/sentence; modern web text ~30–40; specialist/formal prose up to ~76; readability guidance says >60–80 "readers feel it".

#### Verb
- [DONE] 2026-10-21: the Sentence Breakdown now ships the stem's committed dictionary entry (`_stem`) and — when a ja query has no real hits — the *promoted result cards* show the ROOT entry (走った → card 走る【はしる】 + common badge + examples) instead of a pseudo-entry for the conjugated surface. The chip keeps the inflected surface; the tooltip options already name the root per morpheme. Verified across 走った/食べました/行かなかった/泳げます/読んでしまった/高かった/書かれた/急かされた (tests/test_segmentation.py). The remaining "could be an inflection of X" info bar landed same day — plan option (a) below.
- When word 走った is searched it displays a info bar: "走った could be an inflection of 走る, with these forms: Ta-form. It indicates the past tense of the verb." And, then it searches for 走る
  Research (2026-09): no EDRDG file ships an inflected→lemma index — checked the whole `nihongo` archive; `term_aggregates.zip` ("fully inflected forms") is just `freq\tsurface\tPOS`, no lemma column. The usable assets:
  - **`pos` tags** — already inside `data/raw/JMdict_e_NG_examp.xml` (74 verb/adj classes: v5r, v1, vk, vs-i, adj-i, v5k-s 行く-class, adj-ix 良い-class); `build_chunks.py` currently drops them (never reads `sense/pos`). Highest-value piece — turns "guess the ending" into "know the conjugation class".
  - **`vconj`** — EDRDG's own deinflection table inside `xjdic24.tgz` (ftp.edrdg.org): top-down `surface-suffix → dictionary-ending, label#` rules + English label table ("5 = plain, past"); powered xjdic's built-in de-inflection. GPL-licensed + EUC-JP + ~1998 coverage (no 〜ちゃう/〜とく) — transcribe grammar facts, don't vendor the file.
  - **`yamagoya/jconj`** (JMdictDB conjugation tables): `conjo.csv` ~34KB keyed by the same pos codes (rows `pos,conj,neg,fml,stem,okuri,euphr,euphk`) + `conj.csv` (conj# → English form names) + `kwpos.csv` — the tables behind JMdictDB's own conjugate page. No license file — verify with McGraw / jmdictdb GPL terms before vendoring.
  - Community deinflect tables (rikaichan `deinflect.dat` LGPL; Yomitan `deinflect.json` GPL-3 — ~150 rules as `kanaIn/kanaOut/rulesIn/rulesOut` + reason strings) — wwwjdic-lineage, not EDRDG; jisho's "could be an inflection of" banner runs on this data.
- [DONE — 2026-10-21, plan option (a) as recommended] The inflection index + conjugation table shipped as `app/conjugation.py` (hand-authored ~40-row suffix rules — Apache-2.0-clean, no vconj/jconj vendoring):
  - **Build side** `scripts/build_chunks.py`: parses `sense/pos` (one line), `conjugate(pos_texts, primary_kanji, primary_kana)` generates the paradigm rows — godan (9-ending chart), ichidan (potential/passive merged — one row one label), kuru double-stem (来ます/こない), suru (noun+する), i-adjectives incl. the いい→よく irregulars, 行く special class (行った, the one chart override). Payload gains `inflected_forms` (render rows {form, surface, kana}) + `infl_forms` (flat keyword strings); gloss keys gained phrase head-words (the apartment fix). Archaic nidan, aru-class and auxiliary-only entries generate nothing — a wrong row is worse than no row.
  - **Runtime** `app/retrieval.py`: one `MatchValue` infl arm in `_exact_filter` (gated on a once-per-process index-present probe so old data degrades gracefully instead of 400ing), `inflected_forms`/`inflection` (the row label the queried surface equals) into `_hit_to_dict`/`_auto_search` — "走った is the Past form of this word" is data, not heuristics.
  - **UI** `ResultCard.svelte`: a collapsible Conjugations table (form / surface / kana columns) + the inflection info bar when the search itself was an inflected form. Schema: `SearchResult.inflected_forms[InflectionRow] + inflection` — openapi regenerated.
  - Verified offline: 20 unit tests (`tests/test_conjugation.py`: 走る/急ぐ/死ぬ/見る/来る/勉強/する/楽しい/いい/かっこいい/行く + exclusions). Live data arrives with the re-ingest (payload-only — vectors re-embed per --update's content-sig diff).
  - Rejected alternative (kept for reference): b) runtime deinflect walker as its own module; not needed — option (a) already pins the base entry through the exact arm, and class-knowledge beats a class-blind walker. Historical research (2026-09) that fed the decision: no EDRDG file ships an inflected→lemma index (checked the whole `nihongo` archive; `term_aggregates.zip` "fully inflected forms" is just `freq\tsurface\tPOS`, no lemma column); the grammar facts came instead from transcribing standard conjugation rules, since the uploadable tables are all license-encumbered or stale (`vconj` GPL-2/EUC-JP/~1998 coverage; jconj has no license file; rikaichan LGPL, Yomitan GPL-3).

#### Clickable
- [DONE] 2026-10-21 (reworked same day per user feedback): kanji-card badges that name a group ("N strokes", "Grade X", "JLPT NX") are **links to a separate browse page**, showing kanji characters — not words (words were confusing) — with a "show next" pagination. Details:
  - `/kanji/group?by=strokes|grade|jlpt&value=&n=&offset=` returns the KANJI of the group (glyph, first meanings, readings, meta badges) as `(page, total)`; pool ordered by KANJIDIC2 freq (rank 1 first), cached whole (`_kanji_pool`), sliced per request.
  - New page `web/src/routes/kanji-group/+page.svelte` (`prerender = false`, served via the 200.html SPA fallback) reads `?by=&value=&page=`, renders a 48-up grid (glyph + gloss + meta line, each card a deep-link search) and Prev/Next pagination ("Page X of Y").
  - Badge carries `group` in the payload (`MetaBadgeGroup`); clicking opens `/kanji-group?by=&value=`. "Freq #N" stays a tooltip (not a group).
- Make the details in kanji clickable such as 'X strokes', 'Grade X', 'JLPT NX' to get words from that group

#### Related words
- [DONE] 2026-10-21: result cards render a "related words" row — words sharing a kanji with the headword, taken from the kanji table's ranked common-word pools (`render.related_words`, ≤8 per card, deduped vs the entry's own forms, first-gloss chips searchable via the commit path). Kana-only entries get none (hidden). Shipped in /search payloads (`SearchResult.related`) — no extra client round-trips; openapi + `openapi.d.ts` regenerated together.

#### Lists
- [DECIDE] Add user login — accounts backend options:
  - **Convex** — auth + DB + realtime sync in one hosted service; strongest fit for saved-word lists syncing across devices. Lives on the SvelteKit side (TS SDK + Convex Auth); FastAPI/Cloud Run untouched unless API-side writes are ever needed. Free tier covers hobby scale.
  - **Neon/Supabase Postgres + auth** (Clerk or Auth.js) — user data stays in SQL, but auth + CRUD endpoints have to be built on FastAPI/Cloud Run.
  - **Cloudflare-native** (Workers + D1 + JWT issuer) — closest to the existing frontend host, but the most glue code.
- Ability to save the words to list(s). Start with one list per user then probably more lists.
- Import/Export the word list
- Revise/review the list

#### Voice
- Add FOSS Model to process it locally at the search page

### Pre-mass customer reachout

#### Tracking users (minimal)
- Goal: answer three questions — did anyone come, from where, did they come back — without cookies/PII or a consent banner.
- Already logged (SQLite `reikun.db` via `feedback_log.py`): searches (query, mode, latency, result count), thumbs feedback, explanations, kanji lookups → covers "what do users do / do results satisfy".
  - **On Cloud Run `reikun.db` is ephemeral** — the container filesystem is discarded on every instance recycle/revision, so `TELEMETRY=sqlite` would silently lose data. Deployed posture is `TELEMETRY=stdout` (the default) → Cloud Logging, with a BigQuery sink if SQL querying is ever needed. Keep the sqlite sink for the self-hosted Docker path only; if a real DB is wanted later, reuse whichever accounts backend is chosen above rather than mounting a bucket (GCS FUSE lacks the locking semantics SQLite needs).
- To add (minimal):
  - **UTM/referrer on the landing link** — `?utm_source=dev.to`, `?utm_source=showhn`, etc. on each post's URL; log it once per session (the page already reads `page.url.searchParams` for `q`/`level`). Tells which channel works — the whole point before scaling outreach.
  - **Anonymous new/returning flag** — random ID in localStorage, sent with searches or as its own telemetry event; log `new` vs `returning`. No cookies → no banner; gives a retention proxy for the AARRR "keep before monetize" gate.
  - **Activation proxy** — "used ≥2 features in a session" (search + explain / kanji card / sentence parse), derivable from existing logs keyed by that session ID.
  - **Guardrails**: never log IPs/raw UA; verbatim queries already sit in `reikun.db` + Cloud Logging — see the legal-pass item below *before* outreach, since real strangers' input will land there.
- Alternative: skip building any of it — GoatCounter (free for OSS) or self-hosted Umami: one script tag, no cookies, offloads visitor/referrer counting entirely.
- **[LATER] Pre-commercialization legal pass** — before any monetization/paid feature: write a real privacy policy (what's logged: raw search queries + feedback + explanation sentences; where: Cloud Logging + SQLite; why: quality tuning), re-add a retention setting or scheduled purge (telemetry currently keeps rows forever — deliberate for the solo-debug phase, not the launch posture), and run the GDPR/AEPD checklist (ES/EU: lawfulness basis, minimisation, access/deletion handling) plus other jurisdictions' equivalents if targeting non-EU users.

### Marketing/Advertisement (COST FREE)

#### Audience profile
- Target audience: English-speaking Japanese learners — beginners (N5-ish: kanji lookup, stroke order, first searches) through intermediate readers (sentence breakdown, JLPT-tuned grammar). Built for the "reading along, hit a sentence I can't parse" moment; secondary overlap with the OSS/dev crowd who like self-hostable tools.
- Platforms/communities by fit:
  - **Learner communities** (highest fit) — WaniKani forums, Bunpro/JPDB forums, EJLX + other Japanese-learning Discords (`#resources`/`#self-promo` channels); Reddit: r/LearnJapaneseNovice, r/JLPT, r/visualnovels. r/LearnJapanese is big but strict on self-promo — comment-first, answer questions with a breakdown link.
  - **Study social** — #langtwt / #studytwt on X, Bluesky/Mastodon learner clusters; tool posts get reshared.
  - **Video feeds** — TikTok / YouTube Shorts / Instagram Reels, using the portrait clip (see *Content editing & details*).
  - **Dev/launch** — Show HN + dev.to writeup (chosen first posts), Product Hunt / Indie Hackers if those land.
  - [CONSIDER] **Directories** — awesome-japanese / awesome-japanese-learning lists, AlternativeTo, curated resource pages (learnjapanese.moe et al.): one-time effort, permanent placement.
- Etiquette: LinkedIn covers credibility, not learners — the audience lives in the communities above. Become a regular before linking (helpful answers first, tool second); "built it for my own study" framing reads genuine, not promotional.

#### Content editing & details
- Edit pass on the cropped video — labels/captions + sound:
  - **Tool**: CapCut (free, auto-captions) is the fastest path; DaVinci Resolve if more control needed. ffmpeg-only alternative stays in-repo: `drawtext` for step labels, `amix`/`-i music.mp3 -shortest` for audio — scriptable but captions are manual.
  - **Beats to label**: hook text in the first 1–2 s ("Can't parse this Japanese sentence?"), one short label per step (search → grammar → kanji card → sentence breakdown), end card with the URL.
  - **Safe zones**: keep text out of the bottom ~15% (platform UI covers it) and clear of the right edge (TikTok's action rail).
  - **Sound**: royalty-free track (YouTube Audio Library / TikTok commercial sounds) at low volume — the clip has no voiceover so nothing competes with it.
  - **Length**: ~23 s source is already under every platform's limit — no further trimming needed.

#### Posts
- One dev.to post and one HN (Show HN) post — the chosen channels for now
- [CONSIDER] Submit to awesome lists (awesome-japanese / awesome-japanese-learning) and AlternativeTo

- [DONE — verified, 2026-10-21] Compact search-row spacing verified in a live browser at 412px (narrow-viewport iframe — media queries bind to real viewport width): flex gaps between shuffle / あ / JLPT measure exactly [8px, 8px] (the row's standard gap), `margin-left:auto` resolved on the first utility button only (176px) with 0 on the other two, and the strip is flush-right (row-right − last-right = 0), `wrap` branch engaged.

