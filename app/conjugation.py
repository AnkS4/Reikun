"""
Inflection generation for JMdict verb/adjective entries.

Hand-authored suffix rules (~40 rows) applied at ingest build time — no
dependency beyond stdlib. Feeds two payload fields in scripts/build_chunks.py:

    inflected_forms — render rows ({form, surface, kana}) for the conjugation
                      table on word cards (ResultCard)
    infl_forms      — flat strings of every surface/kana so a typed inflection
                      (走った) exact-matches its entry via _exact_filter

Paradigms covered: godan (v5*), ichidan (v1), kuru-irregular (vk), suru
(vs — noun + する), and i-adjectives including the いい→よく irregulars.
Archaic nidan (v2/v4), the aru-class (v5aru) and auxiliary-only entries
generate nothing — a wrong row is worse than no row.

The pos texts are the entity-resolved JMdict strings ("Godan verb with 'ru'
ending", "Ichidan verb", "Kuru verb - special class", "noun or participle
which takes the aux. verb suru", "adjective (keiyoushi)") — exactly what
ElementTree hands the build script. The godan ROW comes from the actual
ending kana of the written form, not the entity letter, so one 9-cell chart
covers every godan class.

Row labels stay short and English — the UI localises its own chrome already
(the LATER i18n item in Plan.md).

Known limits, accepted: any Ichidan entry (見える, 大人しい…) gets the plain
ichidan rows even where a grammar nuanced one reads odd, and godan te-form
specials beyond 行く (行く→行って is regular; only truly irregular 五段 like
ござる skipped via the aru-class guard) are outside the chart.
"""

import re
from collections.abc import Iterable

_V5 = "godan"
_V1 = "ichidan"
_VK = "kuru"
_VS = "suru"
_ADJ = "adj-i"

_GODAN = re.compile(r"Godan verb with '(.{1,2})' ending")
_GODAN_IKU = "Godan verb - Iku/Yuku special class"   # 行く follows plain く-row rules
_VS_TAIL = "takes the aux. verb suru"                # &vs; &vs-c; &vs-i; &vs-s; …

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

# family choice: lowest priority number wins when an entry carries several
# (見る is Ichidan *and* auxiliary — the lexical paradigm beats the aux tag)
_PRIORITY = {_V1: 1, _V5: 2, _VK: 3, _VS: 4, _ADJ: 5}


def family(pos_texts: Iterable[str]) -> str | None:
    """The entry's inflection paradigm, None when it doesn't inflect."""
    picked: dict[int, str] = {}
    for text in pos_texts:
        if text == _GODAN_IKU:
            picked[_PRIORITY[_V5]] = _V5
        elif _GODAN.match(text) and "special class" not in text:
            picked[_PRIORITY[_V5]] = _V5
        elif text == "Ichidan verb":
            picked[_PRIORITY[_V1]] = _V1
        elif text == "Kuru verb - special class":
            picked[_PRIORITY[_VK]] = _VK
        elif _VS_TAIL in text:
            picked[_PRIORITY[_VS]] = _VS
        elif text == "adjective (keiyoushi)":
            picked[_PRIORITY[_ADJ]] = _ADJ
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
    # 行く/ゆくclass: the only ending-kana override in the chart (行った, not
    # 行いた) — the reason JMdict tags them a special class at all.
    rows_map = _V5_ROWS_IKU if _GODAN_IKU in texts else _V5_ROWS
    spellings: list[str] = []
    for form in (kanji, kana):
        if not form:
            continue
        if fam == _VS and not form.endswith("する"):
            form = form + "する"
        if form and form not in spellings:
            spellings.append(form)
    if not spellings:
        return []
    tables = [_inflect(fam, form, rows_map) for form in spellings]
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


def _inflect(fam: str, form: str, rows_map: dict[str, tuple[str, ...]] | None = None) -> dict[str, str]:
    """One paradigm applied to ONE spelling: label → inflected surface."""
    if fam == _V5:
        return _godan(form, rows_map or _V5_ROWS)
    if fam == _V1:
        return _ichidan(form)
    if fam == _VK:
        return _kuru(form)
    if fam == _VS:
        return _suru(form)
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


def _ichidan(form: str) -> dict[str, str]:
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
        "Imperative": stem + "ろ",
        "Conditional": stem + "れば",
    }


def _kuru(form: str) -> dict[str, str]:
    if not form.endswith("る"):
        return {}
    k_stem = form[:-1]
    stems = _KURU_STEMS.get(k_stem)
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
        "Conditional": polite + "れば",
    }


# 来(く)る splits its stems: the polite/past/te rows take the き-stem, the
# negative/potential/volitional/imperative rows the こ-stem. The kanji
# spelling keeps the same glyph for both (来ます / 来ない); the kana spelling
# switches (きます / こない) — hence per-spelling stem pairs.
_KURU_STEMS = {"来": ("来", "来"), "く": ("き", "こ")}


def _suru(form: str) -> dict[str, str]:
    if not form.endswith("する"):
        return {}
    stem = form[:-2]
    return {
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
