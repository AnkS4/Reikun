# Issues — debugging log

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

Post-mortem log: each entry is a self-contained write-up (symptom →
confirmed root cause → fix, plus what was tried and rejected), grouped by
area. Issue IDs are `<section letter><n>`:

- **UI (U1–U12)** — Streamlit-era regressions, all superseded by the
  Phase-4 deletion of the Streamlit app; archived to `Issues_old.md`.
- **Deployment (D1–D9)** — issues hit rolling out v2 on the cloud host,
  plus the 0.8.0 retrieval-scoring investigation (D9).
- **Segmentation & furigana (S1–S6)** — sentence-split and gloss-selection
  findings from the NHK Easy validation batches.
- **Frontend (W1–W3)** — SvelteKit-era UI issues.
- **Completed items / data sources** — folded from `Plan.md`: what shipped
  and why, plus the data-source reference and follow-ups.

Five-digit `#NNNNN` numbers inside entries are upstream Streamlit/GitHub
issues, not this log.

> Dev gotcha carried forward from the archive: the uvicorn API caches
> imported `app/` modules and has no auto-reload — restart the server
> after editing e.g. `retrieval.py`, or requests keep hitting stale code.

---

# Deployment issues — v2 rollout on the cloud host

Surfaced while pulling `3cff986` ("feat: v2 overhaul — HTTP API, simplified
UX, uv packaging, unified eval") on the production VM and running
`docker compose up -d --build`. All resolved; each traces to a v2 change
that an existing deployment has to absorb. Common pattern: every
failure was host-state drift against the new in-repo defaults, and the two
gitignored surfaces — `.env` and `docker-compose.override.yml` — are where
that drift must be reconciled per host.

---

## D1. `git pull` aborted — local changes would be overwritten

**Symptom.** `error: Your local changes to the following files would be
overwritten by merge: data/processed/kanji_table.json, docker-compose.yml`.

**Root cause.** The cloud checkout carried uncommitted edits: a `caddy`
service (reverse proxy on ports 80/443, `./Caddyfile` mount, `caddy_data`
volume) appended to the tracked `docker-compose.yml`, plus a locally
regenerated `kanji_table.json` — a single-line build artifact, safe to
discard since the committed copy is canonical.

**Fix.** Moved the caddy service into `docker-compose.override.yml`
(gitignored, auto-merged by every `docker compose` invocation — see
`docker-compose.override.yml.example`), then
`git checkout -- docker-compose.yml data/processed/kanji_table.json` and
`git pull`. Note the new compose file reads `.env` via `env_file:` and no
longer interpolates `${VAR}`s, so host config lives in `.env` + the
override only.

---

## D2. Site down after `up -d` — project name change orphaned the volumes

**Symptom.** All containers reported Started/Healthy but the domain served
nothing.

**Root cause.** v2 adds `name: reikun-app` to `docker-compose.yml`. Compose
prefixes volume names with the project, so `reikun-app_qdrant_data` and
`reikun-app_caddy_data` were created **empty** while the indexed Qdrant
collection and Caddy's Let's Encrypt certs stayed behind in
`reikun_qdrant_data` / `reikun_caddy_data` (the old directory-derived
project name was `reikun`).

**Fix.** Pin the old names in the override so the existing volumes mount:

```yaml
volumes:
  qdrant_data:
    name: reikun_qdrant_data
  caddy_data:
    name: reikun_caddy_data
```

Verify names first with `docker volume ls | grep -E 'qdrant|caddy'`.
Related: the app's host port is `127.0.0.1`-bound, so the Caddyfile must
proxy to `app:8000` over the compose network (was `:8501` in the Streamlit
era — the API's uvicorn port since the Phase-4 migration) — unaffected by
the loopback binding, and the intended only-public-ingress topology anyway.

---

## D3. App crash-loop — `QUERY_REWRITE='nano' invalid`

**Symptom.** `app-1` exited at startup with
`ValueError: QUERY_REWRITE='nano' invalid; expected one of ['auto', 'heuristic', 'off']`
(app/config.py validates at import), and `restart: on-failure:3` left the
container dead after three tries.

**Root cause.** The cloud `.env` predated v2's validation — `nano` was a
stale experimental value; the option set is now `auto | heuristic | off`.
The same file's `RERANKER=...` is dead config — the cross-encoder was
removed entirely in v2.

**Fix.** `QUERY_REWRITE=auto` (or `heuristic`) in `.env`; deleted
`RERANKER`. `.env` is gitignored so it never travels with `git pull` —
each host's copy must be reconciled manually when the schema changes.

---

## D4. Dashboard `sqlite3.OperationalError: attempt to write a readonly database`

**Symptom.** Dashboard crashed at `PRAGMA journal_mode=WAL` in
`feedback_log._conn()` — even opening the DB failed.

**Root cause.** The v2 Dockerfile adds `USER app` (uid 1000); files under
the `./data/monitoring` bind mount were written by the old root-running
container, so the process inherited a root-owned SQLite DB it cannot
write.

**Fix.** `sudo chown -R 1000:1000 data/` on the host, then
`docker compose restart app`. Whole-tree chown (not just `data/monitoring`)
because `data/processed` and `data/raw` need the same writes if
`INGEST_VIA_DOCKER=1` is ever used for an in-container ingest.

---

## D5. Stale `chunks.json` passes `check_state()` → ingest crash-loop

**Symptom.** With `INGEST_VIA_DOCKER=1`, `app-1` crash-looped on
`KeyError: 'gloss_keys'` (`ingest.py` `to_point()`), restarting via
`restart: on-failure:3`.

**Root cause.** `check_state()` (`scripts/startup.py`) returns `"ingest"`
whenever `data/processed/chunks.json` *exists* — it does not check schema
or version. The host's file predated v2's `build_chunks.py` rewrite
(`gloss_keys`/`primary_gloss_keys` added), so ingest read v1 chunks with v2
code.

**Fix.** `docker compose stop app`, `mv data/processed/chunks.json
~/chunks.json.bak` — with no chunks file, `check_state()` returns `"full"`
and the pipeline re-downloads, rebuilds (218,788 chunks), and re-ingests.
Two related traps surfaced here: `docker compose up -d app` recreates only
`app` (a qdrant-side config change needs an unscoped `up -d`), and `app`
reports `(unhealthy)` for the whole ingest — Streamlit only listens after
the pipeline finishes, so the healthcheck fails meanwhile; cosmetic, not
a fault.

**Permanent fix.** `build_chunks` now stamps `chunks.meta.json` (schema +
upstream generation dates) and `check_state()` only routes to `"ingest"`
when the sidecar says the current schema wrote the file — stale chunks go
to `"full"` and get rebuilt instead. A populated collection also gets an
incremental path: `check_state()=="ready"` still rsync-refreshes the EDRDG
XML, rebuilds only when the upstream generation date moved
(`outputs_current()`), and `ingest.run(update=True)` upserts new + edited
ent_seq ids (per-point `sig` payload, content hash) and deletes vanished
ones without dropping the collection — first run on a pre-sig collection
re-embeds in place once to install signatures.

**Hardened further (review pass).** A full ingest that dies mid-upload now
drops the partial collection (`try/except` in `run()`), so `count > 0` can
never masquerade as "ready" and serve silently truncated results — and as a
second net `check_state()` warns when the live count is below
`chunks.meta.json`'s `entries`. A populated collection missing
`kanji_table.json` gets a new `"build"` state (rebuild artifacts, never
touch the collection) instead of falling through to a destructive
re-ingest. Refresh soft-fails now record
`data/processed/refresh_status.json` (outcome + detail + timestamp) so a
run of silent refresh failures is inspectable rather than log-only, and the
two EDRDG rsyncs run concurrently. Kanji "common words" are ranked by
`is_common`/`commonness`/`wf_score` rather than JMdict document order.
The partial-count check compares against `ingest.meta.json` — the actual
post-run point count and scope stamped by `ingest.run()` — rather than the
full-corpus `entries` figure, so a `--common`/`--limit` deployment doesn't
warn on every boot; and the `"build"` branch re-fetches `data/raw/` via
rsync when the wipe took the XML too, so it self-heals instead of degrading
until the next full ingest.

---

## D6. Seeding the collection via snapshot instead of re-embedding

**Context.** Rather than wait ~1 h for the small VM to re-embed 218k
chunks, the already-built v2 collection was copied from the dev machine —
snapshot → file transfer → upload — using Option 1 (manual) rather than
`scripts/cloud_ingest.py` so the `.snapshot` file survives as a backup
artifact (~681 MB).

**Sequence.**

```bash
# source (dev machine): create + download
curl -X POST localhost:6333/collections/jmdict_chunks/snapshots
curl -O localhost:6333/collections/jmdict_chunks/snapshots/<name>
rsync -P -e "ssh -i <key>" <name>.snapshot ubuntu@<vm>:

# target: upload replaces the collection wholesale (partial ingest wiped)
curl -X POST 'localhost:6333/collections/jmdict_chunks/snapshots/upload?wait=true' \
  -F 'snapshot=@<name>.snapshot'
docker compose start app   # check_state → "ready" → straight to serving (uvicorn)
```

**Gotchas.** Oracle's Ubuntu base image has **no `rsync`** (`sudo apt
install rsync`, or use `scp`/`rsync` alternatives); Qdrant ports are
`127.0.0.1`-bound on both ends so all transfer went over SSH; the
collection shows `"status": "yellow"` briefly post-upload while the
optimizer runs — turns green on its own. Endpoint verified:
`points_count` parity between source and target, site serving normally.

**Status (2026-10-22).** Still the preferred path for full re-ingests,
now automated: `scripts/cloud_ingest.py` (snapshot → download with
sha256 → upload `?wait=true` → count verify) plus a cross-instance seed
step — `scripts/ingest.py --seed-from URL` transplants the cloud's
stored vectors onto fresh payloads, so a local build needs no
re-embedding before its snapshot. The runbook lives in
`Deployment.md` (*Updating the vector collection*).

---

## D7. `git pull` — `unable to create file data/processed/headword_index.marisa: Permission denied`

**Symptom.** Pulling `a7c1b0d` — which adds the committed 26 MB
`headword_index.marisa` — failed at checkout on that one path; every
other file in the merge wrote fine. A second `git pull` then refused
outright (`local changes … would be overwritten` plus `untracked working
tree files would be overwritten: app/headword_index.py`) even though the
host had no real local edits.

**Root cause — two layers.**

1. `data/processed/` (and `data/` above it) was `opc:opc` mode `775` —
   created when the `opc` user ran the ingest — while deploys run as
   `ubuntu`, which is not in group `opc` → read-only on the directory,
   so the new file could not be created. Same ownership class as D4,
   but host-side rather than inside the container. Every other path in
   the pull was already `ubuntu`-writable, which is why only the file
   under `data/processed/` failed.
2. A failed fast-forward leaves a **half-applied working tree**: HEAD
   stays at the old commit (`b1a3cdc`, "behind by 2") while the already
   written files show as *modified* and incoming new files show as
   *untracked* — so the retry is blocked by its own debris. And
   `git checkout HEAD -- <path>` can't recover the missing file: the old
   HEAD doesn't contain the path.

**Fix.**

```bash
sudo chown -R ubuntu:ubuntu data/processed   # repo-wide is safer
git reset --hard origin/main
```

`reset --hard` is the deterministic route here — the half-written tree
is already the incoming content, and the only genuinely untracked file
(`Caddyfile`) isn't in the merge set, so it survives. A plain `git pull`
also works after `rm app/headword_index.py`, but the reset is one step.
Verified: clean status, `.marisa` on disk, branch at `a7c1b0d`.

**Follow-ups.** This pull adds runtime deps (`sudachipy`,
`sudachidict-small`, `marisa-trie`) and a `COPY` of the `.marisa` into
the image — deployment needs `docker compose up -d --build`, not just a
restart. Prevention: keep the whole checkout owned by the user that
pulls (`sudo chown -R ubuntu:ubuntu .`), or share `data/` via a common
group with `g+w` if `opc` still needs write there.

---

## D8. `gcloud run deploy --source .` crashed — `ZIP does not support timestamps before 1980`

**Symptom.** Source deploy died at *Uploading sources* with a gcloud
`ValueError`; the log showed `Not using ignore file.` and paths like
`.local/share/Trash/files/venv/bin/python3.12` being zipped — nothing in
the repo itself was pre-1990.

**Root cause.** The command was run from `~`, so `--source .` meant the
home directory — gcloud zipped all of `/home/anks`, including Trash,
which preserves files' original (here pre-1980) mtimes, which the zip
format can't store. No ignore file was loaded because `.gcloudignore`
didn't exist yet.

**Fix.** Deploy from the repo root (`cd ~/REPO/Reikun`), and add
`.gcloudignore` mirroring `.dockerignore` plus repo-only extras (`web/`,
`docs/`, `eval/`, `tests/`, `.github/`) — keeps the Docker-required files
(`data/processed/` artifacts) while dropping the upload to ~10 MB.
Related gotcha surfaced the same day: a `git push` alone does **not**
deploy — no Cloud Build trigger exists; `gcloud run deploy` stays manual.

---

## D9. 0.8.0 retrieval scoring — canonical prior, headline-gloss prior, fusion cutoff

**Symptom.** The 0.8.0 branch measured **137/156 Hit@1** on the 156-query
gold set against the **139** recorded by the 17:07 baseline run (2026-10-21),
and the diff was not random: three gold queries regressed while two improved
— `library` 1→5, `to leave` 1→2, `sea` 1→2 against `phone` 3→1 and `table`
3→2. The baseline itself could not be reproduced from any reachable
configuration, so the gap had to be closed by *understanding* the formula
rather than replaying it.

**What was disproven (do not re-litigate).**
- fastembed-version / embedder drift — byte-identical embedding path; the
  3.13→3.14 venv switch was exonerated.
- Collection drift — vectors, payloads and index point-counts verified
  identical local↔cloud (犬, ワン子, 海, 水分, 水道, 鱒, 本, 時, 出る, 行く,
  図書館, 文庫, 電話; `sig` fields match). Cloud never received the 0.8.0
  payload refresh (the wedged re-ingest left only a cosmetic `infl_forms`
  residue index of 7,172 points).
- Query rewrite — `rewrite_query(...,'heuristic')` is method='none' for every
  contested query ("book", "library", "sea", "to leave", "time", "phone",
  "dog", "water").
- `gloss_keys`/`primary_gloss_keys` semantics across eras — HEAD and current
  `build_chunks.py` both append only sense-0 glosses ("first sense only"); the
  widening `primary_gloss_keys` sets were already in the baseline-era payload.

**The mechanism, decomposed per query.** Under the 4-arm fusion (dense, BM25,
BM25+exact, dense+exact) the fused base is a *rank* score, not a similarity:
a word the query matches exactly enters the exact arms deep — 本, the right
answer for "book", is dense >300, BM25 >300, exact 122 — so its fused
contribution is ≈0.016 and the formula's priors decide the rank. The gap
therefore has one shape: *the right entry is in the pool but a rival wins the
formula*.

| Query | Right answer | Rival that won | Mechanism |
|---|---|---|---|
| `library` | 図書館 | 文庫 | canonical 3×4.27 = 12.81 vs 3×2.73 = 8.19 (Δ4.62) — a gap no fused edge (≈1.0) can close; the baseline needed a base of ≈6.16, more than the maximum RRF contribution |
| `to leave` | 出る | 行く | canonical 16.56 vs 15.69 — 行く's *first sense* genuinely lists "to leave (for)" as its 4th gloss, so the primary filter fires for it too |
| `sea` | 海 | 鱒 | canonical 17.14 vs 15.27 — 鱒's primaries are ['sea','sea trout','trout']; the 'sea' key comes from the head-word expansion of "sea trout" |

Lowering the canonical boost does not save them (the fused edge is smaller
than the wf gap at every boost tested); raising the arm weights only moves
*which* rival enters the pool.

**Root cause — two independent defects.**

1. **The canonical prior answers the wrong question.** It asks "is the query
   one of the entry's first-*sense* glosses?" — but a sense can be a long list
   of secondary glosses, and `wf_score` then picks the entry whose *spelling*
   is common in a corpus, which is not the entry that *means* the word. JMdict
   orders a sense's glosses by centrality, so the first one is the headline
   translation: 行く lists "to leave (for)" 4th, 頼む lists "to ask" 3rd,
   鱒's gloss is "sea trout" — while 出る/問う/尋ねる/海 lead with
   "to leave"/"to ask"/"sea". A frequency prior cannot see that difference.
2. **The formula can only reorder what the fusion returns.** 時間, the right
   answer for "time", reaches the 4-arm RRF at rank ≈204 — it appears in the
   exact arms only (ranks ~127/~164) — so with the fusion cutoff tied to the
   per-arm cutoff (200) it sat exactly on the boundary and fell out of the
   pool on a tie. Nothing inside the formula can rescue a candidate that never
   reaches it.

**Fixes shipped (0.8.0).**

1. **`head_gloss_keys` — a new payload field** (`scripts/build_chunks.py`,
   `scripts/ingest.py`): the gloss keys of the *first gloss of the first
   sense* — the entry's headline translation. 215,565 of 218,786 entries
   carry it; the remaining 3,221 start with a parenthetical gloss that
   normalises to an empty key, so they hold `[]` and can never match by
   construction.
2. **`HEAD_BONUS × wf_score × head_match`** — a new term in the en_word
   formula, `HEAD_BONUS = 1.5`. Frequency-weighted like the canonical term (so
   a rare entry cannot ride a one-word gloss into the top 5) but gated on
   *headline* centrality: the canonical says "the query is what the entry
   means", this says "it is what the entry leads with".
3. **`FUSION_FACTOR = 2`** — the fused list is now twice the per-arm cutoff.
   The arms still fetch 200 each; the fusion returns 400, so a candidate that
   ranks deep in *every* arm (時間 at ≈204) still reaches the formula. It
   also removed a knife-edge: at 1× the boundary was a tie.
4. **`PREFETCH_MIN = 200`** — production now matches the pool the eval
   measures (it was 100, i.e. the eval and the API were never the same
   system).

**The formula that shipped** (`app/retrieval.py`, en_word route):

```
arms (limit = pool = 200 each)   →  Rrf() [all arms equally weighted]  →  FormulaQuery
  1. dense query              (w=1)        fusion limit = pool × 2 = 400    $score
  2. BM25-sparse query        (w=1)                                        + EXACT_BONUS × exact_filter         (= 1.0)
  3. BM25-sparse + exact      (w=1)                                        + COMMON_BOOST × commonness          (= 1.0)
  4. dense + exact            (w=1)                                        + HEAD_BONUS × wf_score × head_filter (= 1.5)
                                                                  + CANONICAL_BOOST × wf_score × primary_filter × commonness  (= 3.0)
outer FormulaQuery limit = num_results (5)
```

**Final numbers** — gold set, local seed Qdrant, `--no-llm`:

| | Hit@1 | Hit@2 | Hit@5 | median |
|---|---|---|---|---|
| 0.8.0 branch before this fix (233909Z: pool 200, fusion ×1) | 137 (87.8%) | 154 | 156 | ~17 ms |
| **shipped** | **149 (95.5%)** | **154 (98.7%)** | **156 (100%)** | ~17–30 ms |

The headline benchmark is `en_words + en_verbs + ja_hiragana` (156 queries) —
the three subsets the 137-vs-139 baseline comparison used. The full gold set
has 306 queries in six categories; the long-English `en_descriptive` set (50
paraphrases — "the vehicle that flies in the sky" → 飛行機) is a separate
rewrite-path suite and is excluded from the ranking benchmark (it scores
7/17 of 50 on Hit@1/5 — the criterion "expected headword in the top 5" is
brutal for a paraphrase). The other two categories (`ja_words`,
`ja_katakana`) are exact-lookup coverage and are at 100%.

**All 300 ranking queries** (en_words, en_verbs, ja_words, ja_hiragana,
ja_katakana — the whole gold set except the long-English paraphrase suite) on
the expanded 60-per-category gold set:

| subset | n | Hit@1 | Hit@2 | Hit@5 |
|---|---|---|---|---|
| en_words | 60 | 56 (93.3%) | 59 | 60 |
| en_verbs | 60 | 58 (96.7%) | 59 | 60 |
| ja_words | 60 | 60 (100%) | 60 | 60 |
| ja_hiragana | 60 | 58 (96.7%) | 60 | 60 |
| ja_katakana | 60 | 60 (100%) | 60 | 60 |
| **all** | **300** | **292 (97.3%)** | **298** | **300** |

The before/after comparison above was measured on the 256-query set that
existed before the gold set grew to 60 per category (original 0.8.0 → 237
Hit@1 → head term 247 → shipped 249). The 54 rows added since are harder
than the set average — 53 of them land at rank 1 — so the rate on the
expanded set is slightly lower than the old one, as it should be. The gold
file now carries a counting rule at the top: 60 per category, 360 total,
fixed, because the per-category rates are denominated by these counts and
every comparison above is stated against a fixed set size.

**Everything tried for score improvement** (all measured on the same gold
set).

*Rejected reshapes of the canonical prior:*

| Idea | Effect | Why rejected |
|---|---|---|
| `canonical × (1 + $score)` | fixes `library` | **destroys** the generic words: book→ブック, water→水道, dog→ワン公, time→度. The fused score measures *specificity* — compounds/katakana match the query's tokens precisely and take the highest RRF; the canonical exists to suppress exactly those |
| `canonical × (1 + k·$score)`, k = 2/3 | same as above | no k separates 図書館/文庫 (fused ratio 5.9×, wf gap 4.62) from ブック/本 (fused ratio 32×, wf gap 3.81) |
| `sqrt($score)` / `log10(1+$score)` in place of $score | — | the compression that lets 図書館 win on `library` (needs ≥2×) also lets ブック win on `book` |
| `log10(1+wf_score)` for the canonical | — | flips `time` to 度 (時 has 3 first-sense glosses vs 度's 2 — length normalisation favours the shorter sense) |
| `primary_gloss_keys` without the head-word expansion | fixes `sea` only | 鱒's 'sea' key came from "sea trout"; stripping the expansion also strips 'book' from 文庫's primaries and 'reading' from 書斎's. It is the *right* precision fix, but it is a payload rebuild for one query |
| second-gloss (`subhead_gloss_keys`) bonus | — | 終わる's "to finish" is its **3rd** first-sense gloss and 聞く's "listen" is a *separate sense*, so the second gloss cannot fix `to finish`; it would also promote 誘う/招く over 問う on `to ask` |
| head bonus × commonness | holds back the `to listen` regression (聞き置く is commonness 0) | costs the frequency weighting — measured 144 Hit@1 at 1.5 vs 147 for the plain wf-scaled term |
| head bonus × gate (0.7+0.3·commonness) | same idea | 0.7 is not enough to hold 聞き置く back (3.82 vs 3.28) |
| flat (non-frequency) head bonus | — | promotes rare compounds: 聞き置く (wf 0) overtakes 聞く on `to listen`; a flat bonus cannot fix `to ask` either (問う needs > 2.05) |
| `sqrt(wf_score)` head bonus | would flip `table` (表 21.24 vs テーブル 21.04) | only the frequency term separates them, and the frequency weighting is the point of the term |

*Sweeps actually run (real eval, `--canon 3 --pool 200 --common 1`):*

| HEAD_BONUS (fusion ×1) | Hit@1 | Hit@2 | Hit@5 | note |
|---|---|---|---|---|
| 0.0 | 137 | 153 | 155 | baseline at this width — `time` lost to the pool tie |
| 0.5 | 144 | 153 | 155 | |
| 1.0 | 147 | 153 | 155 | |
| 1.5 | 149 | 153 | 154 | `to finish` drops out of the top 5 (終わる pushed to #6) |
| 2.0 | 148 | 153 | 154 | same |

| FUSION_FACTOR | HEAD_BONUS | Hit@1 | Hit@2 | Hit@5 |
|---|---|---|---|---|
| 1 | 0.0 | 137 | 153 | 155 |
| 1 | 1.0 | 147 | 153 | 155 |
| **2** | **0.0** | 137 | 154 | 156 |
| **2** | **1.0** | **147** | **154** | **156** — shipped |

The two changes are complementary: the head bonus buys +10 Hit@1, the wider
fusion gives back the Hit@2/Hit@5 that the cutoff tie was eating. At
HEAD_BONUS ≥ 1.5 the head term itself starts costing Hit@2 (`to finish`), so
1.0 is the turning point.

*Offline screening.* Before paying for real evals, ~40 (coefficient × scaling)
combinations were screened with a Python re-ranker that takes the formula's
top-50 and re-sorts it with the bonus applied in-process (`head_gloss_keys`
read from `chunks.json`). It reproduced the direction and the turning point,
but it cannot see the pool boundary (it only re-ranks what the formula
already returned) — which is exactly why the real eval decides. Its absolute
H@2 numbers were optimistic by 1–2 points.

*Rank moves at the shipped config (HEAD_BONUS 0 → 1.5, gate = commonness):*
twelve queries to rank 1 — `family`, `happy`, `hot`, `sea`, `to ask`, `to
close`, `to help`, `to leave`, `to live`, `to stop`, `to teach`, `to want` —
plus `library` 5→3 and `to finish` 2→5.

**Simplification round — the same scores with fewer knobs.** The formula
above arrived with nine tuned constants: four RRF arm weights, EXACT_BONUS,
COMMON_BOOST, HEAD_BONUS, CANONICAL_BOOST, CANONICAL_GATE, plus the pool and
the fusion width. An ablation harness drove the *real* search path (rewrite →
route → arms → formula) over the gold set, patching one knob at a time.

*Ablations at the shipped operating point (gate = commonness, HEAD_BONUS 1.5,
uniform arms):*

| Variant | Hit@1 | Hit@2 | Hit@5 | Verdict |
|---|---|---|---|---|
| shipped formula | 149 | 154 | 156 | — |
| − EXACT_BONUS term | 149 | 154 | 156 | inert on the benchmark (kept — see below) |
| − flat COMMON_BOOST term | 148 | 154 | 156 | costs `to listen` — keep it |
| − EXACT_BONUS − COMMON_BOOST | 148 | 154 | 156 | same |
| − canonical term | 146 | 151 | 154 | essential |
| − head term | 137 | 152 | 156 | essential (+12) |
| canonical without wf_score | 145 | 152 | 154 | essential |
| head + canonical merged into one term | 144 | 153 | 155 | worse — keep them separate |
| canonical K = 2.5 / 3.5 | 149 / 148 | 154 | 156 | K = 3.0 is the peak |

*Knobs that turned out to be free:*

- **The commonness gate needed no floor.** The `0.7 + 0.3c` shape scored
  *identically* to plain `commonness` on every gold query — the second knob
  bought nothing, so the canonical term is now `CANONICAL_BOOST × wf_score ×
  primary × commonness` (an untagged entry keeps none of its frequency, a
  tier-2 one keeps half).
- **The RRF arm weights are irrelevant at this operating point.** Every shape
  measured the same 149/154/156: (1.05, 1, 2.5, 2), (1, 1, 2, 2), (1, 1, 1.5,
  1.5), (1, 1, 1, 1), (1, 1, 2, 1), (1, 1, 1, 2), (1, 1, 3, 1), (1, 1, 1, 3).
  The weights only decide which arm reaches the pool first; the priors decide
  the order. The arms are now fused with plain `Rrf()` — equal weights.
- **HEAD_BONUS wanted to be bigger.** Under the simplified gate the sweep is
  0.75 → 146, 1.0 → 147, 1.25 → 148, **1.5 → 149**, 1.75 → 149, 2.0 → 149
  but Hit@5 155 (`to finish` falls out of the top 5), 2.5 → 148, 3.0 → 147.
  1.5 is the turning point — the earlier 1.0 was chosen while the gate was
  still holding the untagged entries back.

*What the EXACT_BONUS term actually buys:* the top-5 comes back identical on
147 of 156 queries; the nine differences are all last-place swaps (e.g.
"garlic" offers ガーリックトースト with the term and パスタ without). It is
kept because it is the only term that fires for a query that is a *later*
gloss of an entry — neither first-sense nor first gloss — and it keeps those
tail results more relevant than the alternatives.

*The two queries the head term fixes are not benchmark noise but wrong
answers:* `to live` used to return 有る ("to be", wf 6.60) above 生きる ("to
live"), and `to want` used to return 要る ("to be needed", wf 6.66) above
求める ("to want") — pure frequency artifacts, now corrected by the
headline-gloss prior. `to finish` moves the other way (終わる's headline
gloss is "to end", so the gold's preferred entry slides from rank 4 to 5) and
stays inside the top 5.

**Remaining misses (honest ones).** Seven Hit@1 misses: `money` (2), `time`
(2), `table` (2), `library` (3), `to finish` (5), `かわ` (2), `ゆき` (2).
The two Hit@2 misses are synonym ambiguities, not retrieval failures —
`library` returns 文庫/ライブラリー/図書館 (all three are JMdict-valid
translations of "library"; the gold set prefers 図書館, whose corpus
frequency is lower) and `to finish` returns 仕舞う/済む/終える/終わる (all four
mean "to finish"). Both are rank-order judgements the formula has no signal
for, and both answers stay inside the top 5.

**Deployment notes.** `head_gloss_keys` is a new payload field, so the
collection must be refreshed before the API is deployed —
`scripts/ingest.py --update --reuse-vectors` rewrites the payloads from the
rebuilt `data/processed/chunks.json` without re-embedding (minutes).
`CHUNKS_SCHEMA` was bumped 3 → 4 so a stale chunks.json gets rebuilt instead
of ingested (`scripts/startup.py` `check_state()`), and the field sits in
`_INDEX_FIELDS` because Qdrant Cloud runs in strict mode and requires an
index on every field used in a formula condition.

---

# Segmentation & furigana issues — NHK Easy validation

Findings from four test batches of real sentences pulled from
[nhkeasier.com](https://nhkeasier.com/) (~140 sentences total, run through
`segment_japanese()` and compared against the site's own furigana). Headline
result: **zero wrong readings across all batches** — the furigana layer is
sound; every issue below is tokenization or gloss-selection.

---

## S1. Unresolvable token inside an inflection group crashed the whole parse → greedy garbage

**Symptom.** `日本でいちばん重いカボチャを決める大会が、香川県の小豆島でありました。`
parsed as `… でいち(でいち:mud) ｜ ばん(—:seal) … 小豆(あずき) ｜ 島(—:island)
｜ であ(であ:to be) ｜ ました(ました:right under)` — chips that are all real
but coincidental JMdict headwords (泥地, 判, 島, であ, 真下).

**Root cause — confirmed.** Sudachi's own tokenization was correct (`で`,
`いちばん`, `小豆島`, `で`, `あり`, `まし`, `た`). The failure was ours:
`_segment_sudachi`'s merged-chip loop indexed `seg["meanings"][0]`, and an
unresolvable member (`小豆島` — a place name absent from JMdict, glossed with
`meanings=[]` by design) inside the inflection group `[小豆島, で]` raised
`IndexError`. `segment_japanese()` catches exceptions and falls back to
`_segment_greedy`, whose longest-match walk then produced the fake
dictionary chips. One crash discarded a correct 19-morpheme parse.

**Prevalence.** ~4% of batch-4 (2/51 sentences) — the second victim
(`…8％です`, `％` unresolvable inside its group) produced *plausible-looking*
greedy output (`今`→"now") that passed eyeball review, so earlier batches
may contain more silent fallbacks. A greedy-looking chip set
(blank readings, dictionary-coincidental splits) is the signature.

**Fix.** Guard the index (`seg["meanings"] and seg["meanings"][0] not in
meanings`); unresolvable members still contribute surface+reading to the
merged chip and get a bare tooltip line (`小豆島` shows in the breakdown
with no gloss). Same latent pattern hardened in `_ambiguous`
(`e["meanings"][:1]` instead of `[0]`). Verified: `小豆島で` now even carries
Sudachi's own proper-noun reading `しょうどし`; batch diff shows 49/51
outputs identical, the two crash sites now correct.

**Why it was invisible.** `segment_japanese()` silently substituted greedy
output for the crashed rich parse — both return the same `list[dict]` chip
shape, and since greedy only emits *real* dictionary entries, every chip's
gloss looked legitimate (`今`→"now" reads as correct even while `でいち`→
"mud" is nonsense). Confident wrongness, indistinguishable downstream.

**Follow-up fix (applied).** `segment_japanese` is now three-tier: rich
Sudachi → `_segment_bare` (raw tokens, correct boundaries + readings, no
glosses — honest degradation, runs when the *post-processing* crashes) →
greedy (only when tokenizing itself fails), with greedy chips tagged
`"approx": True`. The UI renders those with a dashed border, an
"approximate —" tooltip prefix, and a "fallback segmenter" caption.
Verified by forced failure at each tier.

---

## S2. Contested kana surfaces picked wrong homographs

**Symptom.** `気をつけてください` led with 就ける "to install (a king)",
`いい` with 言い "what was said", `しかし` with 私窩子 "prostitute", `また`
with 股 "groin".

**Methods tried, in order.**

1. `_pick()` on lemma + reading only — insufficient: same-reading
   homographs (付ける/漬ける/点ける all つける) can't be split.
2. **Sudachi `normalized_form` as tiebreaker** — works where it exists
   (`いい`→良い, `しかし`→然し, `また`→又 each resolve to a unique entry),
   but over-resolves kanji surfaces (`来そう` picked らい "next year" over
   き "to come"). **Kept for kana surfaces only** — kanji stays ambiguous
   rather than risk a rare reading.
3. `is_common` tiebreak inside `_pick` — produced "a few wins and a few
   misses" (居る resolved, but a common-but-wrong homograph would also win
   silently). **Removed per review**: ties now always go to `_ambiguous`.
4. Current state: unique resolution (single reading match, or norm landing
   on one entry) commits; everything else renders all candidates,
   `is_common`-ordered, in the tooltip.

**Improved.** `いい`→良い "good", `しかし`→然し "however", `また`→又 "again",
`なっ`→成る, `でき`→"to be able to do" — all correct, all committed rather
than ambiguous.

**Still left.** Within a genuinely contested set the *first* gloss is just
index order — `ように` leads with 酔う "to get drunk" (the real よう-particle
uses are in the tooltip), `いました` leads with 射る "to shoot" over 居る,
`つけて` shows the four-way つける homographs without committing.

**Possible solutions.** Store `wf_score` (already computed in
`build_chunks`) in trie payloads and order ambiguous candidates by it —
highest-leverage remaining gloss fix, needs a trie rebuild; add
`_GRAMMAR`-style glosses for bound function forms (`よう`+助動詞語幹 →
"like ~ / in order to ~", `について` → "about ~" — **closed in #S6**) —
cheap but must respect
real noun uses (やりよう "way to do"); POS-aware candidate filtering.

**FIXED 2026-10-21 (the wf_score half).** `add_entry` now stores `wf`
(rounded Zipf) with every trie candidate and `_ambiguous()` orders by
`(is_common, wf)` instead of ingest order; the trie ships rebuilt
(27→30 MB) with the deploy. Ties beyond commonness+frequency are still
honest ambiguity by design — no silent first-pick.

---

## S3. Numeral + counter splitting

**Symptom.** `25日`, `3日前`, `17歳`, `7人です`, `2分4秒83` split into a bare
numeral chip + a counter chip glossed with the counter's *entry* reading —
contextually wrong (`日`→か where the word reads にち/みっか).

**Fix.** Numeral-`_num` markers fuse with a following counter-**headed**
group (`pos_sub2` carries the 助数詞可能 tag), so auxiliaries ride along:
`7人です` → one chip "7 · counter for people; polite copula". Counter gloss
prefers a "counter"-sense meaning (fixes `あと2日` → "2 · Sunday"); fused
chips carry no furigana — Sudachi's digit-by-digit readings are misleading.
Compound numerals normalise in the gloss (`2万1400` → "21,400",
`10万7677人` fused whole).

**Verified at scale.** `1.25%`, `0.25％`, `1点5%` (as `1点`+`5%`), `6.5m`,
`4ｔ`, `454.5kg`, `3万人`, `7914人`, `114歳`, `1つ`, `24時間` all fuse
correctly.

**Still left.** Contextual counter readings aren't recoverable from entries
alone (`25日` can't show にじゅうごにち without a counter-reading table);
`1日` resolves to the real entry ついたち "first day" where it's a headword
and to a fused counter elsewhere — inconsistent but defensible both ways.
Possible: a small `number×counter → reading` table for the ~20 common
irregulars (一日/二日/一人/二人/二十日…).

**FIXED 2026-10-21 (shipped in 0.7.0).** Both halves of the "still left":
1. Reading table `retrieval._counter_reading` — irregular num×counter
   readings (2日→ふつか, 13日→じゅうみっか incl. the composed tens rule,
   14日→じゅうよっか, 20日→はつか, 1人→ひとり, 2人→ふたり, 4人→よにん,
   4時→よじ, 20歳→はたち, 10分→じゅっぷん…). Untabled combinations keep
   reading "" — no furigana over one that would be wrong. The counter's
   inflection tail (7人です) joins the tabled reading so ruby covers the chip.
2. Counter alias `_counter_alias` — digit-typed counter queries (25日, 1人,
   4時) convert to the kanji spelling and search THAT when it's a real
   headword (`25日`→`二十五日` ✓, `1人`→`一人` ✓), so bare queries land the
   actual entry cards (ふつか/にじゅうごにち/ひとり) instead of BM25 noise.
   Non-headword combos (25kg) fall through to the fused chip. Rewrite is
   surfaced with `method="counter"` in `Rewrite`/`RewriteInfo`.
Both covered in `tests/test_segmentation.py` (48 tests).

---

## S4. `で` glossed as "casual copula" after nouns

**Root cause.** Lexical ambiguity, not a bug: `で` is both the case
particle ("at/by means of") and the continuative of copula `だ`. Sudachi
commits to the 助動詞 parse at clause boundaries — usually wrong for
`場所で`/`鍋で`-type noun+で.

**Fix.** `lemma=だ ∧ surf=で` glosses both readings:
"casual copula (continuative) — or で at/by-means-of particle". Honest for
`静かで` (copula) and `場所で` (particle) alike — one impossible-to-fake
ambiguity where showing both beats guessing wrong.

---

## S5. Genuine Sudachi mis-splits (upstream, not ours)

Verified by raw `tokenizer().tokenize()` on the exact strings — these never
reach our logic wrong, the tokens *are* wrong:

- `力ではかりにのせる` → `は`+`かり` (秤 split; context-dependent, the bare
  `はかりに` parses fine).
- `土曜日ごろ` / `日曜日ごろ` → `土曜`+`日ごろ` — Sudachi's dictionary
  prefers the real entry 日ごろ "usually" over 曜日+ごろ.
- `岸本ふよさん` → `ふ`+`よさ`+`んです` — rare given name absent from the
  dictionary; fragments then resolve to stray entries (ふ→二 "two",
  よさ→良さ "merit").

**Possible solutions.** sudachidict-full (richer named-entity coverage;
cost: bigger dictionary, still no guarantee on rare names); JMnedict merge
(~742k names — see data-source section below; fixes *glosses*, not the
split); suppress glosses on single-mora kana fragments adjacent to
固有名詞-tagged tokens (risky — could hide real parses); user dictionary
for recurring strings. None currently worth the added complexity.

---

## S6. Katakana names resolving to coincidental kanji entries; conjunctive collocations split into literal pieces

Surfaced on `彼女はジョンの勇敢さに感服している`, then stress-tested on 15
random Tatoeba sentences plus 10 random katakana-bearing ones.

**Symptom 1 — names get wrong glosses.** `ジョン` resolved to 煎 "jeon"
(the katakana is that entry's *reading* key, so the trie hit is real —
but it's a coincidence; John isn't jeon). Same class: `ジョー`→"jaw",
kanji surnames (`林`→"woods" for Hayashi). **Fix:** tokens Sudachi tags
`固有名詞/人名` skip the index lookup entirely — person names aren't
JMdict headwords (names live in JMnedict, not indexed), so any hit is a
homophone. The chip stays bare (surface + reading, no gloss) rather than
claiming "personal name" — the POS tag isn't proof enough for a label
either. **Deliberately not generalised** to "katakana never matches
kanji": real katakana words resolve via kanji headwords *correctly* and
often (ネコ→猫, カナダ→加奈陀, ページ→頁, タバコ→煙草, アメリカ→亜米利加
— verified against the corpus). Only the 人名 slice is reliably
coincidence.

**Latent fix in the same pass.** `_pick` compared the morpheme's hiragana
reading verbatim against katakana index readings — `じょん` never equals
`ジョン` — so katakana surfaces could *never* be disambiguated by reading
(`カラス` rendered an ambiguous 3-option chip instead of 烏 "crow"). Now
compares `_hira()`-normalised readings; only affects katakana lookups
(kanji-surface readings are hiragana on both sides already).

**Symptom 2 — conjunctive collocations misglossed.** `燃料のコストとともに`
parsed `と` "and" + `とも` "companion" + `に`; `確保について` parsed `に` +
`つい` "to take (a seat)" + `て`. Sudachi decomposes these into real
morphemes (they *are* historically particle+verb-stem+て), but as units
they're grammar: "together with ~", "regarding ~". **Fix:**
`_COLLOCATIONS` — a joined-surface table fused over consecutive
single-morpheme chips before compound rescue. The single-morpheme
requirement is the disambiguator: in `道についてくる` the て is flagged an
ending part and merges into the `ついてくる` group, so no chip sequence
matches `に+つい+て` and the real verb survives. `として` additionally
skips fusion after a volitional verb (`行こうとして` = "trying to go",
not "as ~"). Table covers とともに/と共に, ともに/共に, という/と言う,
について/に就いて, によって/に依って/に因って, により, によれば, にとって,
に対して, に関して, に比べて, に応じて, として. Deliberately excluded:
において (ambiguity with literal 置く "place on" is unsolvable by shape),
では/にも/のに (genuinely ambiguous particle stacks). This closes the
`について → "about ~"` item listed in S2's "Still left".

**Symptom 3 — right sense truncated out of the data.** `エンジンを吹かす`
glossed "to smoke" — the chunk carries "to rev (an engine)" at sense #4
but `add_entry` stored `meanings[:3]`, so no UI layer could ever show it.
**Fix:** index cap 3→5 (`headword_index.py`) + trie rebuilt (~26→27 MB,
+4% — still trivially mmap'd); merged-group hover lines show up to 4
senses for a morpheme (`吹かし→吹かす` line now reaches "to rev"), and the
group's visible 2-gloss summary drops the conjunctive-て filler "particle"
so the informative subsidiary gloss isn't evicted (`言ってあげる` was
"to say; particle", now "to say; ~ for someone"). Genuine resolution of
"context picks a minor sense" would need WSD — out of scope; this makes
the right sense *reachable* in the tooltip.

**Still left.** `ように` still leads with 酔う "to get drunk" (S2's
known homograph-ordering gap — the real よう-particle uses are in the
tooltip); sense *ordering* inside a stored entry is JMdict's, unchanged.

---

## S7. Reported headword-search misses (tomato / garlic / eraser / じてんしゃ / potato / apartment)

**Symptom.** User-reported top-1 misses on the search page, 2026-10-21:
`garlic` → に文字 (a near-nonword; 大蒜【にんにく】 was 2nd), `eraser` →
字消し over the everyday 消しゴム, `じてんしゃ` → 次点者 ("runner-up")
over 自転車, `apartment` → マンション with アパート 4th. tomato/potato/
家族 were already correct at re-report time (kept as gold-set regression
guardrails).

**Diagnosis (per-query formula math, probe read-only).** Two distinct
mechanisms:

| Query | Culprit entry | wf_score | commonness | Why it won |
|-------|--------------|----------|------------|------------|
| eraser | 字消し | 3.43 | 0.0 | canonical = 3×wf×primary out-ranked 消しゴム (3.35/1.0) by **0.02** — pure wordfreq noise |
| garlic | に文字 | 4.02 | 0.0 | inherits a particle's frequency (wordfreq ja lexicon gaps for kanji words; same family as 護謨 4.18 for rubber) |
| じてんしゃ | 次点者 | 2.15 | 0.0 | the **ja route had no formula layer at all** — BM25-RRF is frequency-blind, so any homograph matching the reading ranked by BM25 only |
| apartment | マンション | 4.32 | 1.0 | アパート's first sense is 2-word-phrase-glossed ("apartment building"), so bare `apartment` never matched `primary_gloss_keys` — canonical never fired for it; マンション has a one-word gloss and did |

wordfreq-Shim noise is a known property (護謨 4.18 stored vs 1.06
re-computed under a different Sudachi dictionary — tokenizer drift), so
JMdict's own tiering must gate it, and homographs must not reach the
user via rank order.

**Fixes (2026-10-21, two formula changes — no re-ingest needed for
either, payloads already carry `wf_score`/`commonness`):**

1. **Canonical gate** (`app/retrieval.py`): `CANONICAL_BOOST × wf_score ×
   first-sense × (0.7 + 0.3·commonness)` — shared by both routes via
   `_canonical_terms()`. An untagged (commonness 0) entry keeps 70% of its
   wf_score. eraser → 消しゴム, garlic → 大蒜, and the same margin that had
   消しゴム losing by 0.02 now has it winning by ~0.85.
2. **Formula layer on the ja route**: the RRF-fused BM25 pool now runs the
   same FormulaQuery (COMMON_BOOST + canonical rule). じてんしゃ →
   自転車 with 次点者 back where it belongs (5.7 vs 15.8).

3. **apartment is ingest-side**: `_gloss_head_words()` in build_chunks
   adds the head word of every ≥2-word gloss ("apartment building" → also
   "apartment", verb-gloss "to …" openers exempt) to `gloss_keys` AND
   `primary_gloss_keys` — canonical then fires for アパート too. Live
   after the next re-ingest. マンション remains a legitimate Hit (its
   JMdict senses genuinely include "apartment"); expected order is
   アパート ≈ マンション top-2.

**Gold-set results.** `eval/gold_set.tsv` gained tomato/garlic/eraser/
potato/apartment (en_words) + じてんしゃ (ja_hiragana). Full benchmark
156 queries: Hit@1 139/156 before AND after (the batch adds 2 gold rows
and fixes those two; no cross-query regression) — but the ja half of the
set reordered wholesale for the better (せんせい→先生 first, びょういん→
病院 first, いえ→家 first …). Top-3 churn outside ja: かわ/ゆき only
(still hits).

**Still left.** family/money/time/happy/hot + 5 en_verbs — the long-known
diluted-entry pattern (a minor sense of a frequent kanji entry carries
the gloss and beats the dedicated word; WSD-shaped, out of scope); かわ/
ゆき first-choice jitters are honest homographs.

---

# SvelteKit frontend issues

Post-migration issues in the SvelteKit frontend (`web/`) — both are
regressions from the post-launch polish pass.

## W1. KanjiCard replay button dead after adding the practice grid

**Symptom.** The stroke-replay button stopped responding right after the
dashed practice-grid lines were added behind the stroke SVG.

**Root cause.** The first implementation gave the SVG `position:
relative` to paint it above the grid pseudo-elements — which also put it
above the replay button (both positioned → DOM order decides, and the
button precedes the SVG in markup). The SVG silently covered the button's
hit area.

**Fix.** Inverted the approach: the `::before`/`::after` grid lines get
`z-index: -1` (sinking behind the in-flow SVG — strokes have no fill so
the grid still shows through) while the button stays unpositioned on top.
Lesson: when layering inside a card, push decorations *down*, not content
up — lifting content reorders everything relative to controls.

---

## W2. Kanji click "does nothing" — card mounted off-screen

**Symptom.** Clicking a kanji deep in the results list looked dead — no
feedback at the click point.

**Root cause.** `KanjiCard` actually mounts instantly (loading skeleton:
glyph + spinner, since `kanjiChar` derives from `committed` before the
fetch resolves) — but at the top of the page while the viewport stayed at
the click position, so nothing changed on screen.

**Fix.** An anchor `div` around the card + `$effect` on `kanjiChar` →
`scrollIntoView({behavior:'smooth'})`, with `scroll-margin-top: 4.5rem`
clearing the sticky search bar. Two subtleties: re-picking the *same*
kanji can't refire the effect (value unchanged) — that path scrolls
imperatively inside `commit()`; and an earlier dedup flag failed because
a plain `let` reset doesn't retrigger `$effect` — only `$state` deps do.
Deep links (`?q=海`) get the scroll for free via the same effect.

---

## W3. Final-review pass — astral kanji, SSE framing, a11y, OLED default

Full review of `web/src` (CSS/TS/HTML/Svelte) before handoff. Everything
below was found by reading, not reported in the wild; all fixed in the
same pass. `svelte-check` 0 errors/0 warnings, `vite build` clean.

- **Astral-plane kanji broken in three places.** Svelte 5's
  `{#each text as ch}` iterates UTF-16 code units, so CJK Ext-B kanji
  (U+20000–U+2A6DF) rendered as lone surrogate pairs in
  `KanjiText.svelte` — fixed with `{#each [...text] as ch}`. The
  kanji-card gate in `+page.svelte` checked `v.length === 1`, rejecting
  the same characters (they're one code point but two code units) —
  now `isKanji(committed)` directly. `typewriter.svelte.ts` slices via
  `Array.from()` for the same reason.
- **SSE parser assumed LF framing.** `explainStream()` split events on
  `\n\n` only; a proxy emitting `\r\n\r\n` would wedge the stream —
  parser now accepts both with chunk-boundary safety.
- **Tooltip self-dismissal.** Clicking/selecting text inside an open
  segment-chip tooltip bubbled to the window click handler and closed
  it — `e.stopPropagation()` on `.seg-tip`.
- **Form/a11y semantics.** `type="button"` on buttons that could act as
  implicit submits (`Feedback`, `Header`, `StrokeSvg`, search pills,
  show-more); `aria-label` on icon-only controls; per-query `<title>`
  via `<svelte:head>` in `+page.svelte`.
- **OLED is the deliberate default dark theme.** System-dark resolves to
  `oled` (not `dark`) in both the `app.html` first-paint script and
  `theme.svelte.ts` — now pinned by explicit comments in both files so
  it isn't "fixed" back to `dark` later; legacy `amoled` values migrate
  to `oled`; dark `theme-color` set to `#000000`.
- **Duplicate dynamic imports.** `ExampleRow.svelte` caches the
  marked/DOMPurify loader promise so concurrent explains share one
  import.

---

# Completed items (folded from Plan.md)

Done work moved out of the TODO backlog. Structural details live in
`Architecture.md`; this is the record of *what* shipped and *why*, in the
order `Plan.md` tracked it. Items whose full story is already an issue
entry above are referenced, not repeated.

## Branding & small fixes
- Logo shipped — `docs/logos/icon-rei-lens.*`; runtime copy at
  `app/assets/logo.png`.
- License: Apache-2.0 (`LICENSE`) + `NOTICE` for data attributions.
- "Press Enter to apply" hint removal — **won't do**: no display toggle
  in Streamlit 1.64; the only lever (`live=`) changes commit semantics
  (`Issues_old.md` #U11). Moot anyway post-migration.
- Kana exact-match false warning — the check now covers `reading` +
  `entry_forms` variants, not just `kanji_form`; しごと→仕事 no longer
  warns.

## Migration — Streamlit → SvelteKit

### Phase 0–1: safety net + standalone API
- Tagged `v0.2.0-streamlit`; Qdrant snapshot
  `jmdict_chunks-…-2026-10-03` (683 MB, 218,786 pts) downloaded to
  `data/snapshots/` (gitignored).
- `uvicorn app.api:app` is the container entrypoint (`reikun` →
  `startup.py` execs it; `asgi_app.py` deleted). `startup.py` only
  serves — ingestion sits behind `--ingest` / `--ingest-only` /
  `INGEST_VIA_DOCKER`.
- Config entirely via env; `/health` dependency-free liveness, `/ready`
  does a real Qdrant count+scroll (503 until populated).
- Rendering moved into JSON via `app/render.py`: `ruby` parts on results
  and segment chips (`{text, kanji_form, reading, meanings, gloss, ruby,
  options, approx}` under top-level `segments`), `meta`/`readings`/ruby'd
  `common_words` on `/kanji/{char}`, `GET /kanji?chars=…` batch hovers,
  `?strokes=true` → `{view_box, strokes, numbers}`.
- `scripts/export_openapi.py` → committed `docs/api/openapi.json`;
  `openapi-typescript` → `web/src/lib/openapi.d.ts`.
- Telemetry behind `app/telemetry.py`: `TELEMETRY=stdout` JSON lines
  (stateless default) or `=sqlite` (`scripts/feedback_log`).
- Slim image: streamlit/pandas/altair out — 627 MB, non-root uid 1000,
  one uvicorn worker, models/ONNX/Sudachi lazy + lifespan-warmed.
- Cold start measured (container → Qdrant Cloud): `/health` ~3.56 s →
  `/ready` ~4.0 s → first `/search` ~4.1 s → second ~76 ms; bare-process
  import ~1.2 s — dominated by interpreter+import, not model load (ONNX
  warms on daemon threads at lifespan; first-search embed ~5 ms).
- Worker note carried over: one process per instance — embedding and
  Sudachi are CPU-bound, so keep endpoints plain `def` (threadpool) and
  let the platform scale by instances; tune `--concurrency` (4–8/vCPU).

### Phase 2–3: SvelteKit frontend + hosting
- Ported feature-for-feature: search box + example pills, ruby/furigana +
  kanji hover cards (batch `/kanji`, microtask-coalesced), "parsed as"
  chips, kanji card (stroke animation + meta badges + readings + common
  words), streamed JLPT explanations (marked + DOMPurify lazy chunks),
  thumbs feedback, stats line, too-long/not-a-headword/nothing-found
  states, show-more pagination, theme picker, KB status dot.
- URL-driven: `?q=`/`?level=` drive everything (+ legacy `?kanji=`
  redirect, stale-response guard). adapter-static SPA (`index.html` +
  `200.html` + prerendered `/about`; `vercel.json` kept for the Vercel
  backup path).
- SvelteKit 3 specifics: config in `vite.config.ts` (no `svelte.config.js`);
  package `imports` `#lib/*` replaces `$lib`; `src/env.ts` replaces
  `$env/*` for `PUBLIC_API_BASE`.
- Shipped: API on **Cloud Run** `reikun-api` (europe-southwest1, 1Gi,
  min 0/max 3, `--source .`, Qdrant/Groq via Secret Manager); frontend
  on **Cloudflare Workers static assets** (`web/wrangler.jsonc`) — the
  Pages Git-integration plan was superseded by the merged Workers
  dashboard. Deploy stays manual — no Cloud Build trigger; `.gcloudignore`
  added after the from-`~` ZIP crash (D8). CORS: `*.workers.dev` +
  `reikun.app`.
- `reikun.app` cut over to the CF Worker — zone moved from name.com (CF
  nameservers at the registrar), imported A-record conflict resolved by
  deleting the auto-imported VM records in CF DNS, custom domain attached
  under the Worker's Domains & Routes. Oracle VM (`docker compose stop`)
  retained as frozen backup — volumes intact for rollback.

## Cleanup & hardening (Phases 4–5)
- Streamlit tree removed: `app/ui/`, `streamlit_app.py`, `.streamlit/`,
  the `ui` dep group, `load_table` — `web/` is the only frontend.
- Telemetry rework: searches store raw `query`/`rewritten_query` +
  `rewritten` flag alongside `*_hash` fields (raw logging re-enabled for
  the debug phase), plus `route`/`embed_ms`/`retrieve_ms` columns;
  feedback + explanations stay hash-only; `TELEMETRY_RETENTION_DAYS`
  removed — rows kept forever; footer carries a one-line privacy note.
- CI (`.github/workflows/ci.yml`): backend — ruff, pytest (no
  Qdrant/Groq needed), `openapi.json` drift via `git diff`; frontend —
  `npm ci`, svelte-check, vite build, `openapi.d.ts` drift via pinned
  `npx openapi-typescript@7.13.0` (kept out of deps — its peer wants TS 5,
  project uses TS 6). `contents: read` least-privilege + `concurrency`
  cancel-in-progress.
- KanjiVG strokes packed: `scripts/download_kanjivg.py` pre-extracts
  `{view_box, strokes, numbers}` into committed
  `data/processed/strokes.json` (~6,416 diagrams); the runtime GitHub
  fetch and the raw `?svg=` response are gone — a missing diagram is a
  normal absence, not a network call.

## Fixes & decisions closed out
- LLM provider switch — Cohere → **Groq-only** (Nov 2026). `grammar_explain.py`
  now uses the `groq` SDK: `openai/gpt-oss-120b` primary → `openai/gpt-oss-20b`
  fallback (independent per-model RPD pools), `reasoning_effort="low"`
  replacing `thinking_budget`, 429s honor `retry-after`, truncated/empty
  responses retry with 1.5× budget. Total failure raises "Grammar explanation
  service is down (models tried: …)" → /explain 502 / SSE error event.
  `last_model()` reports whichever model actually served (telemetry, /ready).
  `cohere`/`google-genai` dropped from deps entirely — the multi-provider
  comparison script lives at `local/llm_compare.py` — the whole `local/`
  tree (script + reports) is gitignored.
  Env is `GROQ_API_KEY` + optional `LLM_MODEL`/`LLM_MODEL_FALLBACK` overrides.
  Picks settled by judged A/B (`local/results/llm_compare_r2.md`, `r3.md`):
  120b beat Cohere under both a self and a neutral (gemini-3.5-flash-lite)
  judge at ~2× speed; qwen3.8-27b/gemma-4-31b/gemini-3.8-flash rejected on
  latency/reliability/quota. English `Meaning:` kept in prompts (−0.5–0.8
  acc without it). gpt-oss sometimes writes N1–N3 explanations in Japanese —
  `_BASE_RULES` now pins "all explanatory prose in English … even at N1"
  since the JA drift was inconsistent (random, not level-conditional).
- Explanation cache — **dropped**: ~32k sentences × 5 levels is too large
  a space for a useful hit rate, and a cache needs storage +
  prompt-version invalidation. `cache_key()`/`PROMPT_VERSION` were
  removed from `grammar_explain.py`; if quota ever binds, prefer per-IP
  rate limiting on /explain over caching.
- `api.reikun.app` Cloud Run domain mapping — **skipped**: the run.app
  URL in `PUBLIC_API_BASE` works indefinitely; a vanity API hostname
  would only be worth it if CF Access is ever wanted in front of /admin
  (Access needs the API hostname on the CF zone).
- Long-Japanese-input inconsistency: `MAX_QUERY_CHARS=150` (raw, any
  language) and `MAX_JA_QUERY_CHARS=100` (post-rewrite) reject before
  embed/retrieve; `meta.too_long` → a real "too long" UI warning instead
  of misleading "Nothing found". Common particles (の/は/に/を) now gloss
  from a small grammar table instead of wrong single-kana headwords.
- Kanji page overhaul (Streamlit era): titled sections, meta-badge
  tooltips, 音読み/訓読み ruby labels, okurigana chips, common-word deep
  links; `?kanji=` → single-kanji search.
- JLPT-aware random button: shuffle + JLPT selector as separate bordered
  tools at the search bar's height/padding; `/kanji/random?level=`
  honours the pick (headword-filtered pool — see §3.2 for the
  candidate-tries trick that fixed the first-click stall, `Issues_old.md` #U8).
- Dashboard-privacy DECIDE — resolved by deletion: the whole Streamlit
  dashboard went away in Phase 4 (option (a) won by default).
- Demo video format: 9:16 portrait chosen for TikTok/Shorts/Reels.
  Re-recorded in true 9:16 — `demo_v4.mp4` (1920×1080) +
  `demo_v4_vertical.mp4` (1080×1920 native, `--portrait`), script now
  targeting the SvelteKit selectors; `demo_v3_cropped.mp4` (768×1080
  letterboxed) superseded. Gotcha learned: the viewport must EQUAL
  `record_video_size` — Playwright never upscales, a smaller viewport
  pastes 1:1 and pads grey (the 900×1600→1080×1920 idea produces a grey
  band).
- Post-launch UI polish: wider column (56 rem); frosted translucent
  sticky bar (backdrop-blur; input + tools translucent); accent reserved
  for the submit button — monochrome everywhere else, kanji tips =
  dotted underlines; compact kanji card (specs under the animation,
  dashed practice grid, larger glyphs/furigana); seg chips + glosses
  enlarged; right-aligned ⓘ stats cluster; scroll-to-card on kanji pick;
  typewriter placeholder that types → holds → backspaces → repeats.
  Regressions logged as W1/W2; final-review findings as W3.
- Sudachi `hint` wired into explanations: `retrieval.morph_hint()`
  emits one `surface → lemma (POS, conjugation)` line per morpheme;
  `/explain` + `/explain/stream` pass it as `<analysis>` (capped at
  `MAX_HINT_CHARS`) so the LLM stops guessing conjugated forms.
- Python 3.13 pass over `app/` + `eval/` + `tests/`
  (`local/skills/python313` checklist): `@lru_cache(maxsize=1)` →
  `functools.cache` on all process-wide singletons
  (`qdrant_client`, `dense_model`/`sparse_model`, `_tokenizer`,
  `_groq`, `telemetry`, kanji/stroke loaders); `Literal.__args__` →
  `typing.get_args` in `api.py`; `MappingProxyType[str, object]` +
  `tuple[str | None, ...]` + `SparseEmbedding` annotations tightened;
  `Field(min_length=1)` drops the redundant `...`; redundant `noqa:
  E402` stripped (ruff auto-fix). `ruff check` + `pytest` (34 tests)
  green on Python 3.13.15.

---

# Data-source reference & follow-ups (moved from Plan.md)

Reference material plus data sources and follow-up ideas not yet pulled —
kept here so `Plan.md` stays a pure TODO backlog. For the as-built anatomy
of the two files actually consumed see `Architecture.md` §1.4.

**Pipeline reference**
- Upstream chain: `yamagoya/jmdictdb` (PostgreSQL DB where JMdict is maintained; emits the daily XMLs) → JMdict_e / JMdict_e_examp / JMnedict / kanjidic2 exports — consumed directly since the XML migration (the `scriptin/jmdict-simplified` JSON step is retired); going further upstream only un-flattens fields the exports drop (xref links, POS detail).
- Licence (verified at edrdg.org/edrdg/licence.html): all EDRDG dictionary files — JMdict (+NG), EDICT/edict_sub, JMnedict/enamdict, COMPDIC, KANJIDIC2 — are **CC BY-SA 4.0**: (a) derived data (`chunks.json`, `kanji_table.json`, Qdrant payloads) is ShareAlike; (b) the app must show an acknowledgement (per-screen, or an About/Sources page); (c) data must be kept regularly updated — the daily rsync in `download_edrdg.py` (generation date in `.meta.json`) aligns. `examples.utf`/Tatoeba content is **CC-BY** (attribute tatoeba.org). KANJIDIC2 embeds third-party material (SKIP/Halpern, Four Corner/Morohashi, De Roo) retaining its own copyright. Domain glossaries, freq lists, `kradfile2` (Jim Rose), `sod-*`, KanjiVG, WaDoku/JR-EDICT have their own terms — check per file. No commercial-use restriction; no warranty.

**EDRDG files** — all from `ftp.edrdg.org::nihongo/` (rsync module) unless noted; dict files regenerate daily, everything else is frozen. Pull one by adding it to `WANTED` in `download_edrdg.py` (see `Architecture.md` §1.3 for the sync mechanics).
- Follow-up: collection refresh via incremental diff (upsert changed `ent_seq`s, delete removed) instead of full-snapshot swaps — see `Deployment_old.md` (*Updating the cloud collection*).

**Skipped**
- `edict_sub` (22k common words) — NG's pri/nf markers cover it.
- `sod-*` stroke-order GIFs — first 1,000 kanji only; local KanjiVG has 6,413.

  > **Researched — nothing beats KanjiVG for Japanese stroke order; coverage gap is closable via fallback chain.** KanjiVG (CC BY-SA 3.0, 6,413) is the upstream Jisho/Kanimaji/stroke-order-font all reuse. `kanji_table` has 13,108 kanji, so ~6.7k lack stroke data. Measured candidates:
  > - **AnimCJK** (github.com/parsimonhi/animCJK) — `svgsJa/` 7,007 files = jōyō 2,136 + jinmeiyō 863 + hyōgai + components + 38 strokes; covers **6,483** of the old 10,384-kanji table (+374 over KanjiVG — but symmetric: KanjiVG has 306 svgsJa lacks, mostly 金-radical hyōgai). NOT KanjiVG-derived: it's makemeahanzi-derived (Arphic font lineage) with years of independent Japanese corrections (stroke order/glyph/direction) cross-checked vs Kakijun/Jitenon/Moji kakudai/KanjiVG — changelog very active (hundreds of hyōgai added 2025–26). Format: **self-animating SVGs** (filled stroke shapes as clip-paths + dashed median paths, inline CSS; works as `<img>` or inline, no JS) — but **no stroke numbers** by default (setNumbersAcjk.js adds them); 1024×1024 viewBox; filenames are **decimal** codepoints (`20013.svg` vs our hex `4e2d.svg`); 199 non-BMP files exist; watch compatibility chars (same glyph under multiple codepoints, e.g. 勉 21193 vs 64051). `graphicsJa.txt` also ships in makemeahanzi single-file format. Bonus: `svgsJaKana/` 177 kana stroke SVGs (KanjiVG has none) and `dictionaryJa.txt` "acjk" radical decompositions (relevant to §Kanji decomposition). License: kanji SVGs + `graphics*` = **Arphic Public License** (permissive, DFSG-free; derived data stays Arphic + notice); kana SVGs + dictionaries + scripts = LGPL.
  > - **Make Me a Hanzi / hanzi-writer-data** — 9,574 chars, **Arphic PL**, +1,664 of the missing kanji (1,357 beyond AnimCJK). Caveats: **PRC stroke order** (differs from Japanese on 必, 左/右 top, etc.) and Chinese kai glyph shapes (直/骨/与) — fine as rare-kanji fallback, wrong as primary. `hanzi-writer-data` = per-char JSON on jsDelivr (`strokes` are filled outlines + `medians` centerlines — needs median-stroke or clip-path animation, not our `pathLength` dash trick).
  > - Combined chain KanjiVG→AnimCJK→makemeahanzi covered **8,146/10,384 (78%)** of the old table; the remainder are rare Ext-A/JIS X 0212 kanji with no permissive source.
  > - Rejected: Kanji-alive (1,235 only, no dataset redistribution), **Taiwan MOE 筆順學習網** (6,063 chars, bulk SVG download offered — but **CC BY-NC-ND 3.0 Taiwan**: non-commercial + no-derivatives kills recolor/re-encode and commercial use; g0v/zh-stroke-data scrape inherits it), Commons Stroke Order Project (patchy, per-file licenses), cnchar/zi.tools (20k+ but provenance dubious, scraped fonts).
  > - AnimCJK's own cross-check references are *not* datasets: kakijun.jp, kanji.jitenon.jp, moji.tekkai.com, ArchChinese, Qianpian, Naver Hanja, HK-EDB are all proprietary view-only sites; Wiktionary stroke-order images are Commons files largely KanjiVG-derived anyway; OpenCC is Apache-2.0 but a script-conversion table, not stroke data. They explain how AnimCJK verified Japanese correctness — none is an additional source we can pull.
  > - If implemented: keep Arphic-derived files in a separate dir from `data/kanjivg/` (different license), add Arphic attribution next to the KanjiVG credit in `common.py`.
- `JMdict_e_examp` (classic XML) — superseded by the NG examp variant; same data, richer schema.
- `examples*` standalone files — embedded in the examp variant (`examples.utf` stays interesting as *backfill*, see below).

**Proper names**
- `JMnedict.xml` / `jmnedict-all` asset — ~742k names (people, places, stations, orgs). Same entry schema as JMdict — mergeable as chunks via the XML build path.
- `enamdictx` — name readings grouped with frequency ordering.
- `oneill.lst` — kanji appearing in Japanese names (O'Neill).

**More example sentences**
- `examples.utf` — 147,836 jpn↔eng pairs indexed to JMdict entries (~5× the embedded ~30k). Backfills examples for entries like 縞馬. `examples_s` = representative subset, `tanakacorp_utf8` = original uncleaned file.

**Kanji decomposition & stroke**
- `radkfile` / `kradfile` / `kradfile-u` — kanji→radical decompositions (~13k kanji, JIS208+212+213) → "find kanji by components" search. Licence note: kradfile2 files are Jim Rose's, different licence.
- KanjiVG `-all.zip` also ships ~4,959 **variant files** (`<hex>-<Suffix>.svg`) — alternates of the *same* codepoint, not extra kanji. `download_kanjivg.py` extracts only plain `<hex>.svg` (the canonical choice, and the only name `kanji_lookup.py` resolves). Suffix inventory: `Kaisho` 4,188 (楷書 printed block style — main SVGs are handwriting-style), `Vt{Fst,Lst,N}` ~570 (alternative stroke orders — VtLst = last stroke differs), `Hz*` ~430 (変体 variant stroke shapes), `Hyougai` 289 (表外 forms), `Jinmei` 34 (人名用), `Md`/`Midashi` ~30 (dictionary-headword glyphs), `Insatsu` 20 (印刷 printed form), misc ~50 (`Ten`/`Dg`/`NoDot`…). Enabling them later (e.g. a "variant glyph / alt stroke order" UI toggle) only needs `_HEX_SVG_RE` relaxed — the zip already contains them.

**Learner-facing word lists**
- `compverb` — ~1,100 compound verbs (Tagashira & Hoff).
- `4jword3` — ~3,000 yojijukugo (four-kanji idioms/proverbs).
- `/kotowaza` — Tim Duncan's proverb collection.
- `KanjiGoldData` / `KG_Top6Words` — precomputed "top-6 common words per kanji" (EDICT-based).
- `classical.zip` — classical Japanese glossary.

**Domain glossaries** (EDICT-format, mergeable as chunks; niche vocab only)
`riverwater` ~45k (rivers/water), `engscidic` ~14k (engineering/sci), `lawdict_comb` ~6.7k (legal), `ediclsd4`/`lifscdic` (biomedical), `findic` ~600 (finance), `mktdic` (business/marketing), `geodic` ~1.3k, `lingdic` ~2.9k, `forsdic` ~800 (forestry EN/ES), `aviation` ~738, `concrete` ~1,060, `manufdic` ~670, `envgloss`, `chemdict`, `jisterme` ~5.8k, `stardict` 107 (constellations), `SwordVocab`. `compdic` already merged into EDICT as `{comp}` tags.

**Frequency data** (older — prefer NG nfXX or modern jpdb/BCCWJ lists)
`wordfreq`/`wordfreq_ck` (~300k words, 1998 Mainichi corpus), `edict-freq-20081002` (freq markup keyed to EDICT, 2008 blog corpus), `base_aggregates`/`term_aggregates` (2008 novels), `edict_dupefree_freq_distribution` / `kanjidic_freq_distribution` (McDonald).

**Other languages** (only if multilingual ever matters)
`wadokujt` (DE), `jr-edict` (RU), `edict_nl` (NL), `kanjidic_{es,pt,fr}`, `HunTechDict` (HU), CC-CEDICT (ZH, actively updated).

**Corpus text**
`genji.*` (Tale of Genji), `/mangajin-vocab` (vocab keyed to MangaJin magazine).

**Jisho's data sources** (list copied from jisho.org — cross-check of what
Jisho pulls that this project doesn't yet)
The data used in Jisho comes from a variety of open source projects:

- **JMdict** — general dictionary, ~170k entries, the bulk of Jisho's words.
- **JMnedict** — proper names (people, companies, locations).
- **KANJIDIC2** — kanji readings/meanings/metadata incl. dictionary lookup
  numbers, stroke count, variant forms.
- **RADKFILE** — kanji radicals → drives Jisho's radical lookup.
- **Jreibun** — teacher-written, professionally translated example
  sentences (407 as of Feb 2023, growing).
- **Tatoeba (Tanaka corpus)** — most of Jisho's example sentences.
- **KanjiVG** — stroke-order data.
- **DBpedia** — Wikipedia articles having both ja and en versions.
- **Jonathan Waller's JLPT Resources** — word/kanji → JLPT level.
- **WaniKani audio (Tofugu)** — audio files.
- **Ve** — Jisho's Ruby wrapper over MeCab for Japanese parsing.
- **kanjivg2svg** — generator for Jisho's old stroke-order diagrams.
- **SKIP** (System of Kanji Indexing by Patterns) — Jack Halpern / Kanji
  Dictionary Publishing Society (kanji.org), used with permission,
  CC BY-SA 4.0.
