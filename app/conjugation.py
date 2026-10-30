"""
Inflection generation for JMdict verb/adjective entries.

Hand-authored suffix rules (~50 rows) applied at ingest build time — no
dependency beyond stdlib. Feeds two payload fields in scripts/build_chunks.py:

    inflected_forms — render rows ({form, surface, kana}) for the conjugation
                      table on word cards (ResultCard)
    infl_forms      — flat strings of every surface/kana so a typed inflection
                      (走った) exact-matches its entry via _exact_filter

Paradigms covered: godan (v5*) including the 問う u-class (問うた/問うて) and
the ある aru-class (ある→ない, Xがある→Xがない), ichidan (v1) including the
kureru special class, zuru (〜ずる = the 〜じる alternates), kuru-irregular
(vk, compound entries included), suru (vs — noun + する, the vs-s sound-change
compounds 愛する and the vs-i phrase verbs 気がする on a safe-row subset), and
i-adjectives including the いい→よく irregulars. Archaic paradigms (nidan
v2/v4, yodan, the su-verbs 愛す), the ある/である-family-as-tagged (irregular
ru verbs, handled properly in _aru_verb) and auxiliary-only entries generate
nothing — a wrong row is worse than no row.

The pos texts are the JMdict strings ("Godan verb with 'ru' ending", "Ichidan
verb", "Kuru verb - special class", "suru verb - special class", "suru verb -
included", "noun or participle which takes the aux. verb suru", "adjective
(keiyoushi)"± "yoi/ii class"…) — exactly what ElementTree hands the build
script. The godan ROW comes from the actual ending kana of the written form,
so one 9-cell chart covers every godan class.

Row labels stay short and English — the UI localises its own chrome already.

Known limits, accepted: the honorific ます-class verbs (いらっしゃる, なさる,
くださる, おっしゃる — JMdict's "-aru special class") and 御座る (mis-tagged
plain v5r but behaving identically) keep their い-insertion masu-forms out of
the chart rather than risk the paradigm's suspect cells (ございます-row of a
plain-v5 engine, ござった); the su-verbs (愛す, 期す) are left on the plain
v5s chart — 愛します/愛さない/愛せば check out natively, so excluding them for
the rare contested cells would cost a working table.
"""

import re
from collections.abc import Iterable

_V5 = "godan"
_V1 = "ichidan"
_VZ = "zuru"
_VK = "kuru"
_VS = "suru"
_AR = "aru"
_ADJ = "adj-i"

_GODAN = re.compile(r"Godan verb with '(.{1,2})' ending")
_GODAN_IKU = "Godan verb - Iku/Yuku special class"  # 行く follows plain く-row rules
_GODAN_U_SPECIAL = "Godan verb with 'u' ending (special class)"  # 問う/乞う/請う class
_GODAN_ARU = "Godan verb with 'ru' ending (irregular verb)"  # ある/である-family
_KURU_FALSE = "Kuru verb - special class"
_ZURU_VERB = "Ichidan verb - zuru verb (alternative form of -jiru verbs)"
_KURERU = "Ichidan verb - kureru special class"  # くれる behaves like plain ichidan
_VS_TAIL = "takes the aux. verb suru"  # &vs; &vs-c; …
_VS_SPECIAL = "suru verb - special class"  # &vs-s; 愛する/圧する (full paradigm)
_VS_INCLUDED = "suru verb - included"  # &vs-i; 気がする (phrase verbs — safe rows only)
_YOI_ADJ = "adjective (keiyoushi) - yoi/ii class"  # いい/かっこいい family

# godan ending kana → (i-row [ます/etc], a-row [ない/passive/causative],
#                      ta-form, te-form, e-row [potential/ば/ imperative],
#                      o-row [volitional])
_V5_ROWS = {
    "う": ("い", "わ", "った", "って", "え", "お"),
    "く": ("き", "か", "いた", "いて", "け", "こ"),
    "ぐ": ("ぎ", "が", "いだ", "いで", "げ", "ご"),
    "す": ("し", "さ", "した", "して", "せ", "そ"),
    "つ": ("ち", "た", "った", "って", "て", "と"),
    "ぬ": ("に", "な", "んだ", "んで", "ね", "の"),
    "ぶ": ("び", "ば", "んだ", "んで", "べ", "ぼ"),
    "む": ("み", "ま", "んだ", "んで", "め", "も"),
    "る": ("り", "ら", "った", "って", "れ", "ろ"),
}

