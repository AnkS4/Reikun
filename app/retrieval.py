"""
Retrieval over the Qdrant `jmdict_chunks` collection.

Modes (all evaluated in eval/eval.py --ir):
    auto    – query routing (default): the rewritten query is classified and
              sent down the matching plan —
                ja          Japanese input → BM25 arm + exact-match arm
                              (kanji_form / reading), RRF with the exact arm
                              weighted higher so exact entries pin to the top
                en_word     1–2 word English query → dense + BM25 +
                              exact-match (gloss_keys) arms fused with RRF,
                              then a formula query adds a commonness prior
                en_sentence longer English input → dense-heavy RRF (dense arm
                              weighted 2×) — gloss exact-match can't fire
    vector  – dense cosine search only (baseline)
    text    – sparse BM25 search only
    hybrid  – server-side Reciprocal Rank Fusion of three prefetch arms:
                • dense semantic match
                • BM25 lexical match
                • dense match restricted to exact kanji_form / reading /
                  gloss_keys hits
              (explicit-mode default, best on the gold set before routing)

`gloss_keys` is a keyword-indexed payload field of normalised meanings
(lowercased, parentheticals stripped, "to"-less verb variant included) built
by scripts/build_chunks.py — it fixes exact-match for English queries whose
raw glosses carry parentheticals, e.g. 犬 is "dog (Canis (lupus) familiaris)".

Query rewriting runs before retrieval (app.query_rewrite). A re-ranking
stage (local cross-encoder / Cohere Rerank) was implemented and evaluated —
both hurt MRR on this bilingual corpus — and was removed entirely.
"""

import logging
import threading
import time
from dataclasses import dataclass, field, replace
from functools import lru_cache
from types import MappingProxyType

from qdrant_client.models import (
    FieldCondition,
    Filter,
    FormulaQuery,
    Fusion,
    FusionQuery,
    MatchValue,
    MultExpression,
    Prefetch,
    Rrf,
    RrfQuery,
    SparseVector,
    SumExpression,
)
from sudachipy import Dictionary as _SudachiDictionary
from sudachipy.tokenizer import Tokenizer as _SudachiTokenizer

from app.config import COLLECTION, DENSE_VECTOR, PROC_DIR, QUERY_REWRITE, SPARSE_VECTOR, qdrant_client
from app.embedder import embed_query, warm_models
from app.headword_index import PAYLOAD_FIELDS, TrieIndex, add_entry, build_trie
from app.kanji_lookup import is_kanji
from app.query_rewrite import Rewrite, gloss_key, is_japanese, normalise, rewrite_query

# SplitMode.B — middle word units (図書館 one token, 位置+し+て+い+ます still
# separate): the granularity that matches dictionary headwords.
_SPLIT_MODE = _SudachiTokenizer.SplitMode.B

log = logging.getLogger(__name__)

MODES = ("auto", "hybrid", "vector", "text")
PREFETCH_MIN = 100      # min candidates fetched per arm — retrieval is cheap,
PREFETCH_FACTOR = 4     # so a generous pool is free and lets fusion rescue
                        # entries that rank poorly in a single arm. This is the
                        # recall ceiling: the formula can only reorder what the
                        # arms return, and raising 30→100 moved Hit@5 77→91 on
                        # eval/eval.py (a diluted entry like 空, whose vector
                        # is spread over 30 glosses, only surfaces this deep).
EXACT_BONUS = 1.0       # additive boost when the query equals a kanji_form /
                        # reading / gloss_key — several arm positions, so an
                        # exact dictionary hit beats a merely-similar entry
COMMON_BOOST = 1.0      # flat prior on JMdict's own commonness (1.0 tier-1 pri
                        # markers, 0.5 tier-2, nf gradient otherwise). Unlike
                        # CANONICAL_BOOST it applies to every candidate, not
                        # just first-sense gloss matches, so it still nudges
                        # results for queries that match no gloss exactly.
CANONICAL_BOOST = 3.0   # K × wf_score × (query is a *first-sense* gloss).
                        # The one canonicality prior, replacing the earlier
                        # commonness / nf-band boosts. Two signals multiplied,
                        # and both are needed:
                        #   wf_score  – corpus Zipf frequency (~0–7), the only
                        #               signal fine-grained enough to order
                        #               near-synonyms that share JMdict's pri
                        #               markers and nf band (仕事 5.7/作業 4.9)
                        #               and to rank katakana either way
                        #               (ゲーム 5.6 vs キャット 3.1).
                        #   primary   – is the query what the entry *mainly*
                        #               means? Frequency alone is harmful
                        #               without it: 足 ("leg") lists "money" as
                        #               a minor sense and outranks お金;
                        #               委員長 lists "chair" and beats 椅子.
MAX_QUERY_CHARS = 150   # input cap, any language — longer text is pasted prose,
                        # never a headword or gloss. Rejected before rewrite /
                        # embed / retrieval, so a long paste costs no model or
                        # DB call. ~3.5× the longest real question in the gold
                        # set (42 chars).
MAX_JA_QUERY_CHARS = 100  # post-rewrite ceiling for Japanese input, shared with
                          # segment_japanese: up to it a ja string gets the
                          # morphological parse — multi-clause sentences stay
                          # usable since each morpheme is its own chip.
                          # Sized from data: ~100% of the Tatoeba example corpus
                          # is ≤80 chars (p99 = 55, median 19); the extra room
                          # covers longer multi-clause input — past it the
                          # input is pasted prose, not a lookup. The cap also
                          # kills the old fall-through where too-long ja
                          # queries got a bare "Nothing found".


