# Architecture: Reikun (例訓) — Semantic Japanese Dictionary

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

This document details the complete step-by-step implementation of the project,
including initial builds and iterative refinements based on testing and user
feedback. It reflects the **current as-built architecture**: a static
SvelteKit SPA (`web/`) calling a standalone FastAPI service
(`uvicorn app.api:app`), which drives the retrieval/lookup/explanation
modules in-process. (The original Streamlit multipage app was removed
entirely in Phase 4 of the migration.)

---

## Project Structure

```
Reikun/
├── app/
│   ├── config.py            # Central env-driven configuration
│   ├── api.py               # FastAPI app — the serving entrypoint (/search, /kanji, /explain, /feedback, /health, /ready)
│   ├── render.py            # UI-agnostic JSON shaping (ruby parts, kanji card, chips, stroke data)
│   ├── telemetry.py         # Event logging interface (stdout JSON default, optional SQLite sink)
│   ├── retrieval.py         # Vector / BM25 / hybrid search, routing, ja sentence segmentation
│   ├── headword_index.py    # marisa-trie headword index (form → entries) for segmentation
│   ├── query_rewrite.py     # Heuristic + optional LLM query rewriting
│   ├── kanji_lookup.py      # Deterministic KANJIDIC2 + KanjiVG lookup
│   ├── grammar_explain.py   # Groq client (primary→fallback chain), JLPT-level-aware prompts
│   └── embedder.py          # FastEmbed dense/sparse model wrappers
├── web/                     # SvelteKit static frontend (adapter-static → web/build/)
│   ├── src/routes/          # /  (search SPA shell)
│   ├── src/lib/             # openapi-fetch client (typed from openapi.d.ts), kanji-hover cache, theme
│   ├── src/env.ts           # PUBLIC_API_BASE schema — build-time public env var
│   └── wrangler.jsonc       # static-assets deploy config (SPA fallback)
├── assets/                  # Brand assets (favicons, icons, images — svg/png)
│   ├── favicons/            # Favicon files (16/32/48 px, svg/png)
│   ├── icons/               # App icons (apple-touch, light/dark, circle variants)
│   └── images/              # OG images (og-image.png/svg for social sharing)
├── docs/
│   ├── api/                 # Committed openapi.json (frontend type generation; CI drift check)
│   ├── screenshots/         # UI captures (search, kanji card)
│   └── videos/              # Demo recording (gif + mp4)
├── eval/
│   ├── gold_set.tsv         # gold set — 360 queries, 60 per category (en_words/en_verbs/en_descriptive/ja_*)
│   ├── eval.py              # unified eval: headword bench + knob sweep (default), --report, --modes, --ir, --llm
│   ├── report_meta.py       # provenance stamp shared by every report writer
│   ├── embed_model_bench.py # dense embedding model benchmark
│   ├── reports/             # curated headline reports (committed) — README.md index, eval.md, headword_eval.*, retrieval_eval*, llm_eval.*
│   └── results/             # generated run outputs (gitignored)
├── scripts/
│   ├── download_edrdg.py    # Sync JMdict NG + KANJIDIC2 XML from EDRDG (rsync)
│   ├── download_kanjivg.py  # Download KanjiVG stroke-order SVGs (packs strokes.json)
│   ├── feedback_log.py      # SQLite telemetry sink (searches, feedback, kanji lookups, explanations)
│   ├── build_chunks.py      # Parse and chunk dictionary data
│   ├── ingest.py            # Embed (dense + sparse) and load into Qdrant
│   ├── cloud_ingest.py      # Snapshot-transfer a local collection to Qdrant Cloud
│   ├── export_openapi.py    # Write docs/api/openapi.json for frontend type generation
│   ├── startup.py           # Container entrypoint (execs uvicorn) + opt-in ingestion pipeline
│   └── sync-assets.sh       # Sync brand assets from assets/ to web/static/
├── CHANGELOG.md             # Version history following Keep a Changelog format
├── .env.example             # Environment variable template
├── data/
│   ├── raw/                 # Downloaded dictionary files
│   ├── processed/           # Parsed chunks, kanji table, packed stroke data (strokes.json)
│   ├── kanjivg/             # Stroke-order SVGs (build input only; not shipped)
│   └── monitoring/          # SQLite telemetry database
├── models/                  # Cached embedding models (local runs; Docker uses a named volume)
├── Dockerfile
├── docker-compose.yml
├── docker-compose.override.yml.example  # optional host-specific overrides (e.g. DNS)
├── pyproject.toml           # pinned deps + ingest/dev dep groups
└── uv.lock                  # locked resolution (uv sync --frozen)
```

---

## Architecture & Technology Decisions

1. **Frontend — SvelteKit static SPA** ([`web/`](../../web/)):
   - Built with `@sveltejs/adapter-static` into `web/build/` — served as
     pure static assets on Cloudflare Workers (`web/wrangler.jsonc`, SPA
     fallback via `not_found_handling: single-page-application`). The API
     base URL is baked in at build
     time via `PUBLIC_API_BASE` (`web/src/env.ts`).
   - The API is a **standalone** FastAPI app (`uvicorn app.api:app`,
     routes at the root) — what the container `CMD` runs (§3.5). The earlier
     Streamlit multipage UI (and before it, a combined Streamlit+`/api`
     mount) was removed in the Phase-1→4 migration; `app/render.py` is the
     UI-agnostic JSON layer that replaced it.
   - URL-driven state: `?q=` makes a search shareable and lets browser-back
     walk previous queries; the JLPT level lives in the segmented picker.
   - Styling is hand-rolled CSS in `web/src/app.css` (light/dark themes via
     a `data-theme` attribute + localStorage picker, Inter/Noto Sans JP
     font stack). Markdown explanations render through lazy-loaded
     `marked`+`dompurify` chunks — kept out of the initial bundle.
   - Design goal: plain but visually pleasing — light CSS, deterministic
     kanji data kept visually distinct from AI-generated explanations.

2. **LLM for Grammar Explanations**:
   - **Models**: `openai/gpt-oss-120b` primary → `openai/gpt-oss-20b`
     fallback, via the `groq` SDK (OpenAI-compatible)
     ([`app/grammar_explain.py`](../../app/grammar_explain.py)). Groq's free
     tier meters per-model, so the fallback doubles as an independent daily
     quota pool when the primary is exhausted; both raise "Grammar
     explanation service is down …" → 502 / SSE error.
   - **Authentication**: key loaded via `GROQ_API_KEY` using `python-dotenv`
     with automatic parent/root directory discovery (`find_dotenv()`).
   - **Design**: level-calibrated prompts for JLPT N5–N1, invoked **on demand**
     (per-sentence, on click) to bound latency and API usage.
   - **Free-tier budgeting**: `chat()` sends `reasoning_effort="low"` plus
     `max_completion_tokens` (grammar calls pass a per-level ceiling from
     `LevelConfig.max_tokens` — N5 950 down to N1 450). Responses are
     validated — empty text, `length` truncation, or leaked internal markers
     (`<|…|>`) retry with a 1.5× larger budget — and transient errors are
     retried twice, honoring `retry-after` on 429s (30 RPM / ~1,000 RPD per
     model). `explain_grammar_stream()` is the streaming variant used by the
     API's SSE endpoint (§3.3); `last_model()` reports whichever model
     actually served for telemetry.