# 行く/ゆく (JMdict "Godan verb - Iku/Yuku special class"): く does NOT shift
# to いた — 行った/行って, i.e. the た/て cells change only in that one row.
_V5_ROWS_IKU = {**_V5_ROWS, "く": ("き", "か", "った", "って", "け", "こ")}

# 問う/乞う/請う/厭う/恋う (JMdict "(special class)" u-ending): the った/って
# cells keep the う — 問うた/問うて (the historical お-row fusion), unlike
# 会った/会って for ordinary u-endings. Every other cell rides the う row.
_V5_ROWS_U = {**_V5_ROWS, "う": ("い", "わ", "うた", "うて", "え", "お")}

# family choice: lowest priority number wins when an entry carries several
# (見る is Ichidan *and* auxiliary — the lexical paradigm beats the aux tag)
_PRIORITY = {_V1: 1, _VZ: 2, _V5: 3, _VK: 4, _VS: 5, _AR: 6, _ADJ: 7}


def family(pos_texts: Iterable[str]) -> str | None:
    """The entry's inflection paradigm, None when it doesn't inflect."""
    picked: dict[int, str] = {}
    for text in pos_texts:
        if text == _GODAN_IKU:
            picked[_PRIORITY[_V5]] = _V5
        elif text == _GODAN_U_SPECIAL:
            # 問う-class: godan family, conjugate() picks the special rows map
            picked[_PRIORITY[_V5]] = _V5
        elif _GODAN_ARU == text:
            picked[_PRIORITY[_AR]] = _AR
        elif _GODAN.match(text) and "special class" not in text and "(irregular" not in text:
            picked[_PRIORITY[_V5]] = _V5
        elif text == "Ichidan verb" or text == _KURERU:
            picked[_PRIORITY[_V1]] = _V1
        elif text == _ZURU_VERB:
            picked[_PRIORITY[_VZ]] = _VZ
        elif text == _KURU_FALSE:
            picked[_PRIORITY[_VK]] = _VK
        elif _VS_TAIL in text or text == _VS_SPECIAL or text == _VS_INCLUDED:
            picked[_PRIORITY[_VS]] = _VS
        elif text == "adjective (keiyoushi)" or text == _YOI_ADJ:
            picked[_PRIORITY[_ADJ]] = _ADJ
        # "-aru special class" (いらっしゃる/なさる/くださる/おっしゃる) and the
        # 御座る tagpair fall through → excluded (see conjugate()); the plain
        # v5s su-verbs ride the standard godan chart
    return picked[min(picked)] if picked else None


def conjugate(pos_texts: Iterable[str], kanji: str | None, kana: str | None) -> list[dict[str, str]]:
    """[{form, surface, kana}] rows for the display table, in fixed order.

    The same suffix engine drives both spellings — the rows build from the
    primary written form (`kanji`, falling back to `kana`) and the reading
    supplies the `kana` column (e.g. 走り/はしり). A spelling that can't
    inflect under its family (missing reading, unexpected tail) is simply
    absent, and a family-less entry returns [] — never a guessed row.
    """
    texts = set(pos_texts)
    fam = family(texts)
    if fam is None or not (kanji or kana):
        return []
    # 御座る is JMdict-tagged plain v5r but conjugates like the -aru class
    # (ございます, not ござります) — skipping beats a half-wrong table.
    if fam == _V5 and kana == "ござる":
        return []
    # vs-i ("suru verb - included") phrase verbs take the safe-row subset only
    # when joined by no other suru tag: 気がする gets 気がします/しない/した/して,
    # not the mechanical 気ができる/される/しろ nonsense. する with no noun stem
    # (為る) counts as included-only.
    vs_only_included = _VS_INCLUDED in texts and not ({_VS_TAIL, _VS_SPECIAL} & texts)
    # 行く/ゆくclass: the only ending-kana override in the chart (行った, not
    # 行いた) — the reason JMdict tags them a special class at all.
    rows_map = _V5_ROWS
    if _GODAN_IKU in texts:
        rows_map = _V5_ROWS_IKU
    elif _GODAN_U_SPECIAL in texts:
        rows_map = _V5_ROWS_U
    spellings: list[str] = []
    for form in (kanji, kana):
        if not form:
            continue
        if fam == _VS and not form.endswith("する"):
            # 為る (kana する): the first spelling獲 already ends with する and
            # covers the rows — don't concatenate onto it.
            if kana and kana.endswith("する"):
                continue
            form = form + "する"
        if form and form not in spellings:
            spellings.append(form)
    if not spellings:
        return []
    tables = [
        _inflect(fam, form, rows_map, vs_only_included, imp="" if _KURERU in texts else "ろ") for form in spellings
    ]
    tables = [t for t in tables if t]
    if not tables:
        return []
    out: list[dict[str, str]] = []
    for label, surfaces in _zip_rows(tables):
        cells = {"surface": surfaces[0], "kana": surfaces[1] if len(surfaces) > 1 else None}
        row = {"form": label, **{k: v for k, v in cells.items() if v}}
        if len(row) > 1:
            out.append(row)
    return out