@dataclass(frozen=True)
class SearchResponse:
    """Immutable: instances are shared across callers through the per-process
    search cache, so `results` is a tuple and `meta` a read-only mapping — a
    caller can't `sort()`/`pop()` its way into corrupting the cached copy."""
    results: tuple[dict, ...]
    rewrite: Rewrite
    mode: str
    latency_ms: int
    meta: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))


def _hit_to_dict(hit, score: float | None = None) -> dict:
    p = hit.payload or {}
    return {
        "id": int(hit.id),
        "kanji_form": p.get("kanji_form"),
        "reading": p.get("reading", ""),
        "kanji_forms": p.get("kanji_forms") or [],
        "readings": p.get("readings") or [],
        "meanings": p.get("meanings", []),
        "example_sentences": p.get("example_sentences", []),
        "is_common": p.get("is_common", False),
        "text": p.get("text", ""),
        "score": round(float(hit.score if score is None else score), 4),
    }


def entry_forms(r: dict) -> tuple:
    """Every written form of a result — primary kanji_form/reading plus the
    variant lists — the same fields _exact_filter matches a Japanese query
    against (a kana query like しごと hits via `reading`, an alternate like
    しまうま via `readings`)."""
    return (r.get("kanji_form"), r.get("reading"),
            *(r.get("kanji_forms") or []), *(r.get("readings") or []))


def _exact_filter(query: str) -> Filter:
    # kanji_form/reading match Japanese input verbatim; kanji_forms/readings
    # hold every variant form so alternates (斑馬, シマウマ) hit too;
    # gloss_keys expects the same normalisation used at index time
    # (lowercased, parens stripped).
    return Filter(should=[
        FieldCondition(key="kanji_form", match=MatchValue(value=query)),
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="kanji_forms", match=MatchValue(value=query)),
        FieldCondition(key="readings", match=MatchValue(value=query)),
        FieldCondition(key="gloss_keys", match=MatchValue(value=gloss_key(query))),
    ])


def _primary_filter(query: str) -> Filter:
    """Matches only entries whose *first sense* means the query — Japanese
    input matches verbatim as before (a headword is its own primary sense)."""
    return Filter(should=[
        FieldCondition(key="kanji_form", match=MatchValue(value=query)),
        FieldCondition(key="reading", match=MatchValue(value=query)),
        FieldCondition(key="kanji_forms", match=MatchValue(value=query)),
        FieldCondition(key="readings", match=MatchValue(value=query)),
        FieldCondition(key="primary_gloss_keys", match=MatchValue(value=gloss_key(query))),
    ])


def is_headword(term: str) -> bool:
    """True if `term` is a written form of any entry.

    Used by the random-kanji button to skip kanji that aren't standalone
    words. Answered from the mmap'd headword trie when it is already loaded
    (~µs, no network — the trie ships in the image and is warmed at boot);
    before the warm-up finishes it falls back to one filtered Qdrant count
    rather than blocking on the trie build.
    """
    if _headword_index is not None:
        return term in _headword_index
    flt = Filter(should=[
        FieldCondition(key="kanji_form", match=MatchValue(value=term)),
        FieldCondition(key="kanji_forms", match=MatchValue(value=term)),
    ])
    return qdrant_client().count(COLLECTION, count_filter=flt, exact=True).count > 0


def _sparse(vec) -> SparseVector:
    return SparseVector(indices=vec.indices.tolist(), values=vec.values.tolist())


def _pool(num_results: int) -> int:
    return max(PREFETCH_MIN, num_results * PREFETCH_FACTOR)


# ── Retrieval arms ───────────────────────────────────────────────────────────

def vector_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Dense cosine search only."""
    dense, _ = vectors or embed_query(query)
    hits = qdrant_client().query_points(COLLECTION, query=dense, using=DENSE_VECTOR, limit=num_results).points
    return [_hit_to_dict(h) for h in hits]


def text_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Sparse BM25 search only."""
    _, sparse = vectors or embed_query(query)
    hits = qdrant_client().query_points(COLLECTION, query=_sparse(sparse), using=SPARSE_VECTOR, limit=num_results).points
    return [_hit_to_dict(h) for h in hits]


def hybrid_search(query: str, num_results: int = 5, *, vectors=None) -> list[dict]:
    """Dense + BM25 + exact-match arms fused with RRF inside Qdrant."""
    dense, sparse = vectors or embed_query(query)
    pool = _pool(num_results)
    hits = qdrant_client().query_points(
        COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
            Prefetch(query=_sparse(sparse), using=SPARSE_VECTOR, limit=pool),
            Prefetch(query=dense, using=DENSE_VECTOR, filter=_exact_filter(query), limit=pool),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=num_results,
    ).points
    return [_hit_to_dict(h) for h in hits]


# ── Query routing (mode="auto") ──────────────────────────────────────────────

def route_query(query: str) -> str:
    """ja | en_word | en_sentence — which retrieval plan fits this query."""
    if is_japanese(query):
        return "ja"
    # ≤3 tokens covers gloss-style queries ("to eat", "to be late",
    # "thank you", "train station"); real descriptions run longer.
    return "en_word" if len(query.split()) <= 3 else "en_sentence"


def _rrf(prefetches: list[Prefetch], weights: list[float], limit: int):
    return dict(prefetch=prefetches, query=RrfQuery(rrf=Rrf(weights=weights)), limit=limit)