3. **Embedding Models (FastEmbed)**:
   - **Dense**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim). Chosen via
     `eval/embed_model_bench.py`: `bge-small-en-v1.5` and
     `snowflake-arctic-embed-xs` are faster or comparable but English-only
     tuned and score near zero on Japanese-typed queries (MRR 0.10 vs 0.38).
   - **Sparse**: `Qdrant/bm25` for the BM25 hybrid arm.
   - Encapsulated in [`app/embedder.py`](../../app/embedder.py); ONNX models are
     cached under `models/fastembed/` and pre-warmed in the Docker image.

4. **Vector Database & Storage**:
   - **Database**: Qdrant v1.19.1 via Docker Compose (matches
     `qdrant-client==1.19.1`).
   - **Collection**: `jmdict_chunks` with **named vectors** — `dense` (cosine,
     384-dim) + `bm25` (sparse). Keyword payload indexes on `kanji_form`,
     `reading`, `gloss_keys`, `primary_gloss_keys`, `kanji_forms`, `readings`
     for the exact/canonical arms, plus float indexes on `commonness` and
     `wf_score` for the formula query (details in §2.2).
   - **Monitoring store**: SQLite at `data/monitoring/reikun.db`
     ([`scripts/feedback_log.py`](../../scripts/feedback_log.py)) — searches,
     feedback, kanji lookups, and explanation requests.

5. **Containerization & Deployment**:
   - Qdrant + the API are orchestrated via
     [`docker-compose.yml`](../../docker-compose.yml); both services have
     healthchecks and the app waits for a healthy Qdrant.
   - `docker compose up -d` → the API at `http://localhost:8000/` (`APP_PORT`;
     docs at `/docs`). Data, models, and the monitoring DB are
     volume-mounted.

---

## Step 1: Project Setup & Environment

### 1.1 Project Structure & Dependencies
Dependencies declared in [`pyproject.toml`](../../pyproject.toml) with
pinned versions, locked by `uv.lock`:
- **Vector DB & Embeddings**: `qdrant-client`, `fastembed`
- **LLM**: `groq`
- **API**: `fastapi`, plain `uvicorn` — the container runs
  `uvicorn app.api:app` directly (one worker), so `uvicorn[standard]`'s
  extras (uvloop/httptools/watchfiles/websockets, ~25 MB) were dead weight;
  the dev group carries only `watchfiles` for the `--reload` path
- **Utilities**: `python-dotenv`, `httpx`, `pydantic`
- **Japanese morphology**: `sudachipy` + `sudachidict-small` are runtime
  deps (~110 MB unpacked — `-small` covers the dictionary; `-core` at
  ~200 MB was the earlier pick) — `segment_japanese` uses them for real
  morpheme/word-unit splitting (`SplitMode.B`), and `build_chunks.py`'s
  `wf_score` uses the same tokenizer at ingest. The app's import is
  still optional: an environment without the packages falls back to the
  greedy matcher.
- **Ingest-only** (`ingest` dependency-group, deliberately not in
  `dependencies`): `wordfreq`, used only by `build_chunks.py`'s `wf_score`
  prior. `uv sync`/`uv run` install it via `dev`'s `include-group`.

### 1.2 Modular Code Layout
- `app/config.py` centralises all env-driven configuration (Qdrant, models,
  retrieval tuning flag `QUERY_REWRITE`, paths).
- `app/` is all UI-agnostic modules — retrieval, rewriting, lookup, LLM —
  plus `api.py` (routes) and `render.py` (JSON shaping). The `web/` frontend
  is a separate npm package. (The Streamlit pages lived in `app/ui/` until
  the Phase-4 removal.)
- [`.gitignore`](../../.gitignore) excludes `.venv/`, `models/`, `data/`, and the
  SQLite monitoring DB.

### 1.3 Raw Dictionary Data Acquisition
[`scripts/download_edrdg.py`](../../scripts/download_edrdg.py) rsyncs the EDRDG
originals from `ftp.edrdg.org::nihongo/` (regenerated daily upstream; the
`.gz` cache is kept for delta transfer, and each sync writes a
`<name>.xml.meta.json` sidecar with the upstream generation date, remote
mtime, and sha256):
- `data/raw/JMdict_e_NG_examp.xml` (74 MB, 218,786 entries, 31,974 Tatoeba
  example pairs embedded — the "Next Generation" JMdict schema with
  `nf01`–`nf48` frequency bands alongside the classic pri markers).
- `data/raw/kanjidic2.xml` (15.6 MB, 13,108 kanji characters).

[`scripts/download_kanjivg.py`](../../scripts/download_kanjivg.py) fetches the
stroke-order SVGs from the KanjiVG GitHub releases into `data/kanjivg/` for
offline rendering — picks the newest stable (non-prerelease) `rYYYYMMDD`
release, skips when the stored tag in `kanjivg.meta.json` already matches,
and extracts only the standard `kanji/<hex>.svg` files. The ~4,959
`-Kaisho`/`-VtLst`/etc. variant files in the release zip are dropped:
they're alternate glyph styles / stroke-order variants of the same
codepoint, and lookups resolve by plain codepoint filename (see
`Issues.md` → *Kanji decomposition & stroke* for the suffix
inventory).

### 1.4 Raw File Anatomy — JMdict_e_NG_examp & KANJIDIC2
What the two EDRDG XMLs look like inside, and which elements
[`scripts/build_chunks.py`](../../scripts/build_chunks.py) keeps vs.
leaves on the table (chunk-field details in §2.1). Both files are
one-element-per-line UTF-8 and carry the **full annotated DTD inside the
DOCTYPE internal subset** — entities expand at parse time, so
`<pos>&n;</pos>` reaches the parser as "noun (common) (futsuumeishi)",
and stripping the DOCTYPE breaks the files.

#### JMdict_e_NG_examp.xml — file frame
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- Rev 1.10  "XML Next Generation" changes:
     created/version root attrs; lsource moved sense→entry; <info> added;
     xref gained type/seq/dict/sno/xk/xr; <ant> removed;
     gloss <pri> element + g_gend attr removed. -->
<!DOCTYPE JMdict [
  <!ELEMENT entry   (ent_seq, k_ele*, r_ele+, lsource*, info*, sense+)>
  <!ELEMENT sense   (stagk*, stagr*, pos*, xref*, field*, misc*,
                     s_inf*, dial*, gloss*, example*)>
  <!ELEMENT example (ex_srce, ex_text, ex_sent+)>
  … 267 <!ENTITY> defs (pos / misc / field / dial codes) …
]>
<JMdict created="2026-09-19" version="1.10">   ← NG root attributes
  <entry> … </entry>   × 218,786
</JMdict>                                      ← rsync integrity marker
```

Three random entries verbatim (of 218,786):
```xml
<!-- kana-only entry: no k_ele, two r_ele, &col;/&dated; misc entities -->
<entry>
<ent_seq>2826268</ent_seq>
<r_ele><reb>ちんちんかもかも</reb></r_ele>
<r_ele><reb>ちんちんかも</reb></r_ele>
<sense>
<pos>&n;</pos><pos>&vs;</pos>
<misc>&col;</misc><misc>&dated;</misc>
<gloss>flirting (with each other)</gloss>
<gloss>fondling</gloss>
<gloss>billing and cooing</gloss>
</sense>
</entry>