def _inflect(
    fam: str, form: str, rows_map: dict[str, tuple[str, ...]], vs_only_included: bool = False, imp: str = "ろ"
) -> dict[str, str]:
    """One paradigm applied to ONE spelling: label → inflected surface."""
    if fam == _V5:
        return _godan(form, rows_map or _V5_ROWS)
    if fam == _V1:
        return _ichidan(form, imp)
    if fam == _VZ:
        return _zuru(form)
    if fam == _VK:
        return _kuru(form)
    if fam == _VS:
        return _suru(form, vs_only_included)
    if fam == _AR:
        return _aru_verb(form)
    return _adjective(form)


def _godan(form: str, rows_map: dict[str, tuple[str, ...]]) -> dict[str, str]:
    row = rows_map.get(form[-1])
    if not row:
        return {}
    stem = form[:-1]
    masu, neg, ta, te, e_row, o_row = row
    return {
        "Dictionary": form,
        "Polite present": stem + masu + "ます",
        "Polite negative": stem + masu + "ません",
        "Polite past": stem + masu + "ました",
        "Polite past negative": stem + masu + "ませんでした",
        "Negative": stem + neg + "ない",
        "Past": stem + ta,
        "Past negative": stem + neg + "なかった",
        "Te-form": stem + te,
        "Potential": stem + e_row + "る",
        "Passive": stem + neg + "れる",
        "Causative": stem + neg + "せる",
        "Volitional": stem + o_row + "う",
        "Imperative": stem + e_row,
        "Conditional": stem + e_row + "ば",
    }


def _ichidan(form: str, imperative: str = "ろ") -> dict[str, str]:
    if not form.endswith("る"):
        return {}
    stem = form[:-1]
    return {
        "Dictionary": form,
        "Polite present": stem + "ます",
        "Polite negative": stem + "ません",
        "Polite past": stem + "ました",
        "Polite past negative": stem + "ませんでした",
        "Negative": stem + "ない",
        "Past": stem + "た",
        "Past negative": stem + "なかった",
        "Te-form": stem + "て",
        # Modern Japanese rents the same surface for both — one row, one label.
        "Potential / Passive": stem + "られる",
        "Causative": stem + "させる",
        "Volitional": stem + "よう",
        # くれる's class tag exists for exactly this cell: bare stem くれ,
        # never the plain-ichidan くれろ
        "Imperative": stem + imperative,
        "Conditional": stem + "れば",
    }


def _zuru(form: str) -> dict[str, str]:
    """〜ずる verbs inflect like their 〜じる alternates (信ずる → 信じます):
    the dictionary row keeps the ずる spelling, every other cell rides the
    plain ichidan engine."""
    if not form.endswith("ずる"):
        return {}
    table = _ichidan(form[:-2] + "じる")
    if not table:
        return {}
    table["Dictionary"] = form
    return table