def _auto_search(query: str, num_results: int, *, vectors, route: str) -> list[dict]:
    dense, sparse = vectors
    pool = _pool(num_results)
    sparse_vec = _sparse(sparse)

    if route == "ja":
        # Dense embeddings are English-tuned (they score ~0 MRR on kana in
        # eval/retrieval_eval.md), so Japanese input goes BM25 + exact-match
        # only. The exact arm is weighted higher so a headword/reading hit
        # always outranks a merely-similar BM25 result.
        params = _rrf(
            [
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, filter=_exact_filter(query), limit=pool),
            ],
            weights=[1.0, 2.0],
            limit=num_results,
        )
    elif route == "en_sentence":
        # No exact arm — a sentence can't equal a headword or a gloss key.
        # Dense carries semantics, so it gets double weight.
        params = _rrf(
            [
                Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
                Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
            ],
            weights=[2.0, 1.0],
            limit=num_results,
        )
    else:  # en_word
        # Full hybrid fused with RRF, then a formula query layers two priors on
        # the fused score: +EXACT_BONUS when the query equals a headword,
        # reading or normalised gloss, and +CANONICAL_BOOST × wf_score when the
        # query is the entry's *first-sense* gloss. Ranking exact matches by
        # bonus (not by dense order inside a filtered arm) is what puts 犬 above
        # 猟犬 for "dog"; the canonical prior is what puts it above ワン子.
        # (Nested prefetch → RRF → formula is the documented pattern; a main
        # query can't be both fusion+formula.)
        exact = _exact_filter(query)
        params = dict(
            prefetch=Prefetch(
                prefetch=[
                    Prefetch(query=dense, using=DENSE_VECTOR, limit=pool),
                    Prefetch(query=sparse_vec, using=SPARSE_VECTOR, limit=pool),
                    Prefetch(query=dense, using=DENSE_VECTOR, filter=exact, limit=pool),
                ],
                query=RrfQuery(rrf=Rrf()),
                limit=pool,
            ),
            query=FormulaQuery(
                defaults={"wf_score": 0.0},
                formula=SumExpression(sum=[
                    "$score",
                    MultExpression(mult=[EXACT_BONUS, exact]),
                    MultExpression(mult=[COMMON_BOOST, "commonness"]),
                    MultExpression(mult=[CANONICAL_BOOST, "wf_score", _primary_filter(query)]),
                ])
            ),
            limit=num_results,
        )

    hits = qdrant_client().query_points(COLLECTION, **params).points
    return [_hit_to_dict(h) for h in hits]


_SEARCHERS = {"hybrid": hybrid_search, "vector": vector_search, "text": text_search}


# ── Japanese compound queries ────────────────────────────────────────────────

_headword_index: TrieIndex | None = None
_headword_lock = threading.Lock()


# Particles that are JMdict entries but not useful as the first hit for a
# sentence split. の's entry is 乃; は/に/を/が often match unrelated
# single-kana nouns. These are grammar, shown explicitly so they aren't
# skipped or mislabeled. Readings are the modern pronunciation — は/へ/を
# keep the historical kana (は→わ, へ→え, を→お) when used as particles.
_PARTICLES = {
    "の": ("の", ("possessive particle",)),
    "は": ("わ", ("topic particle",)),
    "が": ("が", ("subject particle",)),
    "を": ("お", ("object particle",)),
    "に": ("に", ("location / time particle",)),
    "へ": ("え", ("direction particle",)),
    "で": ("で", ("location / means particle",)),
    "と": ("と", ("and / with",)),
    "も": ("も", ("also",)),
    "や": ("や", ("and (listing)",)),
    "か": ("か", ("question particle",)),
    "ね": ("ね", ("seeking agreement",)),
    "よ": ("よ", ("emphasis",)),
    "から": ("から", ("from; because",)),
    "まで": ("まで", ("until; as far as",)),
    "より": ("より", ("than; from",)),
    "って": ("って", ("casual quotation / topic",)),
}

# Auxiliary verbs (助動詞), glossed as grammar — the JMdict entry behind the
# same kana is usually unrelated (ます → 升 "measuring box"; た → 他?). Keyed
# by Sudachi's dictionary_form (ます for まし/ます, う for volitional よ…).
_AUX_GLOSSES = {
    "ます": "polite ending",
    "た": "past tense",
    "ない": "negative ending",
    "ぬ": "negative ending (literary)",
    "ん": "negative ending (casual)",
    "う": "volitional — let's / shall",
    "よう": "volitional — let's / shall",
    "だ": "casual copula — is / am / are",
    "です": "polite copula",
    "らしい": "seems like / -ish",
    "そう": "looks like / hearsay",
    "みたい": "like; seems",
    "たい": "want to ~",
    "べし": "should (べき)",
    "まい": "will not / probably not",
    "れる": "passive / potential",
    "られる": "passive / potential",
    "せる": "causative — make/let ~",
    "させる": "causative — make/let ~",
    "たがる": "wants to ~ (of others)",
    "がる": "shows signs of ~",
    "ず": "without ~ing",
}