<!-- mixed pri markers: spec2 is tier-1 → is_common, commonness 1.0;
     news2/nf38 are the tier-2 + frequency-band signals (a tier-2-only
     entry — news2/ichi2/gai2 without spec2 — would sit at 0.5);
     embedded Tatoeba example; three senses -->
<entry>
<ent_seq>1316270</ent_seq>
<k_ele>
<keb>時節</keb>
<ke_pri>news2</ke_pri><ke_pri>nf38</ke_pri><ke_pri>spec2</ke_pri>
</k_ele>
<r_ele>
<reb>じせつ</reb>
<re_pri>news2</re_pri><re_pri>nf38</re_pri><re_pri>spec2</re_pri>
</r_ele>
<sense>
<pos>&n;</pos>
<gloss>season</gloss>
<example>
<ex_srce exsrc_type="tat">83831</ex_srce>
<ex_text>時節</ex_text>
<ex_sent xml:lang="jpn">物には時節、番茶も出花。</ex_sent>
<ex_sent xml:lang="eng">There is a time for all things.</ex_sent>
</example>
</sense>
<sense><pos>&n;</pos><gloss>the times</gloss></sense>
<sense><pos>&n;</pos><gloss>opportunity</gloss><gloss>occasion</gloss></sense>
</entry>

<!-- no pri markers → is_common=False, commonness=0; four pos tags -->
<entry>
<ent_seq>1073930</ent_seq>
<k_ele><keb>スリム化</keb></k_ele>
<r_ele><reb>スリムか</reb></r_ele>
<sense>
<pos>&n;</pos><pos>&vs;</pos><pos>&vt;</pos><pos>&vi;</pos>
<gloss>slimming down</gloss><gloss>scaling back</gloss>
<gloss>thinning</gloss><gloss>streamlining</gloss><gloss>retrenchment</gloss>
</sense>
</entry>
```

#### JMdict elements — incorporated
- `ent_seq` → chunk `id` → Qdrant **point id** (upsert key; also the
  target namespace for `related` xrefs).
- `k_ele/keb` → `kanji_forms` (all variants, keyword-indexed for
  alternate-form exact match — 斑馬 → 縞馬); `primary_kanji` = first form
  with a tier-1 pri marker, else first → `kanji_form` payload; feeds
  `text`, `sparse_text`, and the `kanji_to_ids` backlink to KANJIDIC2.
- `k_ele/ke_pri`, `r_ele/re_pri` → unioned into `pris` → `is_common`
  (tier-1 `{news1,ichi1,spec1,spec2,gai1}`), `commonness` (1.0 / 0.5
  tier-2-only / nf gradient 0.75→0.02), `freq_band` (min `nfNN`) — the
  `FormulaQuery` priors (§3.1).
- `r_ele/reb` → `readings`; `primary_kana` (same pri-first rule) →
  `reading` payload + `text`/`sparse_text`.
- `r_ele/re_nokanji` + `re_restr` → `reading_restrictions`
  (reading→keb pairing, jmdict-simplified's `appliesToKanji`).
- `sense/gloss[xml:lang="eng"]` → `meanings` (all senses) and
  `primary_meanings` (sense 1 only) → `gloss_keys` /
  `primary_gloss_keys` (normalised exact-match keys) and the dense embed
  text `", ".join(meanings)`.
- `sense/example` → `example_sentences[:5]` (jpn/eng `ex_sent` pairs) —
  payload-only, excluded from both vectors (added noise).
- `sense/xref` → `related` (`{seq, text}` pairs, deduped).
- `sense/misc` → only the first-sense `&uk;` check → `kana_pref` →
  picks the kana form for `wf_score` (ありがとう not 有難う).
- `lsource` (entry-wide in NG) → `lsource` `[{lang, text}]` payload.
- `info` (NG-only element) → `notes` payload.

#### JMdict elements — not incorporated (and what they'd buy)
- `ke_inf` / `re_inf` — per-form orthography flags (`&ateji;`, `&ik;`
  irregular kana, `&oK;` outdated kanji, `&rk;` rare). Use: "irregular /
  rare spelling" badges on variant forms; demote mis-spellings from the
  exact-match arm.
- `ke_pri`/`re_pri` **per-form attribution** — currently unioned across
  the whole entry, losing *which* form is common. Use: better canonical
  display form and scoring `wf_score` on the form that's actually
  frequent.
- `stagk` / `stagr` — sense↔form binding ("this sense applies only to
  this reading/kanji"). Use: per-sense display, stop attributing a gloss
  to a reading it doesn't apply to.
- `pos` — entity-coded POS (`&n;`, `&vs;`, `&adj-i;`…). Use: POS facet
  filter, verb-aware `gloss_keys` ("to X"), context for grammar
  explanations.
- `field` / `dial` / `s_inf` — domain (`&comp;`, `&Buddh;`), dialect
  (`&ksb;`), free-text sense notes. Use: Jisho-style tag chips,
  domain-filtered search.
- `gloss g_type` — `lit`/`fig`/`expl` (+NG `descr`). Use: exclude
  `expl`/`descr` description-sentences from `gloss_keys` exact match;
  style literal/figurative glosses distinctly.
- `xref` attributes — `type` separates **antonyms** from see-refs
  (currently merged indistinguishably into `related`); `xk`/`xr`/`sno`
  pin the target's form/sense; `dict="jmnedict"` links name entries.
  Use: antonym chips, clickable cross-references, JMnedict merge.
- `example/ex_srce` (`exsrc_type="tat"` = Tatoeba sentence id) and
  `ex_text` (the surface form used in the sentence). Use: link sentences
  to tatoeba.org (already required by the CC-BY attribution), prefer
  examples whose `ex_text` matches the queried form.
- `re_pa` (pitch accent, in the NG DTD but unpopulated upstream) and
  `infl` (inflection, proposal stage) — nothing to parse yet.
- Non-English `gloss` — n/a: `JMdict_e*` is the English-only export.

#### kanjidic2.xml — file frame
```xml
<!DOCTYPE kanjidic2 [ <!ELEMENT kanjidic2 (header, character*)> … ]>
<kanjidic2>
<header>
<file_version>4</file_version>
<database_version>2026-262</database_version>   ← YYYY-NN serial
<date_of_creation>2026-09-19</date_of_creation>
</header>
<character> … </character>   × 13,108   (JIS X 0208 + 0212 + 0213)
</kanjidic2>
```
Character grammar: `character (literal, codepoint, radical, misc,
dic_number?, query_code?, reading_meaning?)` where `misc (grade?,
stroke_count+, variant*, freq?, rad_name*, jlpt?)` and
`reading_meaning (rmgroup*, nanori*)`.

Two random characters verbatim (of 13,108):
```xml
<!-- rare kanji: no grade/freq/jlpt, disputed stroke_count (14/15),
     moro ref with m_vol/m_page attrs, a skip_misclass query code -->
