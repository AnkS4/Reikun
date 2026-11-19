"""Static kana tables for /lite/kana — kept byte-identical in order and
content with the SPA's web/src/lib/kana.ts (the two frontends can't import
each other's files, so the tables exist in both). Three sections each in
gojūon reading order: Basic (46), Dakuten (20), Handakuten (5) — empty
gojūon slots are kept so the five-column grid stays visually aligned."""

ROMAJI_TO_DEVANAGARI = {
    "a": "आ", "i": "ई", "u": "ऊ", "e": "ए", "o": "ओ",
    "ka": "का", "ki": "की", "ku": "कू", "ke": "के", "ko": "को",
    "sa": "सा", "shi": "शी", "su": "सू", "se": "से", "so": "सो",
    "ta": "ता", "chi": "ची", "tsu": "त्सू", "te": "ते", "to": "तो",
    "na": "ना", "ni": "नी", "nu": "नू", "ne": "ने", "no": "नो",
    "ha": "हा", "hi": "ही", "fu": "फ़ू", "he": "हे", "ho": "हो",
    "ma": "मा", "mi": "मी", "mu": "मू", "me": "मे", "mo": "मो",
    "ya": "या", "yu": "यू", "yo": "यो",
    "ra": "रा", "ri": "री", "ru": "रू", "re": "रे", "ro": "रो",
    "wa": "वा", "wo": "ओ", "n": "न्",
    "ga": "गा", "gi": "गी", "gu": "गू", "ge": "गे", "go": "गो",
    "za": "ज़ा", "ji": "ज़ी", "zu": "ज़ू", "ze": "ज़े", "zo": "ज़ो",
    "da": "दा", "de": "दे", "do": "दो",
    "ba": "बा", "bi": "बी", "bu": "बू", "be": "बे", "bo": "बो",
    "pa": "पा", "pi": "पी", "pu": "पू", "pe": "पे", "po": "पो",
}


def kana_meta_label(romaji: str, lang: str) -> str:
    """The kana chart's meta label for one cell — Devanagari under hi/mr,
    Latin romaji otherwise (same phonetic content, the chart's own script)."""
    if lang in ("hi", "mr"):
        return ROMAJI_TO_DEVANAGARI.get(romaji, romaji)
    return romaji


HIRAGANA = {
    "basic": [
        [("あ", "a"), ("い", "i"), ("う", "u"), ("え", "e"), ("お", "o")],
        [("か", "ka"), ("き", "ki"), ("く", "ku"), ("け", "ke"), ("こ", "ko")],
        [("さ", "sa"), ("し", "shi"), ("す", "su"), ("せ", "se"), ("そ", "so")],
        [("た", "ta"), ("ち", "chi"), ("つ", "tsu"), ("て", "te"), ("と", "to")],
        [("な", "na"), ("に", "ni"), ("ぬ", "nu"), ("ね", "ne"), ("の", "no")],
        [("は", "ha"), ("ひ", "hi"), ("ふ", "fu"), ("へ", "he"), ("ほ", "ho")],
        [("ま", "ma"), ("み", "mi"), ("む", "mu"), ("め", "me"), ("も", "mo")],
        [("や", "ya"), None, ("ゆ", "yu"), None, ("よ", "yo")],
        [("ら", "ra"), ("り", "ri"), ("る", "ru"), ("れ", "re"), ("ろ", "ro")],
        [("わ", "wa"), None, None, ("を", "wo"), ("ん", "n")],
    ],
    "dakuten": [
        [("が", "ga"), ("ぎ", "gi"), ("ぐ", "gu"), ("げ", "ge"), ("ご", "go")],
        [("ざ", "za"), ("じ", "ji"), ("ず", "zu"), ("ぜ", "ze"), ("ぞ", "zo")],
        [("だ", "da"), ("ぢ", "ji"), ("づ", "zu"), ("で", "de"), ("ど", "do")],
        [("ば", "ba"), ("び", "bi"), ("ぶ", "bu"), ("べ", "be"), ("ぼ", "bo")],
    ],
    "handakuten": [
        [("ぱ", "pa"), ("ぴ", "pi"), ("ぷ", "pu"), ("ぺ", "pe"), ("ぽ", "po")],
    ],
}

KATAKANA = {
    "basic": [
        [("ア", "a"), ("イ", "i"), ("ウ", "u"), ("エ", "e"), ("オ", "o")],
        [("カ", "ka"), ("キ", "ki"), ("ク", "ku"), ("ケ", "ke"), ("コ", "ko")],
        [("サ", "sa"), ("シ", "shi"), ("ス", "su"), ("セ", "se"), ("ソ", "so")],
        [("タ", "ta"), ("チ", "chi"), ("ツ", "tsu"), ("テ", "te"), ("ト", "to")],
        [("ナ", "na"), ("ニ", "ni"), ("ヌ", "nu"), ("ネ", "ne"), ("ノ", "no")],  # noqa: RUF001 — katakana glyph, not URL separator
        [("ハ", "ha"), ("ヒ", "hi"), ("フ", "fu"), ("ヘ", "he"), ("ホ", "ho")],
        [("マ", "ma"), ("ミ", "mi"), ("ム", "mu"), ("メ", "me"), ("モ", "mo")],
        [("ヤ", "ya"), None, ("ユ", "yu"), None, ("ヨ", "yo")],
        [("ラ", "ra"), ("リ", "ri"), ("ル", "ru"), ("レ", "re"), ("ロ", "ro")],
        [("ワ", "wa"), None, None, ("ヲ", "wo"), ("ン", "n")],
    ],
    "dakuten": [
        [("ガ", "ga"), ("ギ", "gi"), ("グ", "gu"), ("ゲ", "ge"), ("ゴ", "go")],
        [("ザ", "za"), ("ジ", "ji"), ("ズ", "zu"), ("ゼ", "ze"), ("ゾ", "zo")],
        [("ダ", "da"), ("ヂ", "ji"), ("ヅ", "zu"), ("デ", "de"), ("ド", "do")],
        [("バ", "ba"), ("ビ", "bi"), ("ブ", "bu"), ("ベ", "be"), ("ボ", "bo")],
    ],
    "handakuten": [
        [("パ", "pa"), ("ピ", "pi"), ("プ", "pu"), ("ペ", "pe"), ("ポ", "po")],
    ],
}