# Subsidiary verbs after ~て/〜で (Vて + いる/おく/しまう…) — Sudachi tags them
# plain 動詞, but their JMdict homographs mislead (て+いる → 射る "to shoot"
# where it means "is ~ing"). Keyed by dictionary_form; only applied when the
# previous token is the て/で conjunctive particle (a main-verb いる after が
# still gets its dictionary gloss).
_SUBSIDIARY = {
    "いる": "~ing / is ~ (progressive or continuing state)",
    "おく": "~ in advance / leave ~ as is",
    "しまう": "~ completely / regrettably",
    "みる": "try ~ing",
    "いく": "go on ~ing / ~ away",
    "くる": "start / come to ~",
    "くださる": "honorific — please ~",
    "もらう": "~ for me / have ~ done",
    "くれる": "~ for me (favour)",
    "あげる": "~ for someone (favour)",
    "ほしい": "want ~ done",
    "ある": "is ~ed (resulting state)",
}

# Light nouns and honorifics whose dictionary candidates mislead in sentence
# context: ため glosses "good; cesspool" (為/溜め share the reading) where it
# is "for the sake of"; さん contests with 酸 "acid". Applied only to kana
# surfaces — kanji 為/事/山 keep their real entries.
_GRAMMAR = {
    "ため": "for the sake of ~ / because of ~",
    "こと": "abstract thing / nominalizer — ~ing",
    "もの": "thing / (reason) because ~",
    "ところ": "place / just about to ~",
    "はず": "ought to ~ / expected to ~",
    "わけ": "reason / no wonder ~",
    "ほう": "the ~ one (of two) / direction",
    "うち": "within ~ / while ~",
    "まま": "as-is / unchanged state",
    "さん": "honorific suffix — Mr/Ms ~",
    "くん": "honorific suffix — (junior male) ~",
    "ちゃん": "honorific suffix — (affectionate) ~",
    "さま": "honorific suffix — (formal) ~",
}


_KATA_TO_HIRA = str.maketrans({chr(c): chr(c - 0x60) for c in range(0x30A1, 0x30F7)})


def _hira(text: str) -> str:
    """Katakana → hiragana (Sudachi readings come back in katakana)."""
    return text.translate(_KATA_TO_HIRA)


def _num_gloss(norm: str) -> str:
    """'100000' → '100,000'; a decimal like '3.5' keeps its point."""
    return f"{float(norm):,}" if "." in norm else f"{int(norm):,}"


# POS major categories that still drop out of a sentence parse instead of
# getting a bare chip: punctuation/symbols (、。) and whitespace. Anything else
# unresolvable (names, %, loanwords JMdict lacks) keeps a chip — its surface
# plus reading is information; an invisible hole isn't.
_SKIP_POS = {"補助記号", "空白"}


def headword_index() -> TrieIndex:
    """
    Every kanji_form/reading in the collection → minimal entry info.

    Served from `data/processed/headword_index.marisa` — a ~26 MB mmap'd trie
    committed to the repo and baked into the image. Missing file → rebuilt
    from one payload-only Qdrant scroll (~44 requests) and saved for the next
    boot; that fallback keeps the old ~340 MB in-memory dict cost, so
    constrained hosts should ship the file. Either way the result is kept for
    the process lifetime — dictionary contents only change on re-ingest,
    which restarts the app. The double-checked lock keeps concurrent first
    callers from paying for a second build. Used to decompose compound
    Japanese queries ("静かな場所" → 静か + 場所) that have no single
    dictionary entry.
    """
    global _headword_index
    if _headword_index is None:
        with _headword_lock:
            if _headword_index is None:  # another thread may have built it while we waited
                path = PROC_DIR / "headword_index.marisa"
                if not path.exists():
                    _build_headword_trie(path)
                _headword_index = TrieIndex(path)
    return _headword_index


def _scroll_headwords() -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    offset = None
    client = qdrant_client()
    while True:
        # 5,000 points/page was fastest in local benchmarks — past ~5k the
        # payload transfer, not the round trips, dominates (~40 MB total).
        points, offset = client.scroll(
            COLLECTION, with_payload=list(PAYLOAD_FIELDS), with_vectors=False, limit=5000, offset=offset,
        )
        for p in points:
            add_entry(index, p.payload or {})
        if offset is None:
            return index


def _build_headword_trie(path) -> None:
    """Rebuild headword_index.marisa from a payload-only scroll — the fallback
    when a boot finds no shipped file (self-provisioning hosts). The
    intermediate dict carries the ~340 MB in-memory cost the trie exists to
    avoid, so deploys should ship the file rather than rely on this."""
    build_trie(_scroll_headwords(), path)


def _pick(cands: list[dict], reading: str = "") -> dict | None:
    """Resolve a contested written form to one entry: the tokenizer's
    contextual reading (ヒガシ) picks the consistent gloss+reading pair.
    Returns None when nothing disambiguates — better to show all candidates
    (_ambiguous) than a silently wrong first pick."""
    if reading:
        matches = [e for e in cands if e["reading"] == reading]
        if len(matches) == 1:
            return matches[0]
        # Several entries share this exact reading (居る/射る both いる) —
        # still ambiguous, so show all rather than first.
        return cands[0] if len(cands) == 1 and not matches else None
    return cands[0] if len(cands) == 1 else None


def _ambiguous(surf: str, cands: list[dict]) -> dict:
    """A contested form shown with every candidate's reading+gloss — honest
    ambiguity (東 → ひがし/あずま/…) instead of one misleading gloss."""
    # Common headwords first — index order otherwise leads with rarer senses
    # (しかし would show 私窩子 "prostitute" before a common candidate).
    ordered = sorted(cands, key=lambda e: not e["is_common"])
    options = [f'{e["reading"] or "—"} — {"; ".join(e["meanings"][:2])}' for e in ordered[:8]]
    if len(ordered) > 8:
        options.append(f"… +{len(ordered) - 8} more")
    return {
        "text": surf,
        "kanji_form": surf,
        "reading": "",
        # One gloss per candidate (kappa first, not the alphabetically-first
        # gloss across every candidate).
        "meanings": list(dict.fromkeys(m for e in ordered for m in e["meanings"][:1]))[:4],
        "options": options,
        # The surface is confirmed — the *gloss* is what's contested — so a
        # headword compound still merges (かっぱ+巻き → かっぱ巻き) and thereby
        # resolves the ambiguity contextually.
        "_idx": True,
    }


