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
    as a bare query; a trailing copula after a counter still rides along
    (2日です is the previous/merged behaviour)."""
    sentence = segment_japanese("2日です")
    assert [s["text"] for s in sentence] == ["2日です"]
    assert sentence[0]["reading"] == "ふつかです"
    bare = segment_japanese("2日")
    assert bare and bare[0]["text"] == "2日" and bare[0]["reading"] == "ふつか"


@pytest.mark.parametrize(
    "sentence,chips",
    [
        # Content word + terminal copula: the copula is its own chip.
        ("学生です", ["学生", "です"]),
        ("学生だ", ["学生", "だ"]),
        ("学生だった", ["学生", "だった"]),
        ("学生でした", ["学生", "でした"]),
        ("静かです", ["静か", "です"]),
        ("元気です", ["元気", "です"]),
        ("水です", ["水", "です"]),
        ("静かな部屋です", ["静かな", "部屋", "です"]),
        ("有名な人です", ["有名な", "人", "です"]),
        # Pronouns are content words too — the merged chip (何です) matches
        # no dictionary entry, so the copula splits off after them as well.
        ("何ですか", ["何", "です", "か"]),
        ("誰ですか", ["誰", "です", "か"]),
        ("それですね", ["それ", "です", "ね"]),
        ("あの店のケーキはとても美味しいです", None),
        # Auxiliary / particle / non-independent / continuative: merge as
        # before — the split must not disturb these.
        ("食べました", ["食べました"]),
        ("行かなかった", ["行かなかった"]),
        ("行きませんでした", ["行きませんでした"]),
        ("行かなかったです", ["行かなかったです"]),
        ("美しくないです", ["美しく", "ないです"]),
        ("美味しくなかったです", ["美味しく", "なかったです"]),
        ("食べるんです", ["食べる", "んです"]),
        ("学生じゃないです", ["学生じゃ", "ないです"]),
        ("2日です", ["2日です"]),
        ("7人でした", ["7人でした"]),
        ("山で", ["山で"]),
        ("学生で", ["学生で"]),
        # Past-tense auxiliary だ (助動詞-タ) must still merge.
        ("休んだ", ["休んだ"]),
        ("読んだ", ["読んだ"]),
        ("飲んだ", ["飲んだ"]),
    ],
)
def test_copula_is_its_own_chip(sentence: str, chips: list[str] | None) -> None:
    """です/だ are words after a content word, not inflection tails:
    美味しいです must not become a pseudo-headword that matches no dictionary
    entry or result card. Every auxiliary/particle case keeps the previous
    merged grouping."""
    segments = segment_japanese(sentence) or []
    texts = [s["text"] for s in segments]
    if chips is None:
        assert texts[-2:] == ["美味しい", "です"], texts
        assert all(s["text"] != "美味しいです" for s in segments)
    else:
        assert texts == chips, texts


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