def _kuru(form: str) -> dict[str, str]:
    if not form.endswith("る"):
        return {}
    k_stem = form[:-1]
    stems = _KURU_STEMS.get(k_stem)
    if not stems and k_stem.endswith("来"):
        stems = (k_stem, k_stem)  # compound kanji: 連れて来 + ます/ない/shared stem
    elif not stems and k_stem.endswith("く"):
        # compound kana: 持ってくる → 持ってき + ます / 持ってこ + ない
        stems = (k_stem[:-1] + "き", k_stem[:-1] + "こ")
    if not stems:
        return {}
    polite, o_stem = stems
    return {
        "Dictionary": form,
        "Polite present": polite + "ます",
        "Polite negative": polite + "ません",
        "Polite past": polite + "ました",
        "Polite past negative": polite + "ませんでした",
        "Negative": o_stem + "ない",
        "Past": polite + "た",
        "Past negative": o_stem + "なかった",
        "Te-form": polite + "て",
        "Potential / Passive": o_stem + "られる",
        "Causative": o_stem + "させる",
        "Volitional": o_stem + "よう",
        "Imperative": o_stem + "い",
        # the provisional rides the plain く-stem — くれば, never きれば
        "Conditional": k_stem + "れば",
    }


# 来(く)る splits its stems: the polite/past/te rows take the き-stem, the
# negative/potential/volitional/imperative rows the こ-stem. The kanji
# spelling keeps the same glyph for both (来ます / 来ない); the kana spelling
# switches (きます / こない) — hence per-spelling stem pairs.
_KURU_STEMS = {"来": ("来", "来"), "く": ("き", "こ")}


def _suru(form: str, included_only: bool = False) -> dict[str, str]:
    """The noun+する paradigm; 為る/する with an empty stem gets the same rows.

    The &vs-i; phrase verbs (気がする, 〜にする) ride a predicate subset: their
    potential/causative/volitional/imperative cells don't exist mechanically
    (気ができる,  Shall がしろ) so only the rows a native speaker would grant
    make the table.
    """
    if not form.endswith("する"):
        return {}
    stem = form[:-2]
    full = {
        "Dictionary": form,
        "Polite present": stem + "します",
        "Polite negative": stem + "しません",
        "Polite past": stem + "しました",
        "Polite past negative": stem + "しませんでした",
        "Negative": stem + "しない",
        "Past": stem + "した",
        "Past negative": stem + "しなかった",
        "Te-form": stem + "して",
        "Potential": stem + "できる",
        "Passive": stem + "される",
        "Causative": stem + "させる",
        "Volitional": stem + "しよう",
        "Imperative": stem + "しろ",
        "Conditional": stem + "すれば",
    }
    if not included_only:
        return full
    return {k: v for k, v in full.items() if k not in ("Potential", "Passive", "Causative", "Volitional", "Imperative")}


def _aru_verb(form: str) -> dict[str, str]:
    """The ある-family ("Godan verb with 'ru' ending (irregular verb)"):
    ある/である/Xがある. Only a subset of the godan cells survive — ある has
    no (あ)らない negative, no potential/passive/causative; the negative
    replaces the whole ある tail (ある→ない, 恩がある→恩がない)."""
    if not form.endswith("る"):
        return {}
    return {
        "Dictionary": form,
        "Polite present": form[:-1] + "り" + "ます",
        "Polite negative": form[:-1] + "り" + "ません",
        "Polite past": form[:-1] + "り" + "ました",
        "Polite past negative": form[:-1] + "り" + "ませんでした",
        "Negative": form[:-2] + "ない",
        "Past": form[:-1] + "った",
        "Past negative": form[:-2] + "なかった",
        "Te-form": form[:-1] + "って",
        "Volitional": form[:-1] + "ろう",
        "Conditional": form[:-1] + "れば",
    }


def _adjective(form: str) -> dict[str, str]:
    # いい/かっこいい irregular: the stem is よ (いい→よくない); everything else
    # drops the final い. Polite past rides on the plain past (楽しかったです).
    stem = form[:-2] + "よ" if form.endswith("いい") else form[:-1]
    if not stem:
        return {}
    return {
        "Dictionary": form,
        "Polite present": form + "です",
        "Negative": stem + "くない",
        "Past": stem + "かった",
        "Past negative": stem + "くなかった",
        "Te-form": stem + "くて",
        "Adverbial": stem + "く",
        "Conditional": stem + "ければ",
    }


def _zip_rows(tables: list[dict[str, str]]) -> list[tuple[str, tuple[str | None, ...]]]:
    """Align the per-spelling tables on their labels — the first table owns
    display order, so columns never drift apart between spellings."""
    return [(key, tuple(t.get(key) for t in tables)) for key in tables[0]]