_warm_started = False


def warm_headword_index() -> None:
    """
    Kick off the headword_index() build on a daemon thread at app startup —
    the first compound Japanese query then hits a warm (or at least
    in-progress, lock-shared) index instead of paying the whole scroll.
    """
    global _warm_started
    if _warm_started:
        return
    _warm_started = True

    def _warm() -> None:
        try:
            headword_index()
            _tokenizer()  # dictionary load is ~1-2 s — warm it too
        except Exception as exc:  # Qdrant not up yet — the first live compound query retries
            log.warning("headword-index warmup failed: %s", exc)

    def _warm_embedders() -> None:
        # The Docker build only *downloads* the fastembed models; loading the
        # ONNX sessions is 1-3 s per process that the first search would pay.
        # Independent of the trie/Sudachi load, so it runs on its own thread.
        try:
            warm_models()
        except Exception as exc:
            log.warning("embedding-model warmup failed: %s", exc)

    for target in (_warm, _warm_embedders):
        threading.Thread(target=target, daemon=True).start()


@lru_cache(maxsize=1)
def _tokenizer():
    """Lazy Sudachi tokenizer (~1-2 s load once). Runtime pins sudachidict-core;
    small accepted as a fallback for environments that install that instead."""
    for name in ("core", "small"):
        try:
            return _SudachiDictionary(dict=name).tokenizer()
        except Exception:
            pass
    raise RuntimeError("sudachipy installed but no sudachidict dictionary package found")


_AUX_POS, _PARTICLE_POS = "助動詞", "助詞"


class _Morph:
    """Plain-Python snapshot of one Sudachi morpheme (reading already in
    hiragana) so the segmentation passes never re-enter the FFI."""

    __slots__ = ("lemma", "norm", "pos", "pos_sub", "pos_sub2", "reading", "surf")

    def __init__(self, m) -> None:
        pos = m.part_of_speech()
        self.surf = m.surface()
        self.pos, self.pos_sub, self.pos_sub2 = pos[0], pos[1], pos[2]
        self.lemma = m.dictionary_form()
        self.norm = m.normalized_form()
        self.reading = _hira(m.reading_form())