<character>
<literal>蔘</literal>
<codepoint>
<cp_value cp_type="ucs">8518</cp_value>
<cp_value cp_type="jis208">1-72-85</cp_value>
</codepoint>
<radical><rad_value rad_type="classical">140</rad_value></radical>
<misc><stroke_count>14</stroke_count><stroke_count>15</stroke_count></misc>
<dic_number>
<dic_ref dr_type="nelson_c">4032</dic_ref>
<dic_ref dr_type="nelson_n">5174</dic_ref>
<dic_ref dr_type="moro" m_vol="9" m_page="0872">31795X</dic_ref>
</dic_number>
<query_code>
<q_code qc_type="skip">2-3-11</q_code>
<q_code qc_type="sh_desc">3k11.18</q_code>
<q_code qc_type="four_corner">4420.2</q_code>
<q_code qc_type="skip" skip_misclass="stroke_diff">2-4-11</q_code>
</query_code>
<reading_meaning>
<rmgroup>
<reading r_type="pinyin">sen1</reading>
<reading r_type="korean_r">sam</reading>
<reading r_type="korean_h">삼</reading>
<reading r_type="vietnam">Tham</reading>
<reading r_type="ja_on">シン</reading>
<reading r_type="ja_on">サン</reading>
<meaning>luxurious growth of grass</meaning>
</rmgroup>
</reading_meaning>
</character>

<!-- common kanji: full misc, 23 dic_refs, deroo code, nanori, fr/es/pt -->
<character>
<literal>兵</literal>
<codepoint>
<cp_value cp_type="ucs">5175</cp_value>
<cp_value cp_type="jis208">1-42-28</cp_value>
</codepoint>
<radical>
<rad_value rad_type="classical">12</rad_value>
<rad_value rad_type="nelson_c">4</rad_value>
</radical>
<misc>
<grade>4</grade><stroke_count>7</stroke_count>
<freq>522</freq><jlpt>2</jlpt>
</misc>
<dic_number>
<dic_ref dr_type="nelson_c">201</dic_ref>
<dic_ref dr_type="heisig">1331</dic_ref>
<dic_ref dr_type="moro" m_vol="2" m_page="0085">1462</dic_ref>
<!-- … 23 dic_ref elements total (nelson_n, halpern_*, heisig6, gakken,
     oneill_*, henshall*, sh_kk*, sakade, jf_cards, tutt_cards, crowley,
     kanji_in_context, kodansha_compact, maniette) … -->
