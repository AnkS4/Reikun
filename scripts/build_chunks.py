#!/usr/bin/env python3
"""
Parse the EDRDG originals (JMdict_e_NG + KANJIDIC2 XML) into embeddable
chunks and a kanji lookup table.

Inputs  (data/raw/):
    JMdict_e_NG_examp.xml  - JMdict "Next Generation" XML, Tatoeba examples
                            embedded (synced daily by scripts/download_edrdg.py)
    kanjidic2.xml          - KANJIDIC2 XML (same source kanjidic2.json was
                            converted from)

Outputs (data/processed/):
    chunks.json      - list of word+example chunks ready for embedding
    kanji_table.json - dict keyed by kanji literal with meanings/readings/strokes

Both XML files carry their DOCTYPE internal subset — all ~270 <!ENTITY>
definitions (POS tags like &n; → "noun (common) (futsuumeishi)", dialect
codes, etc.) live there and ElementTree resolves them automatically.
Stripping the DOCTYPE would break parsing, so the files are parsed as-is
with iterparse (streaming — 74 MB / ~219k entries never fully in memory).

Usage:
    python scripts/build_chunks.py
"""

import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordfreq import zipf_frequency

from app.config import CHUNKS_SCHEMA, PROC_DIR, RAW_DIR
from app.conjugation import conjugate
from app.headword_index import add_entry, build_trie
from app.kanji_lookup import is_kanji
from app.query_rewrite import gloss_key, gloss_keys

log = logging.getLogger(__name__)

JMDICT_XML = "JMdict_e_NG_examp.xml"
KANJIDIC_XML = "kanjidic2.xml"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# jmdict-simplified's `common` flag derives from exactly this tier-1 set —
# verified empirically against jmdict.json (reproduces 22,637 flags ±3 daily
# drift): tier-2 markers (news2/ichi2/gai2) never produce `common` on their
# own, and nfNN bands are a separate ranking that feeds freq_band instead.
COMMON_PRI = frozenset({"news1", "ichi1", "spec1", "spec2", "gai1"})
COMMON_PRI2 = frozenset({"news2", "ichi2", "gai2"})
_NF_RE = re.compile(r"nf(\d{2})")

# ── Entity-code classification ────────────────────────────────────────────────
# iterparse resolves the DOCTYPE's <!ENTITY> declarations, so <pos>, <misc>,
# <dial>, <field> and <ke_inf> arrive as English text ("noun (common)
# (futsuumeishi)", "Kansai-ben", "computing"). The original code is recovered
# through the entity table parsed once from the file head — an exact-match
# lookup, never prefix heuristics (adj-na / adj-no / adj-nari / adj-pn share
# every prefix boundary a regex would test). Verified against the
# 2026-11-13 JMdict_e build: every occurring element is exactly one entity.

_ENTITY_RE = re.compile(r'<!ENTITY\s+(\S+)\s+"([^"]*)"')


@lru_cache(maxsize=1)
def _entities() -> tuple[dict[str, str], dict[str, str]]:
    """(code → resolved text, resolved text → code) from the DOCTYPE subset."""
    head = (RAW_DIR / JMDICT_XML).read_bytes()[:262_144].decode("utf-8", "replace")
    dtd = head[: head.index("]>") + 2]
    code_to_text = dict(_ENTITY_RE.findall(dtd))
    return code_to_text, {text: code for code, text in code_to_text.items()}


_UNMAPPED: Counter = Counter()


def _entity_code(text: str | None) -> str | None:
    """JMdict entity code for a resolved element text (None when unmapped —
    counted in _UNMAPPED so a DTD drift surfaces in the build log)."""
    code = _entities()[1].get(text or "")
    if code is None and text:
        _UNMAPPED[text] += 1
    return code