def _segment_sudachi(query: str, index: TrieIndex) -> list[dict] | None:
    """
    Real morphological split of a Japanese sentence: Sudachi gives morpheme
    boundaries, lemmas (食べ → 食べる) and POS, so conjugation tails resolve
    to auxiliary glosses and content words to their actual JMdict entries —
    where greedy longest-match picked any dictionary hit (してい "servant").

    Display grouping: a maximal tail of *ending parts* — 助動詞 auxiliaries
    (まし/た/ない), subsidiary verbs after て/で (いる/しまう…), and the
    conjunctive て/で gluing them — merges with its stem token into ONE
    segment (食べ+まし+た → 食べました, し+て+い+ます → しています). The badge
    shows the inflected word; the tooltip keeps the per-morpheme breakdown.
    """
    # Snapshot each morpheme's fields once — every accessor is a Rust FFI call
    # and the passes below would otherwise re-read pos/reading several times
    # per token.
    toks = [_Morph(m) for m in _tokenizer().tokenize(query, _SPLIT_MODE)]
    n = len(toks)

    def _is_te(i: int) -> bool:
        return toks[i].pos == _PARTICLE_POS and toks[i].surf in ("て", "で")

    # Ending flags, computed right-to-left: a て/で conjunctive is an ending
    # part only when what follows is one (て働く keeps its て as a connector).
    ending = [False] * n
    for i in range(n - 1, -1, -1):
        if toks[i].pos == _AUX_POS:
            ending[i] = True
        elif (toks[i].pos == "動詞" and i and _is_te(i - 1)
              and toks[i].lemma in _SUBSIDIARY):
            ending[i] = True
        elif _is_te(i) and i + 1 < n and ending[i + 1]:
            ending[i] = True

    groups: list[list[int]] = []
    for i in range(n):
        if ending[i] and groups:
            groups[-1].append(i)
        else:
            groups.append([i])

    def _gloss(m: "_Morph", prev_te: bool, conj: bool = False) -> dict | None:
        """One morpheme → segment fields; None = unresolvable token (skipped).
        conj marks a て/で used as a conjunctive inside an inflection tail —
        glossed as plain "particle", not its case-particle meaning."""
        surf, pos, reading = m.surf, m.pos, m.reading
        if prev_te and (g := _SUBSIDIARY.get(m.lemma)):
            return {"text": surf, "kanji_form": surf, "reading": reading, "meanings": [g]}
        if pos == _PARTICLE_POS:
            if conj and surf in ("て", "で"):
                p_reading, meanings = reading, ("particle",)
            else:
                p_reading, meanings = _PARTICLES.get(surf, (reading, ("particle",)))
            return {"text": surf, "kanji_form": surf, "reading": p_reading, "meanings": list(meanings)}
        if pos == _AUX_POS:
            g = _AUX_GLOSSES.get(m.lemma, "auxiliary")
            # A で after a noun is genuinely two words: the case particle
            # (山で "at the mountain") or the copula's conjunctive (山だ→で
            # "it is a mountain, and…"). Sudachi commits to the copula at
            # clause boundaries, so gloss both readings rather than leave a
            # bare "casual copula" on an instrumental で.
            if m.lemma == "だ" and surf == "で":
                g = "casual copula (continuative) — or で at/by-means-of particle"
            return {"text": surf, "kanji_form": surf, "reading": reading, "meanings": [g]}
        # Kana-spelled function words are grammar glosses, not whichever
        # homograph shares the reading — ため is "for the sake of", not 溜め
        # "cesspool". Kanji surfaces keep the dictionary path.
        if (g := _GRAMMAR.get(surf)) and not any(map(is_kanji, surf)):
            return {"text": surf, "kanji_form": surf, "reading": reading, "meanings": [g]}
        # Nouns/verbs/adjectives: the lemma (食べ→食べる, 位置し→位置する) is
        # what a dictionary indexes; the token's reading picks the pair
        # (東→ヒガシ → the ひがし "east" entry, not あずま). When the lemma's
        # candidates can't be resolved, Sudachi's normalized form is the
        # tiebreaker for *kana* surfaces — it carries the disambiguated
        # spelling (いい→良い, しかし→然し, また→又) where the lemma only lists
        # the kana homographs. Kanji surfaces don't retry on a tie: a norm
        # lookup can resolve to a rare reading (来そう → らい "next year" over
        # き "to come"), so they stay honest-ambiguous unless the lemma found
        # nothing at all.
        cands = entry = None
        kana_surf = not any(map(is_kanji, surf))
        for form in dict.fromkeys((m.lemma, m.norm, surf)):
            found = index.get(form)
            if not found:
                continue
            if cands is None:
                cands = found
            if entry := _pick(found, reading):
                break
            if not kana_surf:
                break
        if not cands:
            # Numerals aren't JMdict headwords but are self-describing — the
            # normalised value is the gloss (10万 → "100,000"). Only digit
            # values reach here: 万/二/億 are headwords resolved above. No
            # furigana — Sudachi reads digits one-by-one (イチレイレイ).
            if m.pos_sub == "数詞" and m.norm.replace(".", "", 1).isdigit():
                return {"text": surf, "kanji_form": surf, "reading": "",
                        "meanings": [_num_gloss(m.norm)], "_num": True}
            if pos in _SKIP_POS:
                return None
            return {"text": surf, "kanji_form": surf, "reading": reading, "meanings": []}
        if entry:
            # Furigana is the surface's own reading when the surface isn't the
            # canonical written form (起こっ → おこっ); an exact headword keeps
            # the entry's principal reading (明日 → あした over Sudachi's あす).
            # The lemma reading moves to _lemma for the compound merge —
            # dictionary compounds match on canonical readings
            # (精進+料理 → しょうじんりょうり).
            return {"text": surf, **entry, "_lemma": entry["reading"],
                    "reading": entry["reading"] if surf == entry["kanji_form"] else reading,
                    "_idx": True}
        amb = _ambiguous(surf, cands)
        amb["reading"] = reading
        return amb

    parts: list[dict] = []
    for g in groups:
        if len(g) == 1:
            if seg := _gloss(toks[g[0]], g[0] > 0 and _is_te(g[0] - 1)):
                seg["_start"] = seg["_end"] = g[0]
                parts.append(seg)
            continue
        # Inflected word: one badge for the tail, options = per-morpheme lines.
        lines, meanings = [], []
        for i in g:
            seg = _gloss(toks[i], i > 0 and _is_te(i - 1), conj=ending[i])
            if seg is None:
                continue
            if seg["meanings"] and seg["meanings"][0] not in meanings:  # one summary gloss per part
                meanings.append(seg["meanings"][0])
            head = f"→{seg['kanji_form']}" if seg.get("kanji_form") != seg["text"] else ""
            opts = seg.get("options", [])
            if opts:
                # Ambiguous morpheme: first candidate on its line, the rest
                # as indented continuations — no truncation of real options.
                lines.append(f"{seg['text']}{head} — {opts[0]}")
                lines.extend(f"   {o}" for o in opts[1:])
            elif seg["meanings"]:
                lines.append(f"{seg['text']}{head} — {'; '.join(seg['meanings'][:2])}")
            else:
                lines.append(f"{seg['text']}{head}")
        text = "".join(toks[i].surf for i in g)
        # Whole-word reading = the morphemes' contextual readings joined —
        # 食べ+まし+た → タベマシタ → たべました, so the chip gets furigana.
        reading = "".join(toks[i].reading for i in g)
        parts.append({"text": text, "kanji_form": text, "reading": reading,
                      "meanings": meanings[:4], "options": lines,
                      "_start": g[0], "_end": g[-1]})

    # Fuse bare numeral + counter into one chip ("25日", "2分", "17歳"):
    # Sudachi splits them and the counter's own entry reading is contextually
    # wrong (日→か where the word is にじゅうごにち), so the fused chip keeps
    # no furigana and glosses value + counter unit instead. The counter's own
    # inflection tail rides along — "7" + "人です" → "7人です".
    fused: list[dict] = []
    for p in parts:
        prev = fused[-1] if fused else None
        if (prev is not None and prev.get("_num")
                and p.get("_start") == prev.get("_end", -2) + 1
                and (toks[p["_start"]].pos == "接尾辞" or "助数詞" in toks[p["_start"]].pos_sub2)):
            # The counter's first gloss is often a homonym sense (日→"Sunday"
            # where the chip means "counter for days") — prefer it. When the
            # counter heads an inflection group (7人です), its endings' glosses
            # trail the fused meaning; a lone counter stays one summary gloss.
            gloss = next((g for g in p["meanings"] if "counter" in g),
                         (p["meanings"] or [toks[p["_start"]].surf])[0])
            tail = p["meanings"][1:] if p["_end"] != p["_start"] else []
            num_surf = prev["text"]
            prev.update(text=num_surf + p["text"], kanji_form=prev["kanji_form"] + p["text"],
                        reading="", meanings=[f"{num_surf} · {gloss}", *tail], _end=p["_end"])
            prev.pop("_num")  # the counter ends the numeral — "2分4秒" fuses 秒 to 4, not 分
            if p.get("options"):
                prev["options"] = [f"{num_surf} — {num_surf}"] + p["options"]
            continue
        fused.append(p)
    parts = fused

    # Compound rescue: two adjacent index-resolved segments whose joined
    # surface is itself a headword merge into the compound's entry
    # (精進+料理 → 精進料理) — Sudachi's dictionary can't know every JMdict
    # compound at any split mode. The joined readings pick the entry just
    # like a single token's reading does. Chains extend naturally.
    # Both parts must be token-adjacent — skipped tokens (punctuation,
    # unresolvable words) leave holes, and 山、川 must not merge into 山川.
    out: list[dict] = []
    for p in parts:
        cands = (index.get(out[-1]["text"] + p["text"])
                 if out and out[-1].get("_idx") and p.get("_idx")
                 and out[-1]["_end"] + 1 == p["_start"] else None)
        if not cands:
            out.append(p)
            continue
        prev = out.pop()
        entry = _pick(cands, (prev.get("_lemma") or prev.get("reading") or "")
                             + (p.get("_lemma") or p.get("reading") or ""))
        span = {"_idx": True, "_start": prev["_start"], "_end": p["_end"]}
        if entry:
            out.append({"text": prev["text"] + p["text"], **entry, **span})
        else:
            out.append({**_ambiguous(prev["text"] + p["text"], cands), **span})
    parts = out

    for p in parts:
        for k in ("_idx", "_start", "_end", "_lemma", "_num"):
            p.pop(k, None)
    # ≥2 segments, or one *merged* segment (a lone inflected word like
    # 食べました), or a lone *unresolved* token — 田中 isn't a headword but a
    # bare chip still carries the reading, better than "Nothing found".
    return parts if len(parts) >= 2 or (
        parts and (any(len(g) > 1 for g in groups) or not parts[0]["meanings"])) else None


