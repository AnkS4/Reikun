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
    # 問う/乞う u-ending rides godan with special った/って cells
    assert family(["Godan verb with 'u' ending (special class)"]) == "godan"
    # ある/である family: godan-tagged but irregular — its own safe rows
    assert family(["Godan verb with 'ru' ending (irregular verb)"]) == "aru"
    # くれる behaves like plain ichidan; 〜ずる rides its 〜じる alternate
    assert family(["Ichidan verb - kureru special class"]) == "ichidan"
    assert family(["Ichidan verb - zuru verb (alternative form of -jiru verbs)"]) == "zuru"
    assert family(["suru verb - special class"]) == "suru"
    assert family(["suru verb - included"]) == "suru"
    assert family(["adjective (keiyoushi) - yoi/ii class"]) == "adj-i"
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
    assert rows["Past"]["surface"] == "急いだ"  # ぐ→いだ
    assert rows["Negative"]["surface"] == "急がない"
    rows = row_map(["Godan verb with 'nu' ending"], "死ぬ", "しぬ")
    assert rows["Past"]["surface"] == "死んだ"  # ぬ→んだ


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
    # JMdict tags the いい-family "yoi/ii class" — same irregular paradigm
    rows = row_map(["adjective (keiyoushi) - yoi/ii class"], "いい", "いい")
    assert rows["Negative"]["surface"] == "よくない"
    assert rows["Past"]["surface"] == "よかった"
    assert rows["Polite present"]["surface"] == "いいです"


def test_iku_follows_plain_godan() -> None:
    rows = row_map(["Godan verb - Iku/Yuku special class"], "行く", "いく")
    assert rows["Past"]["surface"] == "行った"
    assert rows["Te-form"]["surface"] == "行って"
    assert rows["Volitional"]["surface"] == "行こう"


def test_tou_keeps_the_u_tail() -> None:
    """問う-class u-ending: 問うた/問うて, unlike 会った/会って — every other
    cell rides the plain う-row (問います/問わない/問おう)."""
    rows = row_map(["Godan verb with 'u' ending (special class)"], "問う", "とう")
    assert rows["Past"]["surface"] == "問うた" and rows["Past"]["kana"] == "とうた"
    assert rows["Te-form"]["surface"] == "問うて"
    assert rows["Polite present"]["surface"] == "問います"
    assert rows["Negative"]["surface"] == "問わない"
    assert (rows["Past"]["surface"], rows["Past"]["kana"]) == ("問うた", "とうた")


def test_oku_godan_contrast() -> None:
    rows = row_map(["Godan verb with 'u' ending"], "会う", "あう")
    assert rows["Past"]["surface"] == "会った"  # the plain u-shift った


def test_kuru_stem_conditional() -> None:
    """来れば is read くれば — the provisional rides the く-stem, never きれば."""
    assert row_map(KURU, "来る", "くる")["Conditional"]["surface"] == "来れば"
    assert row_map(KURU, "来る", "くる")["Conditional"]["kana"] == "くれば"


def test_kuru_compound_kanji() -> None:
    """連れて来る keeps the 来 glyph everywhere; the kana spelling splits
    き/こ stems like plain 来る."""
    rows = row_map(["Kuru verb - special class"], "連れて来る", "つれてくる")
    assert rows["Polite present"]["surface"] == "連れて来ます"
    assert rows["Polite present"]["kana"] == "つれてきます"
    assert rows["Negative"]["surface"] == "連れて来ない"
    assert rows["Negative"]["kana"] == "つれてこない"
    assert rows["Imperative"]["surface"] == "連れて来い"
    assert (rows["Conditional"]["surface"], rows["Conditional"]["kana"]) == ("連れて来れば", "つれてくれば")
    rows = row_map(["expressions (phrases, clauses, etc.)", "Kuru verb - special class"], None, "連れてくる")
    assert rows["Past"]["surface"] == "連れてきた"
    assert rows["Volitional"]["surface"] == "連れてこよう"


def test_zuru_rides_jiru_alternate() -> None:
    """信ずる conjugates like 信じる; only the Dictionary row keeps the ずる."""
    rows = row_map(["Ichidan verb - zuru verb (alternative form of -jiru verbs)"], "信ずる", "しんずる")
    assert rows["Dictionary"]["surface"] == "信ずる"
    assert rows["Polite present"]["surface"] == "信じます" and rows["Polite present"]["kana"] == "しんじます"
    assert rows["Negative"]["surface"] == "信じない"
    assert rows["Past"]["surface"] == "信じた"
    assert rows["Dictionary"]["kana"] == "しんずる"
    # kana-only entry (no keb) — the reading spelling becomes the surface
    rows = row_map(["Ichidan verb - zuru verb (alternative form of -jiru verbs)"], None, "しんずる")
    assert rows["Dictionary"]["surface"] == "しんずる"
    assert rows["Te-form"]["surface"] == "しんじて"


