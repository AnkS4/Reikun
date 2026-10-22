"""segment_japanese() behavior tests — run offline (the headword trie is
committed), so only the parse is covered; the promoted-results path that
reads `_stem` lives behind a Qdrant-bound search."""

import pytest

from app.retrieval import segment_japanese


@pytest.mark.parametrize(
    "inflected,root,reading",
    [
        ("走った", "走る", "はしる"),
        ("食べました", "食べる", "たべる"),
        ("行かなかった", "行く", "いく"),
        ("泳げます", "泳ぐ", "およぐ"),
        ("見ました", "見る", "みる"),
        ("高かった", "高い", "たかい"),
    ],
)
def test_inflected_word_carries_root_entry(inflected: str, root: str, reading: str) -> None:
    """The inflection group embeds the committed dictionary entry of its
    stem — the root verb/adjective the conjugated surface derives from."""
    segments = segment_japanese(inflected)
    assert segments and len(segments) == 1
    stem = segments[0].get("_stem")
    assert stem, f"{inflected}: no _stem on {segments}"
    assert stem["kanji_form"] == root
    assert stem["reading"] == reading
    assert stem["meanings"]


def test_sentence_inflected_chips_carry_stems() -> None:
    """Inside a full sentence, chips rooted in a resolved verb still embed
    the stem entry (事情があって休んだ → 休んだ → 休む); chips whose stem is
    a particle/auxiliary get none."""
    segments = segment_japanese("事情があって休んだ")
    assert segments
    stems = [s.get("_stem") for s in segments]
    assert any(stems)  # at least the main verb resolves


def test_stem_does_not_leak_into_chip_whitelist_fields() -> None:
    """segment_chip() shapes the API chip payload; _stem is internal-only."""
    from app.render import segment_chip

    chip = segment_chip(next(s for s in segment_japanese("走った")))
    assert set(chip) == {"text", "kanji_form", "reading", "meanings",
                         "gloss", "ruby", "options", "approx"}


# ---- Number x counter reading table ----

@pytest.mark.parametrize(
    "num,counter,reading",
    [
        ("2", "日", "ふつか"),
        ("3", "日", "みっか"),
        ("7", "日", "なのか"),
        ("9", "日", "ここのか"),
        ("13", "日", "じゅうみっか"),
        ("23", "日", "にじゅうみっか"),
        ("14", "日", "じゅうよっか"),
        ("20", "日", "はつか"),
        ("12", "日", ""),  # じゅうににち is regular — no furigana over honesty
        ("25", "日", ""),  # the S3 bug case — never にじゅうごか
        ("1", "日", ""),  # ついたち vs いちにち: leave to the entry
        ("1", "人", "ひとり"),
        ("2", "人", "ふたり"),
        ("4", "人", "よにん"),
        ("7", "人", ""),  # しちにん is regular
        ("4", "時", "よじ"),
        ("9", "時", "くじ"),
        ("3", "時", ""),
        ("20", "歳", "はたち"),
        ("10", "分", "じゅっぷん"),
        ("15", "分", ""),  # じゅうごふん untabled
        ("25", "歳", ""),  # にじゅうごさい is regular
        ("あ", "日", ""),  # not a numeral
    ],
)
def test_counter_reading_table(num: str, counter: str, reading: str) -> None:
    from app.retrieval import _counter_reading

    assert _counter_reading(num, counter) == reading


def test_counter_chip_in_sentence_and_alone() -> None:
    """The table reading lands on the fused chip both inside a sentence and
    as a bare query, and the counter's inflection tail joins the ruby."""
    assert segment_japanese("2日です")[0]["reading"] == "ふつかです"
    bare = segment_japanese("2日")
    assert bare and bare[0]["text"] == "2日" and bare[0]["reading"] == "ふつか"


@pytest.mark.parametrize(
    "n,kanji",
    [
        (10, "十"), (25, "二十五"), (13, "十三"), (300, "三百"),
        (4000, "四千"), (1111, "一千一百十一"), (1, "一"), (20, "二十"),
    ],
)
def test_kanji_number(n: int, kanji: str) -> None:
    from app.retrieval import _kanji_number

    assert _kanji_number(n) == kanji


@pytest.mark.parametrize(
    "query,alias",
    [
        ("25日", "二十五日"),  # ２５日/二十五日 entries exist for both readings
        ("1人", "一人"),
        ("2日", "二日"),
        ("4時", "四時"),
        ("25kg", None),  # untabled counter unit
        ("12345日", None),  # beyond the alias ε-range
        ("二十五日", None),  # already kanji-spelled
        ("train", None),
    ],
)
def test_counter_alias(query: str, alias: str | None) -> None:
    from app.retrieval import _counter_alias

    assert _counter_alias(query) == alias
