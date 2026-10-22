"""Offline tests for the conjugation table (app/conjugation.py) and the
gloss head-word keys (scripts/build_chunks.py). Generation-only — no Qdrant."""

from app.conjugation import conjugate, family

GODAN_RU = ["Godan verb with 'ru' ending"]
V1_POSES = ["Ichidan verb"]
KURU = ["Kuru verb - special class"]
VS = ["noun or participle which takes the aux. verb suru"]
ADJ_I = ["adjective (keiyoushi)"]

def row_map(pos, kanji, kana) -> dict[str, dict]:
    return {r["form"]: r for r in conjugate(pos, kanji, kana)}


def test_family_selection() -> None:
    assert family(V1_POSES) == "ichidan"
    assert family(GODAN_RU) == "godan"
    assert family(KURU) == "kuru"
    assert family(VS) == "suru"
    assert family(ADJ_I) == "adj-i"
    # 見る carries auxiliary-verb tags alongside the lexical one — paradigm wins
    assert family([*V1_POSES, "auxiliary verb", "transitive verb"]) == "ichidan"
    # 行く's special class follows the plain く-row; ある's special class makes no rows
    assert family(["Godan verb - Iku/Yuku special class"]) == "godan"
    assert family(["Godan verb - Aru special class"]) is None
    assert family(["Godan verb with 'u' ending (special class)"]) is None
    assert family(["noun", "transitive verb"]) is None  # not an inflecting POS


def test_godan_table_hashiru() -> None:
    rows = row_map(GODAN_RU, "走る", "はしる")
    assert len(rows) == 15
    assert rows["Past"]["surface"] == "走った" and rows["Past"]["kana"] == "はしった"
    assert rows["Negative"]["surface"] == "走らない"
    assert rows["Polite present"]["surface"] == "走ります"
    assert rows["Te-form"]["surface"] == "走って"
    assert rows["Potential"]["surface"] == "走れる"
    assert rows["Passive"]["surface"] == "走られる"
    assert rows["Causative"]["surface"] == "走らせる"
    assert rows["Volitional"]["surface"] == "走ろう"
    assert rows["Imperative"]["surface"] == "走れ"
    assert rows["Conditional"]["surface"] == "走れば"
    assert rows["Polite past negative"]["surface"] == "走りませんでした"


def test_godan_ending_rows() -> None:
    rows = row_map(["Godan verb with 'gu' ending"], "急ぐ", "いそぐ")
    assert rows["Past"]["surface"] == "急いだ"          # ぐ→いだ
    assert rows["Negative"]["surface"] == "急がない"
    rows = row_map(["Godan verb with 'nu' ending"], "死ぬ", "しぬ")
    assert rows["Past"]["surface"] == "死んだ"          # ぬ→んだ


def test_ichidan_and_merged_potential() -> None:
    rows = row_map(V1_POSES, "見る", "みる")
    assert rows["Dictionary"]["surface"] == "見る"
    assert rows["Potential / Passive"]["surface"] == "見られる"
    assert rows["Past negative"]["surface"] == "見なかった"
    assert rows["Imperative"]["surface"] == "見ろ"
    assert "Potential" not in rows and "Passive" not in rows  # merged


def test_kuru_double_stem() -> None:
    rows = row_map(KURU, "来る", "くる")
    assert rows["Polite present"]["surface"] == "来ます" and rows["Polite present"]["kana"] == "きます"
    assert rows["Negative"]["surface"] == "来ない" and rows["Negative"]["kana"] == "こない"
    assert rows["Past"]["surface"] == "来た" and rows["Past"]["kana"] == "きた"
    assert rows["Imperative"]["surface"] == "来い" and rows["Imperative"]["kana"] == "こい"
    assert rows["Te-form"]["kana"] == "きて"


def test_suru_noun_icons() -> None:
    rows = row_map(VS, "勉強", "べんきょう")
    assert rows["Dictionary"]["surface"] == "勉強する"
    assert rows["Potential"]["surface"] == "勉強できる"
    assert rows["Past negative"]["surface"] == "勉強しなかった"
    assert rows["Imperative"]["surface"] == "勉強しろ"
    # the bare auxiliary verb する works without a noun
    rows = row_map(VS, None, "する")
    assert rows["Dictionary"]["surface"] == "する"
    assert rows["Te-form"]["surface"] == "して"


def test_adjective_rules() -> None:
    rows = row_map(ADJ_I, "楽しい", "たのしい")
    assert rows["Negative"]["surface"] == "楽しくない"
    assert rows["Past"]["surface"] == "楽しかった"
    assert rows["Past negative"]["surface"] == "楽しくなかった"
    assert rows["Te-form"]["surface"] == "楽しくて"
    assert rows["Adverbial"]["surface"] == "楽しく"
    assert rows["Conditional"]["surface"] == "楽しければ"
    assert rows["Polite present"]["surface"] == "楽しいです"


def test_ii_irregular() -> None:
    rows = row_map(ADJ_I, "いい", "いい")
    assert rows["Negative"]["surface"] == "よくない"
    assert rows["Past"]["surface"] == "よかった"
    assert rows["Te-form"]["surface"] == "よくて"
    rows = row_map(ADJ_I, "かっこいい", "かっこいい")
    assert rows["Past"]["surface"] == "かっこよかった"


def test_iku_follows_plain_godan() -> None:
    rows = row_map(["Godan verb - Iku/Yuku special class"], "行く", "いく")
    assert rows["Past"]["surface"] == "行った"
    assert rows["Te-form"]["surface"] == "行って"
    assert rows["Volitional"]["surface"] == "行こう"


def test_excluded_families_and_missing_forms() -> None:
    assert conjugate(["Godan verb - Aru special class"], "ある", "ある") == []
    assert conjugate(["noun"], "アパート", "アパート") == []
    assert conjugate(ADJ_I, None, None) == []


def test_rows_never_lie_about_kana() -> None:
    """The kana column is the reading-level inflection of the same row — all
    rows of 読む start with its stem よ, and the label order is stable."""
    tables = conjugate(["Godan verb with 'mu' ending"], "読む", "よむ")
    assert tables[0]["form"] == "Dictionary"
    assert all(r["kana"].startswith("よ") for r in tables)


def test_gloss_head_words() -> None:
    from scripts.build_chunks import _gloss_head_words

    heads = _gloss_head_words(["apartment building", "apartment block", "to eat", "car"])
    assert heads == {"apartment"}  # phrase head only; verb glosses exempt
    assert _gloss_head_words(["4-engine扎实"]) == set()  # non-alphabetic head
    assert _gloss_head_words(["condominium"]) == set()   # single word, no head
    assert _gloss_head_words(["to become clear"]) == set()