</dic_number>
<query_code>
<q_code qc_type="skip">2-5-2</q_code>
<q_code qc_type="sh_desc">2o5.6</q_code>
<q_code qc_type="four_corner">7280.1</q_code>
<q_code qc_type="deroo">2661</q_code>
</query_code>
<reading_meaning>
<rmgroup>
<reading r_type="pinyin">bing1</reading>
<reading r_type="korean_r">byeong</reading>
<reading r_type="korean_h">병</reading>
<reading r_type="vietnam">Binh</reading>
<reading r_type="ja_on">ヘイ</reading>
<reading r_type="ja_on">ヒョウ</reading>
<reading r_type="ja_kun">つわもの</reading>
<meaning>soldier</meaning><meaning>private</meaning>
<meaning>troops</meaning><meaning>army</meaning>
<meaning>warfare</meaning><meaning>strategy</meaning><meaning>tactics</meaning>
<meaning m_lang="fr">soldat</meaning>  <!-- +fr/es/pt meanings -->
</rmgroup>
<nanori>へ</nanori>
</reading_meaning>
</character>
```

#### KANJIDIC2 elements — incorporated
- `literal` → table key; `codepoint_hex` recomputed via `ord()` (drives
  the KanjiVG filename lookup).
- `misc/grade`, `freq`, `jlpt` → `grade`, `freq` (the ~2,501
  `_common_kanji` pool behind the shuffle button, §3.2), `jlpt_level`.
- `misc/stroke_count` → first value only (`findtext`).
- `rmgroup/reading[r_type=ja_on|ja_kun]` → `on_yomi` / `kun_yomi`.
- `rmgroup/meaning` (no `m_lang` = English) → `meanings`.
- `common_words` — synthesised: every kanji char in a chunk's
  `kanji_form` backlinks `word_id` into `kanji_to_ids`; each literal then
  pulls up to 10 `is_common` words (§2.1). The only JMdict↔KANJIDIC2
  join — nothing cross-references between the files upstream.

#### KANJIDIC2 elements — not incorporated (and what they'd buy)
- `codepoint/cp_value` jis208/212/213 kutens (ucs is recomputed, the
  JIS kuten codes dropped). Use: JIS-level provenance/filtering.
- `radical/rad_value` (classical + nelson_c). Use: radical browse /
  "kanji by radical"; pairs with `kradfile2` for the component search in
  `Issues.md`.
- `misc/variant` — alternate glyph/kuten links. Use: variant-glyph
  display, dedup.
- Extra `stroke_count` values — disputed counts (蔘: 14 **and** 15).
  Use: display "14–15 strokes".
- `misc/rad_name` — radical name for kanji that are themselves radicals.
  Use: show radical names in the kanji card.
- `dic_number/dic_ref` (~23 `dr_type`s — Nelson, Halpern, Heisig,
  Morohashi w/ `m_vol`/`m_page`, etc.). Use: "Heisig #1331"-style
  cross-refs for learners using those books; niche otherwise.
- `query_code/q_code` — `skip`/`sh_desc`/`four_corner`/`deroo` +
  `skip_misclass` attr. Use: find-kanji-by-shape (SKIP `2-5-2` → 兵)
  without needing kradfile. Licence caveat: SKIP/Halpern, Four
  Corner/Morohashi and De Roo codes retain third-party copyright
  (Issues.md, licence note).
- `nanori` — name readings. Use: name lookup; JMnedict tie-in.
- Non-ja readings (pinyin/korean/vietnam) and non-en meanings
  (fr/es/pt) — multilingual display; `Issues.md` already defers this.
- `rmgroup` structure — multiple rmgroups bind readings to *their*
  meanings; flattening merges all into one list. Use: per-reading sense
  display.
- `header` fields — surface dataset version in an About/Sources page
  (the licence asks for regular updates anyway). Note:
  `download_edrdg.py`'s `_GEN_DATE_RE` matches `created[=:]`, which
  kanjidic2's header lacks → `generation_date_from_header: null` in its
  `.meta.json`; matching `date_of_creation` would fix it.

---

## Step 2: Data Ingestion Pipeline

### 2.1 Parsing & Chunk Construction
[`scripts/build_chunks.py`](../../scripts/build_chunks.py) — stream-parses both
EDRDG XMLs with `ElementTree.iterparse` (the DOCTYPE internal subset is kept:
all ~270 `<!ENTITY>` defs resolve automatically):
- **Word + example chunks (`data/processed/chunks.json`)**: primary kanji/kana
  forms (preferring `common`-marked forms), English meanings, paired Tatoeba
  sentences, every variant form (`kanji_forms`/`readings` for alternate-form
  exact match), `freq_band` (min `nfNN` band), `related` (typed xrefs),
  `lsource` (loanword origin), entry `notes`, `is_common` (tier-1 pri markers
  `{news1, ichi1, spec1, spec2, gai1}` — tier-2 markers never produce `common`
  on their own upstream), and three ranking fields:
  - `commonness` — real-valued prior: 1.0 for tier-1 pri markers, 0.5 for
    tier-2-only (`{news2, ichi2, gai2}`), otherwise an nf-band gradient of
    0.75 (nf01, top-500) down to ~0.02 (nf48).
  - `wf_score` — corpus Zipf frequency (wordfreq, ~0–7) of the *written*
    form: the kanji form, or the kana form when the entry has no kanji or
    its first sense is `&uk;` ("usually written in kana" — ありがとう 5.70,
    not 有難う 3.2). Never the max of both (a one-mora reading collides
    with a frequent particle — 屁/へ 6.08), and minus one Zipf decade per
    extra token so phrases can't score like single words (口にする vs
    食べる). This is the canonical-ordering prior that separates
    near-synonyms sharing pri markers and nf band (仕事 5.68 / 作業 4.91)
    and ranks katakana both ways (ゲーム 5.62 vs キャット 3.14). wordfreq
    lives in the `dev` dependency-group; the score is precomputed into
    the payload, the app never imports it. wordfreq's `ja` path
    lazy-imports `wordfreq.mecab` (mecab-python3/ipadic were removed);
    `_ja_tokenizer` registers a Sudachi-backed shim in `sys.modules` so
    all ja lookups run through the runtime segmenter instead.
  - `gloss_keys` — every English gloss normalised for exact-match filtering
    (`app/query_rewrite.py::gloss_keys`: lowercase, parentheticals stripped
    — 犬's "dog (Canis (lupus) familiaris)" → `dog` — plus a "to"-less
    variant for verb glosses). `primary_gloss_keys` is the same keys for
    **sense 1 only**, so the canonical prior can tell an entry's main
    meaning from minor senses — without it frequency alone is harmful
    (足 "leg" lists "money" and would beat お金; 委員長 lists "chair" and
    would beat 椅子).
  Per-entry text fields: `text` = `<kanji/kana> [<reading>]: <first 3
  meanings>` — the display line, kept short; `sparse_text` = every
  variant form + reading + all meanings — the BM25 document, so the
  Japanese route hits alternate forms (しまうま → 縞馬) and English BM25
  matches deep glosses. All English glosses are retained in `meanings` and
  `gloss_keys` (443,285 total; max 79 on a single entry). Example
  sentences are stored for display but excluded from every embedded text
  (they added noise to both dense vectors and the BM25 vocabulary).
- **Kanji table (`data/processed/kanji_table.json`)**: KANJIDIC2 records —
  meanings, On/Kun readings, stroke counts, grade, frequency, JLPT level,
  `codepoint_hex` — cross-referenced with JMdict for up to 10 common words
  per kanji (13,108 records — the XML covers ~2.7k more kanji than the old
  JSON export, which silently dropped characters without English glosses).

### 2.2 Dense + Sparse Ingestion into Qdrant
[`scripts/ingest.py`](../../scripts/ingest.py):
- (Re)creates `jmdict_chunks` with named vectors `dense` + `bm25`.
- Creates keyword payload indexes on `kanji_form`/`reading`/`gloss_keys` plus
  `primary_gloss_keys` and `kanji_forms`/`readings` (every variant form) for
  the exact-match and canonical-match arms.
- Encodes all 218,786 entries in batches by default — `--common` selects the
  `example_sentences or is_common or freq_band ≤ 24` subset (~37k, quick
  testing), `--freq-band N` widens that cutoff. The shipped collection is a
  default (all-entries) ingest:
  rare markerless entries like 縞馬 ("zebra" — no pri/nf markers, no
  examples) fail every marker-based filter, and `gloss_keys` exact match
  plus the priors below keep them ranked correctly once indexed.
- Vector inputs: dense embeds the full English gloss list
  (`", ".join(meanings)` — the English-tuned model never sees Japanese
  script since the `ja` route skips dense); BM25 indexes `sparse_text`.
- `commonness` and `wf_score` also get **float** payload indexes: the
  `FormulaQuery` mult expressions reference them, and Qdrant Cloud enables
  `strict_mode` by default — every filtered/formula field needs an index
  there (self-hosted Qdrant happily full-scans instead).

> **Payload indexes & rebuilding.** A keyword payload index is an inverted
> map `value → point ids` (e.g. `斑馬 → [1321690]`) stored on disk — filters
> hit it in O(1) instead of scanning all 218k payloads. It's a derived
> structure, safe to rebuild: `delete_payload_index` +
> `create_payload_index(field, PayloadSchemaType.KEYWORD, wait=True)`
> walks all points and rebuilds it; points/vectors are untouched. Needed
> in practice when: (a) after a **snapshot restore** — index declarations
> carry over but the index data can be stale, queries 400 with `Index
> required but not found for "<field>"` until rebuilt; (b) strict-mode
> clouds reject any filter/formula field lacking an index — including
> `commonness` (needs `PayloadSchemaType.FLOAT`).

### 2.3 Ingestion Pipeline
[`scripts/startup.py`](../../scripts/startup.py) — the container entrypoint —
owns the ingestion workflow as a plain Python pipeline (`ingest_pipeline`):
a `wait_for_qdrant` readiness loop (30 × 2 s), a `check_state` deciding
between full/ingest-only/skip, then `download-edrdg` + `download-kanjivg` →
`build-chunks` → `ingest` with retries on the network/DB steps, then
uvicorn launches. Ingestion is **opt-in**: a plain boot goes straight to
the API; `INGEST_VIA_DOCKER=1` / `--ingest` runs the pipeline first, `--ingest-only`
runs it without launching the server. (Earlier versions ran this as a Prefect
flow; it was removed because a four-step linear pipeline gains nothing from
an orchestrator — Prefect added ~150–350 MB RAM and a cloud dependency, the
difference between fitting and timing out on Render's free tier.)
Each underlying script (`download_edrdg.py`, `download_kanjivg.py`,
`build_chunks.py`, `ingest.py`) remains runnable standalone — `ingest.py`
exposes `run()` for programmatic use.

---

## Step 3: Retrieval, Lookup & LLM Services

### 3.1 Retrieval Engine
[`app/retrieval.py`](../../app/retrieval.py) — pipeline: **rewrite → route →
retrieve**. The default mode is `auto`, which routes the
rewritten query to the best plan (`route_query`):
- **Japanese input** → BM25 (on `sparse_text`) + exact-match
  (`kanji_form`/`reading`/`kanji_forms`/`readings`) arms, RRF weighted
  1.0/2.0 toward exact so a headword hit pins to the top; the English-tuned
  dense model is skipped entirely (~4 ms vs ~1.3 s cold for these queries).
- **English word (≤3 tokens — gloss-style phrases like "to be late" behave
  as word lookups)** → dense + BM25 + exact `gloss_keys` arms fused by RRF,
  then re-scored by a `FormulaQuery`:

      score = RRF + EXACT_BONUS·exact + COMMON_BOOST·commonness
                  + CANONICAL_BOOST·wf_score·primary

  with `EXACT_BONUS=1.0`, `COMMON_BOOST=1.0`, `CANONICAL_BOOST=3.0`.
  `exact` fires when the query equals a headword/reading/variant or a
  normalised gloss (several arm positions, so an exact dictionary hit
  outranks a merely-similar one — 犬 over 猟犬 for "dog"); `primary`
  restricts the canonical prior to entries whose *first sense* matches
  (`primary_gloss_keys`). This formula is what fixed the Hit@1 collapse of
  the full 218k ingest, where pure-vector rare entries beat canonical words
  ("cat" → キャット over 猫): Hit@1 24 → 77 on the 100-word eval.
- **English sentence (4+ tokens)** → dense-heavy RRF (dense arm weighted
  2×, no exact arm — a sentence can't equal a headword or gloss key).
- **Prefetch pool**: every arm fetches `max(100, 4·num_results)` candidates
  (`PREFETCH_MIN`/`PREFETCH_FACTOR`) — the formula can only re-score what
  the arms return, so this is the recall ceiling (30→100 moved Hit@5
  77→91, flat past that; retrieval stays ~20–25 ms).
- **Compound Japanese queries**: when the ja route finds no exact headword
  hit (checked against every variant form via `entry_forms()`),
  `segment_japanese()` splits the query into dictionary segments. With
  `sudachipy` + `sudachidict-small` installed (runtime dep — a slim image
  can drop the two packages and falls back to greedy) it is a real
  morphological analysis (`_segment_sudachi`, `SplitMode.B` word units —
  法学部/図書館 stay whole while 位置し→位置+し stays split): morphemes
  carry lemmas
  (食べ→食べる, 位置し→位置する…'s し→する) and POS, so content words resolve
  by lemma against `headword_index()`, 助詞 particles take the
  `_PARTICLES` gloss table (readings use the modern pronunciation — は→わ,
  へ→え, を→お — since their JMdict headwords are unrelated: の's is 乃),
  助動詞 auxiliaries take `_AUX_GLOSSES` (ます→polite, た→past — their
  kana-form JMdict hits are unrelated nouns like ます→升), and subsidiary
  verbs after て/で (いる→progressive, しまう→completely) take
  `_SUBSIDIARY` — without it a plain JMdict lookup glosses て+いる as
  射る "to shoot". Inflection tails are then *merged back* into one badge:
  a maximal run of ending parts (助動詞 + subsidiary verbs + the て/で
  gluing them — a て/で only counts when followed by an ending part, so
  食べて寝る keeps its connector て separate) attaches to the preceding
  stem token, so 食べ+まし+た renders as one `食べました` badge and
  し+て+い+ます as `しています`; the tooltip lists the per-morpheme
  breakdown (`options`, same mechanism as `_ambiguous`). A *compound
  rescue* pass then re-joins adjacent index-resolved segments whose
  concatenated surface is itself a headword (精進+料理 → 精進料理,
  飲み+物 → 飲み物) — Sudachi's dict only merges the units it knows, at
  any split mode. Merges require token adjacency (skipped tokens like
  punctuation can't bridge: 山、川 stays 山 + 川) and chain naturally;
  ambiguous merges list all candidates. Without Sudachi,
  `_segment_greedy` does a longest-match
  against the index (single-character segments must be kanji; the same
  particle table supplies の/は/に). `headword_index()` is a
  `TrieIndex` — a marisa-trie form→[entry,…] map of every
  headword/variant served from the committed
  `data/processed/headword_index.marisa` (~27 MB, mmap'd, baked into the
  image, ~5 MB RSS vs ~340 MB for the in-memory dict it replaced);
  contested keys keep all
  candidates in ingest order and the token's contextual `reading_form`
  picks the consistent pair — 東→ヒガシ resolves to the ひがし "east"
  entry — since a JMdict popularity rank can't select readings reliably.
  When no candidate matches the reading the segment shows *every*
  candidate (`_ambiguous`: the badge tooltip lists each reading+gloss)
  rather than a misleading first pick. If the `.marisa` file is missing
  (`_build_headword_trie`), it is rebuilt from one payload-only scroll
  (limit=5,000/request, ~44 requests over the 218,786-point collection)
  and saved for the next boot — self-provisioning hosts pay the old
  ~340 MB in-memory dict cost while building, so deploys should ship the
  file. Either way it is
  kept for the process lifetime. The build is
  guarded by a lock so concurrent first callers share one scroll, and
  `warm_headword_index()` kicks it (and the Sudachi dictionary load) off
  on a daemon thread at app startup —
  a user's first compound query waits on the in-flight build instead of
  paying the whole scroll itself. The random-kanji button likewise stays
  off it, using `is_headword()` (§3.2) instead — the fix for the
  slow first click (`Issues_old.md` #U8).
  Segments go into `meta["segments"]` for the UI's parsed-word row,
  and are promoted into `results` when the query has no hits at all
  (静かな場所 → 静か + 場所, 例訓 → 例 + 訓). Remaining limits: shared
  readings pick one homograph (main-verb いる can gloss as 射る "to
  shoot", not 居る "to exist"), and tokenizer-free environments inherit
  the greedy matcher's inflection blindness.
- **Length caps** (`MAX_QUERY_CHARS`, `MAX_JA_QUERY_CHARS`): over-long input
  is rejected before any rewrite/embed/DB call — the response carries empty
  results + `meta["too_long"]` so the UI shows a "too long" warning rather
  than a misleading "Nothing found". The raw cap (150 chars, any language)
  is script-blind; post-rewrite Japanese is held to 100 chars, shared with
  `segment_japanese`'s ceiling — ja sentences up to that length are
  legitimate "sentence lookups" the matcher can segment; past it the input
  is prose, not a lookup.
- **`is_headword(term)`** — one filtered `count` on `kanji_form`/
  `kanji_forms` (~1 request, ~ms): the cheap headword probe the
  random-kanji button uses instead of building `headword_index()`.
- **Explicit modes** (`vector` / `text` / `hybrid`) remain for eval tooling —
  hybrid = dense + BM25 + exact-match, fused server-side with Qdrant RRF.
- **Query rewriting** ([`app/query_rewrite.py`](../../app/query_rewrite.py)):
  heuristic regex normalisation (free, default) → optional LLM rewrite for
  long descriptive English queries (`QUERY_REWRITE=auto`).
- **Caching**: `search()` is `lru_cache`d per process — a repeated query
  (same or another user, same settings) is served without re-embedding or
  re-querying.
- **Re-ranking**: implemented (local cross-encoder and Cohere Rerank),
  evaluated, and removed — on this bilingual corpus an English-tuned
  cross-encoder prefers rare pure-gloss entries for the same reason the
  dense model does (Hit@1 dropped to 14 with ms-marco).

### 3.2 Deterministic Kanji & Stroke-Order Lookup
[`app/kanji_lookup.py`](../../app/kanji_lookup.py): cached lookup over
`kanji_table.json`; stroke-order diagrams served from the committed
`data/processed/strokes.json` — ~6,416 diagrams ({view_box, strokes,
numbers}) pre-extracted from the KanjiVG SVGs by
`scripts/download_kanjivg.py`. No runtime network or LLM involved (the
fetch-once-from-GitHub fallback and the raw `?svg=` response are gone;
missing diagrams are simply absent). `random_kanji()` picks uniformly from the ~2,501
frequency-ranked kanji (`_common_kanji`, `lru_cache`d). The Search page
keeps the pick to kanji that are themselves JMdict headwords — a lone
kanji often isn't a standalone word, and an unrestricted pick rendered the
kanji card above an empty result list ~28% of the time (~1,793 of the pool
qualify). `/kanji/random` (`app/api.py`) therefore draws candidates and
probes each with `is_headword()` — one filtered-count request per try,
expected ~1.4 tries, capped at 8 — instead of restricting `within=` a
`headword_index()` built up front; that one-time scroll was the slow
first click. If Qdrant is unreachable (or 8 misses in a row) it falls
back to an unrestricted pick.

### 3.3 JLPT-Aware Grammar Explanation
[`app/grammar_explain.py`](../../app/grammar_explain.py): level-aware vs generic
prompts, concise Markdown bullets, bounded token budgets and malformed-output
detection as described above. A `_LEVEL` dict holds each JLPT level's
`LevelConfig` (learner profile, style instruction, bullet range, word
ceiling, `max_tokens`), so depth *and* length scale N5→N1. Entry points:
`explain_grammar()` (blocking) and `explain_grammar_stream()` (generator
consumed by the API's SSE endpoint — stream creation retries
via `_with_retries`, and if the stream dies before emitting any text it
falls back to the blocking call; once text has streamed, errors propagate
since partial output can't be safely retried).

### 3.4 Monitoring & Feedback Logging
[`scripts/feedback_log.py`](../../scripts/feedback_log.py): SQLite (WAL mode)
tables for searches (`query_hash`, `rewritten_query_hash`, rewrite method,
mode, num_results, result count, top result, latency), thumbs feedback
(`kind` = search | explanation → `ref_id`, ±1), kanji lookups (with
`source` = search | pill | api — 'dialog' survives as the legacy value),
and explanation requests (`sentence_hash`, JLPT level, model, latency, ok
flag). Searches store the raw `query`/`rewritten_query` plus a `rewritten`
flag alongside their `_h()` 12-hex SHA-256 prefixes; feedback and
explanation text stays hash-only. Rows are kept forever (the
`TELEMETRY_RETENTION_DAYS` pruning knob was removed). The stdout sink
emits the same fields as JSON lines.

### 3.5 HTTP API
[`app/api.py`](../../app/api.py) — the standalone FastAPI service the
container runs (`uvicorn app.api:app`, routes at the root, one worker, CORS
from `CORS_ORIGINS`). A `lifespan` hook kicks `warm_headword_index()` on
daemon threads so `/health` is live while the trie, Sudachi dictionary and
ONNX sessions load. Endpoints: `GET /health` (liveness only) and
`GET /ready` (readiness — real count + scroll against the collection, 503
until populated); `GET /search` (the same `search()` pipeline, with `mode` /
`rewrite` / `log` params; results carry `ruby` furigana parts and parsed
Japanese sentences come back under top-level `segments` as chip JSON);
`GET /kanji?chars=…` (batch hover cards — one round-trip per sentence of
tooltips); `GET /kanji/{char}` (the full card: `meta` badges, `readings`
split into stem/okurigana, `common_words` with ruby parts; `?strokes=true`
adds sanitized KanjiVG data — viewBox + path `d`s + number labels — served
from the committed `data/processed/strokes.json`, pre-extracted from the
SVGs by `scripts/download_kanjivg.py`, so no SVGs and no network at
request time); `POST /explain` and `POST /explain/stream`
(SSE — `data:` chunks, then a `done` event carrying `explanation_id`); and
`POST /feedback`. Swagger UI at `/docs`; `scripts/export_openapi.py` commits
`docs/api/openapi.json` for frontend type generation. Event logging goes
through the `telemetry()` interface (`app/telemetry.py`): `TELEMETRY=stdout`
emits one JSON line per event (default, stateless), `=sqlite` keeps the
`scripts/feedback_log` monitoring DB. Searches carry raw
`query`/`rewritten_query` (+ `route`, `embed_ms`, `retrieve_ms`,
`rewritten`); feedback and explanation text stays hash-only (§3.4).

---

## Step 4: SvelteKit Frontend

The frontend is a fully client-side SPA in [`web/`](../../web/) — one
route (`/` + SPA fallback), components in `web/src/lib/components/`,
typed API client in `web/src/lib/api.ts` (openapi-fetch, types generated
from `docs/api/openapi.json`).

- **Search**: `?q=` drives everything — on mount and on `popstate` the
  page fetches `/search` and re-renders, so every state is a shareable
  URL and browser-back works. The merged input+button control sits in a
  landing hero (centered, typewriter placeholder that types, holds and
  backspaces — `typewriter.svelte.ts`) that compacts into a sticky,
  frosted translucent header once results exist (backdrop-blur, matches
  the input translucency). Shuffle + JLPT selector sit beside it as
  separate bordered tools at the same height/padding as the submit
  button. One automatic retry covers transient 502/503/504s (Cloud Run
  cold starts, waking Qdrant) with a "waking up" hint.
- **Results** (`ResultCard.svelte`): `<ruby>` furigana headword parts,
  common badge, meanings, example sentences (`ExampleRow.svelte`) with a
  per-sentence "Explain grammar" action that streams `/explain/stream`
  (SSE) through lazy-loaded `marked`/`dompurify` chunks — kept out of the
  initial bundle; an empty list renders "No example sentences." The
  stats line keeps "N entries" + thumbs feedback (`Feedback.svelte` →
  `POST /feedback`) left and a muted ⓘ cluster right (mode · route · ms
  · embed ms · retrieve ms).
- **Kanji navigation**: every kanji in headwords and examples is a real
  link through `KanjiText`→`KanjiTip` (middle-click/copy-link still work,
  left-click runs an in-page `?q=` search) with a hover tooltip batched
  through `GET /kanji?chars=…` (microtask-coalesced in
  `lib/hover.svelte.ts`). Kanji with live tooltips carry a dotted
  underline; the accent colour is reserved for the search submit. A
  single-kanji query shows the full card (`KanjiCard.svelte` +
  `StrokeSvg.svelte` stroke-order animation over a dashed practice grid,
  readings split onyomi/kunyomi, common words) and picking a kanji deep
  in the results smooth-scrolls the card into view (anchor +
  `scroll-margin-top` clearing the sticky bar).
- **Japanese sentence queries**: unmatched sentences get a "parsed as"
  chip row (`SegChips.svelte`) from the top-level `segments` field —
  ruby + gloss per Sudachi word unit.
- **Chrome**: `Header.svelte` (title home, KB status dot polling
  `/ready`, theme picker writing `data-theme`+localStorage),
  `Segmented.svelte`/`Popover.svelte` JLPT selector, `Footer.svelte`
  attributions (JMdict/KANJIDIC2 © EDRDG CC BY-SA 4.0; Tatoeba CC-BY;
  KanjiVG CC BY-SA 3.0).

---

## Step 5: Evaluation

- **Gold set**: `eval/gold_set.tsv` is the single gold source for all suites —
  one row per query (`category <TAB> query <TAB> expected_answers <TAB>
  notes`), alternatives joined by ` / `, notes recording why an alternative
  counts. Subsets: `en_words` + `en_verbs` (50 each = the default 100-query
  benchmark), `en_descriptive`, `ja_words`, `ja_hiragana`, `ja_katakana`
  (300 queries total). `eval/eval.py` owns loading and resolves expected
  headwords to entry IDs via `chunks.json`.
- **Retrieval** (`eval/eval.py --ir`): reports Hit@k, MRR, NDCG@5, and MAP.
  In the `--no-llm` grid: vector 0.365 MRR, BM25 0.556, hybrid 0.668,
  +heuristic rewrite 0.724. Reranking was tried (local cross-encoder and
  Cohere Rerank), reduced MRR on both, and was removed — hybrid + heuristic
  rewriting is the shipped pipeline. The
  full grid with `QUERY_REWRITE=auto` reaches ~0.77 MRR but costs one LLM
  call per query. `--modes` runs the text/hybrid/auto comparison;
  `--canon`/`--pool`/`--common` sweep the scoring knobs in-process and write
  timestamped md + a query×variant rank CSV. Results: `eval/results/`.
- **Latest numbers** (300-query gold, 218,786-point collection, production
  config): `en_words` + `en_verbs` Hit@1 84 / Hit@2 97 / Hit@5 100 at ~24 ms
  (vs Hit@1 24 right after the full ingest — the canonical prior did the
  work); `ja_*` subsets Hit@1 ≈ 98 at ~3–5 ms; `en_descriptive` Hit@1 21 at
  ~390 ms — the weak subset: "a word for X" phrasings route as word lookups
  so the LLM rewriter never fires, and the rewrite path tails badly on
  free-tier rate limits. Residual en misses are mostly arguable
  generic-vs-specific gold labels (車 vs 自動車) and gloss-wording gaps
  ("phone" vs JMdict's gloss "telephone" — no synonym data).
- **Embedding models** (`eval/embed_model_bench.py`): MiniLM retained —
  `paraphrase-multilingual-MiniLM-L12-v2` is the documented fallback if
  dense recall ever becomes the bottleneck (+0.02 MRR on the bench but
  4.7× slower embed, still zero on kana). `eval/reports/embed_model_bench.json`.
- **LLM prompts** (`eval/eval.py --llm`): level-aware vs generic on 5 sentences
  × N5/N1, scored by an LLM judge plus objective proxies, with a per-call
  rate limiter to stay within the free-tier RPM cap — level-aware
  adopted. Results: `eval/reports/llm_eval.md`.

---

## Step 6: Docker Deployment

### 6.1 Dockerfile
[`Dockerfile`](../../Dockerfile): Python 3.13 slim on Debian 13 trixie
(`python:3.13-slim-trixie` — the suite is pinned so the `slim` alias can't
silently move to the next Debian release), deps installed by `uv sync --frozen`
into `/app/.venv` in two stages — third-party deps first
(`--no-install-project`, cached on the lockfile), then the project itself
as an editable install that provides the `reikun` console script
(`uv.lock` is committed). The `INGEST_VIA_DOCKER` build arg (default 0 —
lean runtime-only image) does double duty: `--build-arg INGEST_VIA_DOCKER=1`
makes apt install `rsync` (`download_edrdg.py`) and `uv sync` include the
ingest group (wordfreq for `build_chunks.py`), and `ENV
INGEST_VIA_DOCKER=$INGEST_VIA_DOCKER` bakes it into the image so the
container *also* runs the pipeline at boot —
one flag for capability and behavior. Dependency-groups keep the image lean:
the default `dev` group (which includes `ingest`) is synced out via
`--no-default-groups`, so the runtime carries no wordfreq or dev tooling
(Phase 1 slim image; the `ui` group — Streamlit stack — was removed in
Phase 4 when the frontend fully replaced it). Runs as an unprivileged user (`app`, UID 1000 —
matches the host user so compose bind mounts stay writable). Pre-warms the
embedding/sparse ONNX models at build time, healthcheck on `/health`
(liveness; `/ready` is the real-query probe for orchestrators),
`CMD ["reikun"]` → `scripts/startup.py`, which `exec`s uvicorn so it is
PID 1 and receives `docker stop`'s SIGTERM directly.

### 6.2 Docker Compose
[`docker-compose.yml`](../../docker-compose.yml):
- **`qdrant`** (v1.19.1): ports 6333 (REST) / 6334 (gRPC, unused by the
  app) bound to `127.0.0.1` only — Qdrant has no auth by default; named
  volume; TCP-connect healthcheck on 6333.
- **`app`**: the uvicorn API on container port 8000 →
  `127.0.0.1:APP_PORT` (default 8000), `depends_on: qdrant healthy`, bind
  mounts for `data/{processed,raw,kanjivg,monitoring}` plus a `models`
  **named** volume — named volumes seed from the image on first creation,
  so the ONNX models pre-warmed in the Dockerfile are actually used (a
  bind mount would mask them and force a re-download). `QDRANT_HOST=qdrant`
  is the only hardcoded env; everything else (`GROQ_API_KEY`,
  `EMBED_MODEL`, `QUERY_REWRITE`, …) comes from `.env` via `env_file:`
  (optional) or `app/config.py` defaults. `restart: on-failure:3`, not
  `unless-stopped`: `startup.py` exits 1 when the ingest pipeline fails
  and unless-stopped would retry forever, re-downloading JMdict each time.
  `INGEST_VIA_DOCKER` reaches the build via `args:` (`.env`/shell)
  and is baked into the image env — one var for tooling + boot behavior (§6.1);
  a `.env` value also reaches the container env via `env_file:`, so it can
  toggle the pipeline at runtime without a rebuild.
- Hosts whose resolver fails inside containers (HF Hub, ftp.edrdg.org,
  Groq unreachable) can copy
  [`docker-compose.override.yml.example`](../../docker-compose.override.yml.example)
  to `docker-compose.override.yml` (gitignored, auto-merged) for a public-DNS
  `dns:` block — deliberately not in the committed compose file, since
  forced resolvers break split-horizon/corporate DNS.

---

## Step 7: Cloud Deployment

Moved to [`Deployment.md`](Deployment.md) — current production stack:
**Qdrant Cloud** vectors + **Cloud Run** API + **Cloudflare Pages**
frontend. The superseded free-tier Render walkthrough is archived in
[`Deployment_old.md`](Deployment_old.md).

---

## How to Run

### Option A: Using Docker Compose (Recommended)
```bash
cd Reikun

# Set your Groq API key in .env or environment
export GROQ_API_KEY=your_key_here

# Launch both Qdrant and the API
docker compose up -d

# API → http://localhost:8000/ (docs at /docs) · frontend → web/ (npm run dev)
```

### Option B: Local Python Development
```bash
cd Reikun

# 1. Start Qdrant
docker compose up -d qdrant

# 2. Download + ingest data (first run only)
uv run python scripts/download_edrdg.py
uv run python scripts/download_kanjivg.py
uv run python scripts/build_chunks.py
uv run python scripts/ingest.py

# 3. Run the API (same entrypoint the container execs)
uv run uvicorn app.api:app --port 8000
# Frontend (dev): cd web && npm install && npm run dev   # → http://localhost:5173/

# API → http://localhost:8000/ (docs at /docs)
```