def _segment_greedy(query: str, index: TrieIndex) -> list[dict] | None:
    """Greedy longest-match split — the fallback when Sudachi fails."""
    parts: list[dict] = []
    i = 0
    while i < len(query):
        for size in range(min(8, len(query) - i), 0, -1):
            word = query[i : i + size]
            if word in _PARTICLES:
                # Grammar, not a dictionary headword — the written form stays
                # as kanji_form so cards show は, while reading carries the
                # actual particle pronunciation (は→わ, へ→え, を→お). A longer
                # match (から) wins over a one-char one (か) — longest-first.
                reading, meanings = _PARTICLES[word]
                parts.append({"text": word, "kanji_form": word, "reading": reading, "meanings": list(meanings)})
                i += size
                break
            # A lone kana can be a headword too (な → "greens"), but for a
            # compound it is almost always a particle/suffix — only accept
            # single-character segments that are kanji.
            if (len(word) > 1 or is_kanji(word)) and (cands := index.get(word)):
                if entry := _pick(cands):  # no tokenizer here — contested forms show all
                    parts.append({"text": word, **entry})
                else:
                    parts.append(_ambiguous(word, cands))
                i += size
                break
        else:
            i += 1  # unmatched character (inflection, unknown suffix …) — skip it
    return parts if len(parts) >= 2 else None


def _segment_bare(query: str) -> list[dict] | None:
    """Degraded parse — raw Sudachi tokens with their readings and no
    glosses, for when the rich `_segment_sudachi` pass fails *after*
    tokenization: boundaries and furigana are still the tokenizer's, so
    unlike `_segment_greedy` nothing here can be confidently wrong."""
    parts = [{"text": m.surf, "kanji_form": m.surf, "reading": m.reading, "meanings": []}
             for m in (_Morph(t) for t in _tokenizer().tokenize(query, _SPLIT_MODE))
             if m.pos not in _SKIP_POS]
    return parts if len(parts) >= 2 else None


def segment_japanese(query: str, max_len: int = MAX_JA_QUERY_CHARS) -> list[dict] | None:
    """
    Split a Japanese sentence/compound into dictionary segments for the
    "parsed as" note. Sudachi gives real morphemes — lemmas, particles and
    auxiliaries — via `_segment_sudachi`; on failure `_segment_bare` keeps
    the tokenizer's boundaries and readings, and only if tokenizing itself
    fails does the greedy longest-match `_segment_greedy` run.

    Returns [{"text", "kanji_form", "reading", "meanings"}, …] when the query
    decomposes into ≥2 parts. None when the query is itself a headword, is
    too long, or doesn't decompose. Greedy-fallback chips carry
    `"approx": True` — its longest-match picks are dictionary coincidences
    (泥地 "mud" for でいち), not morphology, so the UI marks them.
    """
    if not query or len(query) > max_len:
        return None
    index = headword_index()
    if query in index:
        return None
    try:
        return _segment_sudachi(query, index)
    except Exception as exc:
        log.warning("sudachi segmentation failed for %r: %s", query, exc)
    try:
        if parts := _segment_bare(query):
            return parts
    except Exception as exc:
        log.warning("sudachi tokenizer failed for %r: %s", query, exc)
    if parts := _segment_greedy(query, index):
        for p in parts:
            p["approx"] = True
        return parts
    return None