# POS: the 83 codes occurring in JMdict_e (2026-11-13 census, 322,409 sense
# occurrences) plus five DTD-defined codes that occur zero times here
# (adj-kari, v5uru, n-adv, n-t, n-pr — kept so a future full-JMdict feed
# classifies instead of dropping). Tag totals cross-check to the census:
# verb 61,302 · adj-i 3,680 · adj-na 15,074 · noun 214,573 · adv 7,675 ·
# phrase 14,843 · intj 955 · other 4,307.
_POS_TAG_MAP: dict[str, str] = {
    # verb — godan v5*, ichidan v1*, archaic v2*/v4*, suru/kuru/zuru families
    "vt": "verb", "vi": "verb", "vr": "verb", "vk": "verb", "vn": "verb",
    "vz": "verb", "v-unspec": "verb",
    "v1": "verb", "v1-s": "verb",
    "v5r": "verb", "v5s": "verb", "v5k": "verb", "v5u": "verb", "v5m": "verb",
    "v5t": "verb", "v5g": "verb", "v5b": "verb", "v5n": "verb", "v5aru": "verb",
    "v5r-i": "verb", "v5k-s": "verb", "v5u-s": "verb", "v5uru": "verb",
    "vs": "verb", "vs-i": "verb", "vs-s": "verb", "vs-c": "verb",
    "v2a-s": "verb", "v2b-k": "verb", "v2b-s": "verb", "v2d-k": "verb",
    "v2d-s": "verb", "v2g-k": "verb", "v2g-s": "verb", "v2h-k": "verb",
    "v2h-s": "verb", "v2k-k": "verb", "v2k-s": "verb", "v2m-k": "verb",
    "v2m-s": "verb", "v2n-s": "verb", "v2r-k": "verb", "v2r-s": "verb",
    "v2s-s": "verb", "v2t-k": "verb", "v2t-s": "verb", "v2w-s": "verb",
    "v2y-k": "verb", "v2y-s": "verb", "v2z-s": "verb",
    "v4b": "verb", "v4g": "verb", "v4h": "verb", "v4k": "verb", "v4m": "verb",
    "v4n": "verb", "v4r": "verb", "v4s": "verb", "v4t": "verb",
    # adj-i — keiyoushi incl. the archaic ku/shiku/taru/kari classes
    "adj-i": "adj-i", "adj-ix": "adj-i", "adj-ku": "adj-i",
    "adj-shiku": "adj-i", "adj-t": "adj-i", "adj-kari": "adj-i",
    # adj-na — keiyodoshi + rentaishi/genitive-noun adjectivals
    "adj-na": "adj-na", "adj-nari": "adj-na", "adj-no": "adj-na", "adj-pn": "adj-na",
    # noun — common + prefix/suffix uses; n-adv/n-t/n-pr are DTD no-ops here
    "n": "noun", "n-suf": "noun", "n-pref": "noun",
    "n-adv": "noun", "n-t": "noun", "n-pr": "noun",
    "adv": "adv", "adv-to": "adv",
    "exp": "phrase",
    "int": "intj",
    # other — prenominal adj-f, bound forms (suf/pref/pn/prt/conj/ctr),
    # auxiliaries, numbers, copula, unclassified
    "adj-f": "other", "suf": "other", "pn": "other", "prt": "other",
    "pref": "other", "conj": "other", "ctr": "other", "aux-v": "other",
    "num": "other", "aux": "other", "unc": "other", "cop": "other",
    "aux-adj": "other",
}

# Badge order: specific tags before the noun/other catch-alls — plain `n` is
# 66.5% of sense-level tags, so an adj-na+noun entry must badge the adjective.
_POS_ORDER = ("verb", "adj-i", "adj-na", "adv", "intj", "phrase", "noun", "other")

# misc: all 55 DTD codes (52 occur in JMdict_e 2026-11-13, 50,648 elements —
# oth/X/station are DTD no-ops kept for completeness). Two-tier policy: the
# first four tags are union-safe content-type labels that display as badges;
# the rest are sense-conditional register/name labels captured for the
# sense-aware restructure and the org-name suppression in related_words.
_MISC_TAG_MAP: dict[str, str] = {
    # tier 1 — display now
    "on-mim": "on-mim", "uk": "kana", "abbr": "abbr",
    "yoji": "idiom", "id": "idiom", "proverb": "idiom",
    # tier 2 — capture-only
    "form": "formal", "hon": "formal",
    "arch": "archaic", "rare": "archaic", "hist": "archaic",
    "obs": "archaic", "dated": "archaic", "poet": "archaic",
    "col": "colloquial", "sl": "colloquial", "net-sl": "colloquial",
    "m-sl": "colloquial", "derog": "colloquial", "vulg": "colloquial",
    "joc": "colloquial", "hum": "colloquial", "fam": "colloquial",
    "serv": "colloquial", "chn": "colloquial", "pol": "colloquial",
    "sens": "colloquial",
    "org": "name", "work": "name", "company": "name", "product": "name",
    "person": "name", "place": "name", "surname": "name", "given": "name",
    "dei": "name", "ship": "name", "station": "name", "ev": "name",
    "obj": "name", "doc": "name", "creat": "name", "fict": "name",
    "leg": "name", "myth": "name", "relig": "name", "group": "name",
    "unclass": "name",
    "fem": "other", "male": "other", "char": "other", "quote": "other",
    "euph": "other", "oth": "other", "X": "other",
}