def test_aru_verb_rows() -> None:
    """ある-family: あり-insertion ます forms, whole-tail negative replacement."""
    rows = row_map(["Godan verb with 'ru' ending (irregular verb)"], "有る", "ある")
    assert rows["Dictionary"]["surface"] == "有る"
    assert (rows["Polite present"]["surface"], rows["Polite present"]["kana"]) == ("有ります", "あります")
    assert (rows["Negative"]["surface"], rows["Negative"]["kana"]) == ("ない", "ない")
    assert rows["Past"]["surface"] == "有った" and rows["Past"]["kana"] == "あった"
    assert rows["Past negative"]["surface"] == "なかった"
    assert rows["Te-form"]["surface"] == "有って"
    assert rows["Conditional"]["surface"] == "有れば"
    assert "Potential" not in rows and "Passive" not in rows and "Causative" not in rows
    assert "Imperative" not in rows
    # compound tail: Xがある → Xがない / Xがりました
    rows = row_map(["Godan verb with 'ru' ending (irregular verb)"], "意味がある", "いみがある")
    assert rows["Negative"]["surface"] == "意味がない"
    assert rows["Past"]["surface"] == "意味があった"
    assert rows["Polite past"]["surface"] == "意味がありました"


def test_vs_s_full_paradigm() -> None:
    rows = row_map(["suru verb - special class"], "愛する", "あいする")
    assert rows["Dictionary"]["surface"] == "愛する"
    assert (rows["Past"]["surface"], rows["Past"]["kana"]) == ("愛した", "あいした")
    assert rows["Polite present"]["surface"] == "愛します"
    assert rows["Negative"]["surface"] == "愛しない"
    assert rows["Te-form"]["surface"] == "愛して"
    assert rows["Causative"]["surface"] == "愛させる"
    assert rows["Volitional"]["surface"] == "愛しよう"
    assert rows["Imperative"]["surface"] == "愛しろ"


def test_vs_i_predicate_subset() -> None:
    """気がする: no 気ができる/気がされる/気がしろ — safe rows only."""
    rows = row_map(["expressions (phrases, clauses, etc.)", "suru verb - included"], "気がする", "きがする")
    assert rows["Polite present"]["surface"] == "気がします"
    assert (rows["Past"]["surface"], rows["Past"]["kana"]) == ("気がした", "きがした")
    assert rows["Negative"]["surface"] == "気がしない"
    assert rows["Negative"]["kana"] == "きがしない"
    assert rows["Te-form"]["surface"] == "気がして"
    for gone in ("Potential", "Passive", "Causative", "Volitional", "Imperative"):
        assert gone not in rows


def test_suru_bare_is_included_subset() -> None:
    """為る/する with no noun stem rides vs-i, minus the impossible cells."""
    rows = row_map(["suru verb - included"], "為る", "する")
    assert rows["Dictionary"]["surface"] == "する"  # bare する — kana column absent
    assert rows["Past"]["surface"] == "した"
    assert rows["Polite present"]["surface"] == "します"
    for gone in ("Potential", "Passive", "Causative", "Volitional", "Imperative"):
        assert gone not in rows


def test_kureru_class_is_plain_ichidan() -> None:
    """くれる's class tag exists only because its imperative is くれ (the
    plain-ichidan くれろ never shows for this verb)."""
    rows = row_map(["Ichidan verb - kureru special class"], "くれる", "くれる")
    assert rows["Dictionary"]["surface"] == "くれる"
    assert rows["Polite present"]["surface"] == "くれます"
    assert rows["Negative"]["surface"] == "くれない"
    assert rows["Past negative"]["surface"] == "くれなかった"
    assert rows["Imperative"]["surface"] == "くれ"


def test_excluded_families_and_missing_forms() -> None:
    # 御座る is JMdict-tagged plain v5r but behaves like the -aru class
    # (ございます) — a half-wrong table is worse than none
    assert conjugate(["Godan verb with 'ru' ending"], "御座る", "ござる") == []
    # いらっしゃる/なさる/くださる/おっしゃる — "-aru special class", no rows
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
    assert _gloss_head_words(["condominium"]) == set()  # single word, no head
    assert _gloss_head_words(["to become clear"]) == set()