# ── Public entry point ───────────────────────────────────────────────────────

def search(
    query: str,
    num_results: int = 5,
    mode: str = "auto",
    *,
    rewrite_mode: str | None = None,
) -> SearchResponse:
    """Full pipeline: rewrite → route (auto) → retrieve.

    Results are cached per-process: the same (query, settings) pair — whether
    repeated by one user or first asked by another — is served without
    re-embedding or re-querying. Queries are normalised (whitespace + case)
    before keying so superficial variants share an entry. The cache is safe
    because the collection is static between ingest runs (which restart the
    process).

    Over-long queries are rejected before any model or DB call — the response
    carries empty results and meta["too_long"], so callers can show a warning
    rather than a misleading "nothing found". Validation and those rejections
    happen *before* the cache so a pasted paragraph or a bad mode never takes
    a slot from a real result.

    `latency_ms` is always this call's wall time: a cache hit is re-stamped
    (and flagged meta["cached"]) instead of replaying the original
    computation's timing into the monitoring DB.
    """
    if mode not in _SEARCHERS and mode != "auto":
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    t0 = time.perf_counter()
    normalized = " ".join(query.split()).lower()
    too_long = None
    if len(normalized) > MAX_QUERY_CHARS:
        too_long = MAX_QUERY_CHARS
    # A Japanese query longer than the segmentation ceiling is a sentence, not
    # a lookup. Rewriting never changes Japanese input beyond normalise(), so
    # the post-rewrite length is known here.
    elif is_japanese(normalized) and len(normalise(normalized)) > MAX_JA_QUERY_CHARS:
        too_long = MAX_JA_QUERY_CHARS
    if too_long:
        return SearchResponse(results=(), rewrite=Rewrite(normalized, normalized, "none"), mode=mode,
                              latency_ms=_ms_since(t0), meta=MappingProxyType({"too_long": too_long}))

    # None and the configured default are the same setting — resolve before
    # keying so they share one cache entry.
    resp, computed_at = _search_cached(normalized, num_results, mode, (rewrite_mode or QUERY_REWRITE).lower())
    if computed_at < t0:  # served from cache: computed before this call began
        resp = replace(resp, latency_ms=_ms_since(t0), meta=MappingProxyType({**resp.meta, "cached": True}))
    return resp


def _ms_since(t: float) -> int:
    return int((time.perf_counter() - t) * 1000)


@lru_cache(maxsize=512)
def _search_cached(
    query: str,
    num_results: int,
    mode: str,
    rewrite_mode: str,
) -> tuple[SearchResponse, float]:
    """Returns (response, perf_counter at completion) — the timestamp lets
    `search` tell a cache hit from a fresh computation without touching
    `cache_info()`, which isn't attributable per call across threads."""
    t0 = time.perf_counter()
    rw = rewrite_query(query, rewrite_mode)
    t1 = time.perf_counter()

    route = route_query(rw.query) if mode == "auto" else None
    # Only embed with the model(s) the plan will read: the Japanese route and
    # explicit `text` mode never read the dense vector (English-tuned,
    # ~useless on kana), explicit `vector` mode never reads the sparse one.
    vectors = embed_query(rw.query, dense=route != "ja" and mode != "text", sparse=mode != "vector")
    t2 = time.perf_counter()

    if mode == "auto":
        results = _auto_search(rw.query, num_results, vectors=vectors, route=route)
    else:
        results = _SEARCHERS[mode](rw.query, num_results, vectors=vectors)
    t3 = time.perf_counter()

    meta = {
        "rewrite_ms": int((t1 - t0) * 1000),
        "embed_ms": int((t2 - t1) * 1000),
        "retrieve_ms": int((t3 - t2) * 1000),
    }
    if route:
        meta["route"] = route
        # A Japanese query with no exact headword hit may be a compound
        # expression — decompose it so the UI can show the parts.
        if route == "ja" and not any(rw.query in entry_forms(r) for r in results):
            try:
                if segments := segment_japanese(rw.query):
                    meta["segments"] = tuple(segments)
                    if not results:
                        # Compound query with no single entry — surface the
                        # segment entries as the results themselves so the UI
                        # and API consumers get the decomposed words directly.
                        results = [
                            {
                                "id": None,
                                "kanji_form": s["kanji_form"],
                                "reading": s["reading"],
                                "meanings": s["meanings"],
                                "example_sentences": [],
                                "is_common": False,
                                "text": s["text"],
                                "score": 0.0,
                            }
                            for s in segments[:num_results]
                        ]
            except Exception as exc:
                log.warning("segmentation failed for %r: %s", rw.query, exc)

    latency_ms = _ms_since(t0)
    log.info(
        "search %s%s: embed=%dms retrieve=%dms total=%dms",
        mode, f"/{route}" if route else "",
        meta["embed_ms"], meta["retrieve_ms"], latency_ms,
    )
    resp = SearchResponse(results=tuple(results), rewrite=rw, mode=mode,
                          latency_ms=latency_ms, meta=MappingProxyType(meta))
    return resp, time.perf_counter()