_MISC_ORDER = ("on-mim", "idiom", "abbr", "kana",
               "formal", "archaic", "colloquial", "name", "other")


def _coded_tags(texts: Iterable[str], code_to_tag: dict[str, str],
                order: tuple[str, ...]) -> list[str]:
    """Resolved element texts → deduped coarse tags in display priority order."""
    tags = {code_to_tag[c] for t in texts
            if (c := _entity_code(t)) is not None and c in code_to_tag}
    return sorted(tags, key=order.index)


def iter_elements(path: Path, tag: str):
    """Yield each <tag> element, streaming so the tree never fills memory.

    `elem.clear()` alone isn't enough: the (now empty) element stays attached
    to the root, so ~219k husks still accumulate. Clearing the root after each
    yield drops them — the root's own attributes aren't needed."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing: {path}\nRun  python scripts/download_edrdg.py  first."
        )
    size_mb = path.stat().st_size / (1024 * 1024)
    log.info("Streaming %s  (%.0f MB) …", path.name, size_mb)
    events = ET.iterparse(path, events=("start", "end"))
    _, root = next(events)
    for event, elem in events:
        if event == "end" and elem.tag == tag:
            yield elem
            root.clear()


# ── JMdict parsing ────────────────────────────────────────────────────────────

def _pri_tags(elem, tag: str) -> set[str]:
    return {p.text or "" for p in elem.findall(tag)}


def _commonness(pris: set[str], freq_band: int | None) -> float:
    """Real-valued frequency prior for the FormulaQuery — the max of three
    signals: 1.0 for tier-1 common markers, 0.5 for tier-2-only markers
    (news2/ichi2/gai2 — genuinely common but second-tier), and an nf
    gradient of 0.75 (nf01, top-500) down to ~0.02 (nf48)."""
    score = 0.0
    if pris & COMMON_PRI:
        score = 1.0
    elif pris & COMMON_PRI2:
        score = 0.5
    if freq_band is not None:
        score = max(score, round(0.75 * (49 - freq_band) / 48, 4))
    return score


def _wf_score(kanji: str | None, kana: str | None, kana_pref: bool) -> float:
    """Corpus word frequency as a Zipf value (~0-7: 7 = "the"-tier, 3 = rare).

    The canonical-ranking prior. Unlike JMdict's own signals it is continuous
    and covers every surface form, which is what separates near-synonyms that
    both carry tier-1 pri markers and the same nf band (仕事 5.68 / 作業 4.91)
    and what ranks katakana loanwords correctly in both directions — canonical
    ones score high (ゲーム 5.62, ドア 4.58), translations of convenience low
    (キャット 3.14, ファイア 3.59). JMdict's nfNN bands express neither.

    Scored on the form the word is actually written in: the kanji form, or the
    kana form when there is no kanji or JMdict tags the entry &uk; ("usually
    written using kana alone" — ありがとう 5.70, not 有難う 3.2). Never the max
    of both: a one-mora reading collides with a far more frequent particle and
    would hand rare single-kanji entries a huge score (屁/へ 6.08, 戸/と 7.21).
    """
    form = kana if (kana_pref or not kanji) else kanji
    if not form:
        return 0.0
    # wordfreq has no phrase frequencies: for multi-token input it returns
    # roughly the average of the tokens — a phrase is strictly rarer than
    # its rarest token, so charge one Zipf decade (10x) per extra token — still
    # far more conservative than the ~9 decades independence would imply.
    # Tokenized by Sudachi (the runtime segmenter) — wordfreq's own `tokenize`
    # needs mecab-python3/ipadic, which are no longer dependencies; the shim
    # in _ja_tokenizer routes wordfreq's ja path through Sudachi instead.
    # Without Sudachi, return 0.0 — a wrong score is worse than none.
    if _ja_tokenizer() is None:
        return 0.0
    # zipf_frequency tokenizes `form` through the shim; _ja_tokens is cached,
    # so this second call for the token count is a dict hit, not a re-parse.
    return round(zipf_frequency(form, "ja") - max(0, len(_ja_tokens(form)) - 1), 3)


@lru_cache(maxsize=1)
def _ja_tokenizer():
    """Sudachi tokenizer — also shims `wordfreq.mecab` so every ja lookup
    (zipf_frequency tokenizes internally) uses it instead of the removed
    mecab-python3. wordfreq lazy-imports wordfreq.mecab per call, so a
    sys.modules stub installed before the first lookup is enough."""
    try:
        from sudachipy import Dictionary
        for name in ("core", "small"):
            try:
                tok = Dictionary(dict=name).tokenizer()
                break
            except Exception:
                pass
        else:
            raise RuntimeError("no sudachidict package")
    except Exception:
        log.warning("sudachipy unavailable — wf_score returns 0 for all entries")
        return None
    import types
    shim = types.ModuleType("wordfreq.mecab")
    shim.mecab_tokenize = lambda text, lang: _ja_tokens(text) if lang == "ja" else [text]
    sys.modules.setdefault("wordfreq.mecab", shim)
    return tok


_HEAD_SKIP = ("to ", "and ", "or ", "be ")  # verb/conj-gloss openers


def _gloss_head_words(glosses: list[str]) -> set[str]:
    """Head word of every multi-word gloss ("apartment building" →
    "apartment") so a one-word query matches phrase-glossed entries. Verb
    glosses ("to eat" — head word "to") and non-alphabetic heads are exempt;
    the head word is one extra MatchValue candidate, not a ranking signal,
    so the first-sense exclusivity stays with primary_gloss_keys."""
    out: set[str] = set()
    for m in glosses:
        key = gloss_key(m)
        words = key.split()
        if len(words) < 2 or not words[0].isalpha() or key.startswith(_HEAD_SKIP):
            continue
        out.add(words[0])
    return out


@lru_cache(maxsize=65_536)
def _ja_tokens(text: str) -> list[str]:
    """Sudachi surfaces for `text`. The main win is deduping the back-to-back
    pair of lookups per entry (wordfreq shim + the len() call in _wf_score),
    which any size covers; the bigger bound adds cross-entry reuse — headword
    forms repeat across senses — without risking the 512 MB-class build hosts."""
    return [m.surface() for m in _ja_tokenizer().tokenize(text)]


def _entry_to_chunk(entry: ET.Element) -> dict | None:
    word_id = entry.findtext("ent_seq")

    # Sense-level POS texts (entity-resolved: "Godan verb with 'ru' ending"…)
    # drive the inflection table — see app/conjugation.py.
    pos_texts = {p.text for p in entry.findall("sense/pos") if p.text}

    kanji_forms: list[str] = []
    readings: list[str] = []
    reading_restrictions: dict[str, list[str]] = {}
    ke_inf: dict[str, list[str]] = {}
    pris: set[str] = set()
    primary_kanji: str | None = None
    primary_kana: str | None = None

    for k in entry.findall("k_ele"):
        keb = k.findtext("keb")
        if not keb:
            continue
        kanji_forms.append(keb)
        k_pris = _pri_tags(k, "ke_pri")
        pris |= k_pris
        if primary_kanji is None and k_pris & COMMON_PRI:
            primary_kanji = keb
        # Per-form usage labels (sK search-only / rK rare / ateji / io / iK /
        # oK / ik) — capture-only; the variant-forms package owns display.
        if labels := [c for inf in k.findall("ke_inf")
                      if (c := _entity_code(inf.text))]:
            ke_inf[keb] = labels
    if primary_kanji is None and kanji_forms:
        primary_kanji = kanji_forms[0]

    for r in entry.findall("r_ele"):
        reb = r.findtext("reb")
        if not reb:
            continue
        readings.append(reb)
        r_pris = _pri_tags(r, "re_pri")
        pris |= r_pris
        if primary_kana is None and r_pris & COMMON_PRI:
            primary_kana = reb
        # r_ele↔k_ele pairing (what jmdict-simplified called appliesToKanji):
        # re_nokanji = reading-only (empty list); re_restr = applies only to
        # the listed keb. Sense-level stagk/stagr pairing is dropped, as it
        # was in the JSON→chunk flattening.
        if r.find("re_nokanji") is not None:
            reading_restrictions[reb] = []
        elif (restr := [x.text for x in r.findall("re_restr") if x.text]):
            reading_restrictions[reb] = restr
    if primary_kana is None and readings:
        primary_kana = readings[0]
    if primary_kana is None:
        return None  # can't embed a word with no kana

    is_common = bool(pris & COMMON_PRI)
    nf_bands = [int(m[1]) for p in pris if (m := _NF_RE.fullmatch(p))]
    freq_band = min(nf_bands) if nf_bands else None

    meanings: list[str] = []
    primary_meanings: list[str] = []
    example_sentences: list[dict] = []
    xrefs: list[dict] = []
    s_inf: list[str] = []
    seen_xref: set[tuple] = set()
    kana_pref = False
    for i, sense in enumerate(entry.findall("sense")):
        # &uk; — "word usually written using kana alone"; the entity resolves to
        # that text, so match on it rather than the entity name. First sense
        # only: 犬 carries &uk; on a minor "snitch" sense, and honouring that
        # would score the entry as いぬ (3.53) instead of 犬 (5.10).
        if i == 0:
            kana_pref = any(
                m.text and "kana alone" in m.text for m in sense.findall("misc"))
            # First-sense usage notes — capture-only until the note-line UI
            # ships (JMdict-authored English, e.g. "usu. as …").
            s_inf = [s.text for s in sense.findall("s_inf") if s.text]
        for gloss in sense.findall("gloss"):
            if gloss.get(XML_LANG, "eng") == "eng" and gloss.text:
                meanings.append(gloss.text)
                if i == 0:
                    primary_meanings.append(gloss.text)
        for ex in sense.findall("example"):
            jpn = eng = None
            for s in ex.findall("ex_sent"):
                lang = s.get(XML_LANG, "eng")
                if lang == "jpn" and jpn is None:
                    jpn = s.text
                elif lang == "eng" and eng is None:
                    eng = s.text
            if jpn and eng:
                example_sentences.append({"japanese": jpn, "english": eng})
        for x in sense.findall("xref"):
            key = (x.get("seq") or "", x.text or "")
            if key in seen_xref:
                continue
            seen_xref.add(key)
            # type is a REQUIRED attr ("see"/"ant"/"syn") — dictionary-
            # authoritative relations, unlike the kanji-overlap `related`
            # computed at render time. Shipped under `xrefs` to keep the
            # two datasets distinct.
            xrefs.append({"seq": key[0], "text": key[1], "type": x.get("type") or "see"})

    if not meanings:
        return None

    lsource = []
    for ls in entry.findall("lsource"):
        item = {"lang": ls.get(XML_LANG, "eng"), "text": ls.text or ""}
        # ls_type="part" marks a partial source phrase; ls_wasei="y" marks a
        # Japanese coinage built from source-language words (wasei-eigo) —
        # both capture-only for now.
        if ls.get("ls_type") == "part":
            item["type"] = "part"
        if ls.get("ls_wasei") == "y":
            item["wasei"] = True
        lsource.append(item)
    notes = [i.text for i in entry.findall("info") if i.text]

    # Sense-level unions (entry-level tags — the accepted flattening
    # tradeoff): POS badges, misc register markers, domain fields, dialects.
    pos_tags = _coded_tags(pos_texts, _POS_TAG_MAP, _POS_ORDER)
    misc_tags = _coded_tags(
        (m.text for m in entry.findall("sense/misc") if m.text),
        _MISC_TAG_MAP, _MISC_ORDER)
    field_tags = sorted({f.text for f in entry.findall("sense/field")
                         if f.text and _entity_code(f.text)})
    code_to_text = _entities()[0]
    dial_codes = {_entity_code(d.text) for d in entry.findall("sense/dial")}
    dial_codes.discard(None)
    dial = [{"code": c, "name": code_to_text[c]} for c in sorted(dial_codes)]

    # Display text: primary headword + reading + glosses. The dense
    # vector is built from glosses only at ingest time. Example sentences
    # stay payload-only.
    display = primary_kanji or primary_kana
    kept = meanings
    text = f"{display} [{primary_kana}]: {', '.join(kept[:3])}"
    # BM25 index text: every variant form + reading, not just the primaries —
    # the `ja` route is BM25-only, so a hiragana query like しまうま can only
    # hit if the kana itself is indexed (it isn't the primary reading here,
    # シマウマ is). Variants are dictionary identity, not example-sentence noise.
    sparse_text = f"{' '.join(kanji_forms + readings)}: {', '.join(kept)}"

    chunk = {
        "id": word_id,
        "kanji_form": primary_kanji,
        "reading": primary_kana,
        "meanings": kept,
        # Normalised glosses for exact-match filtering (see
        # app.query_rewrite.gloss_keys). Multi-word glosses also index their
        # head word ("apartment building" → also "apartment") so a one-word
        # query can land the full-phrase-glossed entry — アパート's own
        # primary senses are all 2-word phrases, which left マンション (a
        # single-word gloss) as the top 'apartment' hit. Verb-gloss keys
        # ("to eat") are exempt: their head word is just "to".
        "gloss_keys": sorted(
            {k for m in kept for k in gloss_keys(m)} | _gloss_head_words(kept)),
        # Gloss keys of the FIRST sense only — "is this English word what the
        # entry primarily means?". Without it, a frequency prior is actively
        # harmful: 足 ("leg") lists "money" as a minor sense and would beat
        # お金 on frequency alone; 委員長 lists "chair" and beats 椅子.
        "primary_gloss_keys": sorted(
            {k for m in primary_meanings for k in gloss_keys(m)}
            | _gloss_head_words(primary_meanings)),
        # Gloss keys of the FIRST gloss of the FIRST sense — the entry's
        # headline translation ("is this word what the entry leads with?").
        # JMdict orders a sense's glosses by centrality, so the first one is
        # the primary translation and the rest are refinements: 行く lists
        # "to leave (for)" as gloss 4, 頼む lists "to ask" as gloss 3, while
        # 出る/問う/尋ねる/海 lead with "to leave"/"to ask"/"sea". Used as a
        # small frequency-weighted bonus on top of the canonical prior — it
        # separates a true translation pair from a broad sense that happens to
        # mention the query late (see HEAD_BONUS in app/retrieval.py).
        "head_gloss_keys": sorted(
            {k for m in primary_meanings[:1] for k in gloss_keys(m)}),
        "example_sentences": example_sentences[:5],
        "text": text,
        "sparse_text": sparse_text,
        "is_common": is_common,
        "commonness": _commonness(pris, freq_band),
        # Corpus frequency prior for ranking — see _wf_score. JMdict's own
        # commonness/freq_band stay above for display and ingest filtering, but
        # they are too coarse to rank with (500-word nf buckets, binary pri).
        "wf_score": _wf_score(primary_kanji, primary_kana, kana_pref),
    }
    # Inflection table for verb/adjective entries (see app/conjugation.py):
    # the render rows plus a flat keyword list so a typed inflection
    # (走った) exact-matches this very entry.
    if inflected := conjugate(pos_texts, primary_kanji, primary_kana):
        chunk["inflected_forms"] = inflected
        chunk["infl_forms"] = sorted(
            {r["surface"] for r in inflected} | {r["kana"] for r in inflected if r.get("kana")})
    # Optional payload fields — written only when present to keep chunks.json lean.
    if freq_band is not None:
        chunk["freq_band"] = freq_band
    if len(kanji_forms) > 1:
        chunk["kanji_forms"] = kanji_forms
    if len(readings) > 1:
        chunk["readings"] = readings
    if reading_restrictions:
        chunk["reading_restrictions"] = reading_restrictions
    if ke_inf:
        chunk["ke_inf"] = ke_inf
    if xrefs:
        chunk["xrefs"] = xrefs
    if pos_tags:
        chunk["pos"] = pos_tags
    if misc_tags:
        chunk["misc"] = misc_tags
    if field_tags:
        chunk["field_tags"] = field_tags
    if dial:
        chunk["dial"] = dial
    if s_inf:
        chunk["s_inf"] = s_inf
    if lsource:
        chunk["lsource"] = lsource
    if notes:
        chunk["notes"] = notes
    return chunk


def build_word_chunks() -> tuple[list[dict], dict[str, list[str]]]:
    """
    Convert JMdict entries into flat dicts suitable for embedding + Qdrant
    storage. Also returns kanji_to_ids: maps each kanji character → list of
    word IDs that use it (for the common-words-per-kanji index).
    """
    chunks: list[dict] = []
    kanji_to_ids: dict[str, list[str]] = defaultdict(list)

    total = skipped = 0
    for entry in iter_elements(RAW_DIR / JMDICT_XML, "entry"):
        total += 1
        chunk = _entry_to_chunk(entry)
        if chunk is None:
            skipped += 1
            continue
        chunks.append(chunk)
        if chunk["kanji_form"]:
            for ch in chunk["kanji_form"]:
                if is_kanji(ch):
                    kanji_to_ids[ch].append(chunk["id"])

    log.info(
        "  → %s chunks built from %s entries  (%s skipped - no meaning)",
        f"{len(chunks):,}", f"{total:,}", f"{skipped:,}",
    )
    if _UNMAPPED:
        log.warning(
            "  %s element texts not in the DOCTYPE entity table (dropped): %s",
            f"{sum(_UNMAPPED.values()):,}",
            ", ".join(f"{t!r}x{n}" for t, n in _UNMAPPED.most_common(10)),
        )
    return chunks, dict(kanji_to_ids)


# ── KANJIDIC2 parsing ─────────────────────────────────────────────────────────

def _int_or_none(text: str | None) -> int | None:
    return int(text) if text else None


def build_kanji_table(
    kanji_to_ids: dict[str, list[str]],
    id_to_chunk: dict[str, dict],
) -> dict[str, dict]:
    """
    Build a flat lookup table:  kanji_literal → details dict.

    Same output schema as the JSON pipeline produced: English meanings
    (m_lang absent = English), on/kun'yomi, stroke count, grade, frequency,
    JLPT level, and up to 10 common words that use the kanji.
    """
    table: dict[str, dict] = {}
    total = 0
    for char in iter_elements(RAW_DIR / KANJIDIC_XML, "character"):
        total += 1
        literal = char.findtext("literal")
        if not literal:
            continue

        misc = char.find("misc")
        stroke_count = grade = freq = jlpt = None
        if misc is not None:
            stroke_count = _int_or_none(misc.findtext("stroke_count"))
            grade = _int_or_none(misc.findtext("grade"))
            freq = _int_or_none(misc.findtext("freq"))
            jlpt = _int_or_none(misc.findtext("jlpt"))

        on_yomi: list[str] = []
        kun_yomi: list[str] = []
        meanings: list[str] = []
        rm = char.find("reading_meaning")
        if rm is not None:
            for group in rm.findall("rmgroup"):
                for reading in group.findall("reading"):
                    t, v = reading.get("r_type"), reading.text
                    if t == "ja_on":
                        on_yomi.append(v)
                    elif t == "ja_kun":
                        kun_yomi.append(v)
                meanings.extend(
                    meaning.text
                    for meaning in group.findall("meaning")
                    if meaning.get("m_lang", "en") == "en" and meaning.text
                )

        # ── Common words using this kanji ─────────────────────────────────────
        # Ranked, not file order: JMdict emits entries in document order, so a
        # raw word_ids[:30] slice could skip the kanji's actual top words when
        # they happen to sit deeper in the file. Name-tagged entries (proper
        # nouns — composers, places, orgs; misc "name") are excluded: this
        # pool feeds both the kanji card's common words and related_words(),
        # where Picasso/Mozart chips are noise, not relations.
        pool = [id_to_chunk[w] for w in kanji_to_ids.get(literal, []) if w in id_to_chunk]
        pool = [c for c in pool if "name" not in (c.get("misc") or [])]
        ranked = sorted(
            pool,
            key=lambda c: (bool(c.get("is_common")), c.get("commonness", 0.0), c.get("wf_score", 0.0)),
            reverse=True,
        )
        common_words = [
            {"kanji_form": c["kanji_form"], "reading": c["reading"], "meanings": c["meanings"]}
            for c in ranked[:10]
        ]

        table[literal] = {
            "literal": literal,
            "codepoint_hex": f"{ord(literal):05x}",
            "meanings": meanings,
            "on_yomi": on_yomi,
            "kun_yomi": kun_yomi,
            "stroke_count": stroke_count,
            "grade": grade,
            "freq": freq,
            "jlpt_level": jlpt,
            "common_words": common_words,
        }

    log.info("  → %s kanji entries built (of %s characters)", f"{len(table):,}", f"{total:,}")
    return table


# ── Entry point ───────────────────────────────────────────────────────────────

CHUNKS_META = PROC_DIR / "chunks.meta.json"


def _raw_generation(xml_name: str) -> str | None:
    """Upstream generation date recorded by download_edrdg's .meta.json sidecar."""
    try:
        return json.loads((RAW_DIR / f"{xml_name}.meta.json").read_text(encoding="utf-8")).get(
            "generation_date_from_header"
        )
    except (OSError, ValueError):
        return None


def outputs_current() -> bool:
    """True when the processed outputs match the on-disk raw XML — same schema
    stamp and same upstream generation dates, so a rebuild would change nothing."""
    try:
        meta = json.loads(CHUNKS_META.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if meta.get("schema") != CHUNKS_SCHEMA:
        return False
    for xml_name, key in ((JMDICT_XML, "jmdict_generation"), (KANJIDIC_XML, "kanjidic2_generation")):
        gen = _raw_generation(xml_name)
        if gen is None or gen != meta.get(key):
            return False
    return all((PROC_DIR / name).exists()
               for name in ("chunks.json", "kanji_table.json", "headword_index.marisa"))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    log.info("=== Step 1: Build word chunks from %s ===", JMDICT_XML)
    chunks, kanji_to_ids = build_word_chunks()
    id_to_chunk = {c["id"]: c for c in chunks}

    log.info("=== Step 2: Build kanji table from %s ===", KANJIDIC_XML)
    kanji_table = build_kanji_table(kanji_to_ids, id_to_chunk)

    log.info("=== Step 3: Save outputs ===")
    chunks_path = PROC_DIR / "chunks.json"
    kanji_path = PROC_DIR / "kanji_table.json"

    log.info("  Writing %s …", chunks_path.name)
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, separators=(",", ":"))

    log.info("  Writing %s …", kanji_path.name)
    with open(kanji_path, "w", encoding="utf-8") as f:
        json.dump(kanji_table, f, ensure_ascii=False, separators=(",", ":"))

    # Compact form→[entry, …] map for sentence splits, packed as a marisa
    # BytesTrie (~26 MB — small enough to commit and ship in the image,
    # unlike the ~70 MB JSON / ~340 MB in-memory dict it replaced). The app
    # falls back to a Qdrant scroll rebuild when the file is absent, through
    # the same add_entry/build_trie, so both paths produce identical tries.
    index: dict[str, list[dict]] = {}
    for c in chunks:
        add_entry(index, c)
    index_path = PROC_DIR / "headword_index.marisa"
    log.info("  Writing %s …", index_path.name)
    build_trie(index, index_path)

    # Sidecar stamps the schema + upstream generation dates: check_state()
    # trusts chunks.json only when this says the current build wrote it, and
    # outputs_current() uses it to skip a rebuild when upstream hasn't moved.
    meta = {
        "schema": CHUNKS_SCHEMA,
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "entries": len(chunks),
        "jmdict_generation": _raw_generation(JMDICT_XML),
        "kanjidic2_generation": _raw_generation(KANJIDIC_XML),
    }
    CHUNKS_META.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    total_examples = sum(len(c["example_sentences"]) for c in chunks)
    log.info(
        "Done.\n  chunks.json      %.1f MB  (%s chunks, %s example sentences)\n"
        "  kanji_table.json %.1f MB  (%s kanji characters)",
        chunks_path.stat().st_size / (1024 * 1024), f"{len(chunks):,}", f"{total_examples:,}",
        kanji_path.stat().st_size / (1024 * 1024), f"{len(kanji_table):,}",
    )


if __name__ == "__main__":
    main()
