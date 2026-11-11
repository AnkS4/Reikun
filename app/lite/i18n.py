"""Chrome strings for the Lite UI (en/ja)."""

_I18N: dict[str, dict[str, str]] = {
    "en": {
        "statusTitle": "Dictionary status",
        "statusConnected": "Connected",
        "statusOffline": "Offline",
        "statusUnavailable": "Unavailable — try again shortly",
        "statusAriaReady": "Dictionary ready — {count} entries",
        "statusAriaOffline": "Dictionary offline — {msg}",
        "fullSwitch": "Switch to the full interface",
        "fullShort": "Full",
        "langSwitch": "Switch to {name}",
        "themeLight": "Light",
        "themeDark": "Dark",
        "themeToLight": "Switch to the light theme",
        "themeToDark": "Switch to the dark theme",
        "statusChecking": "Checking",
        "taglineLite": "Search in English or Japanese, break down sentences word-by-word with "
        "furigana and meanings, inspect kanji.",
        "liteNote": "Lite mode: plain pages, no scripts.",
        "liteNoteLink": "What's different →",
        "searchPlaceholder": "Search English or Japanese…",
        "search": "Search",
        "randomKanjiLabel": "Random kanji",
        "furiganaLabel": "Furigana",
        "furiganaShown": "Furigana shown — click to hide readings",
        "furiganaHidden": "Furigana hidden — click to show readings",
        "recentSearches": "Recent searches",
        "exampleSearches": "Example searches",
        "clear": "Clear",
        "searchedForBefore": "Searched for ",
        "searchedForAfter": "",
        "tooLongJa": "“{shown}” is too long — Japanese input is parsed up to {max} characters; "
        "enter a word or a shorter sentence.",
        "tooLong": "“{shown}” is too long for a dictionary lookup — enter a single word or a "
        "short phrase ({max} characters max).",
        "breakdown": "Sentence Breakdown",
        "breakdownHint": "Hover for definitions · Click to view entry",
        "approximate": "Approximate",
        "entryOne": "1 entry",
        "entryMany": "{count} entries",
        "nothingFound": "Nothing found. Try a different English or Japanese word.",
        "notAWord": "“{char}” isn’t a standalone dictionary word — see the common words above "  # noqa: RUF001
        "for it in use.",
        "searchUnavailable": "Search is temporarily unavailable. Please try again.",
        "retry": "Retry",
        "common": "common",
        "inflectionNote": '{query} — matched the <b>{form}</b> form of <span lang="ja">{head}</span>',
        "conjLink": "Conjugations ({count})",
        "kanjiLabel": "Kanji",
        "kanjiSuffix": "kanji",
        "groupSubtitle": "Every kanji with the same {group}, frequency-ranked most-common first. "
        "Click one to open its full card with readings, stroke order and words.",
        "strokesCount": "{n} strokes",
        "freq": "Freq #{n}",
        "relatedWords": "Related words",
        "backToSearch": "Back to search",
        "backTo": "Back to {word}",
        "conjugations": "Conjugations",
        "conjPageTitle": "{word} conjugations",
        "conjSub": "How the forms of {word} are written and read.",
        "conjNoWord": 'No word given — open a search result and click its "Conjugations" link.',
        "noConjData": 'No conjugation data for <span lang="ja">{word}</span> — only verbs and '
        "i-adjectives ship a table.",
        "form": "Form",
        "written": "Written",
        "kana": "Kana",
        "lookupUnavailable": "Lookup unavailable",
        "meanings": "Meanings",
        "commonWords": "Common words",
        "strokeAria": "Stroke order for {char}",
        "notKanji": "Not a kanji",
        "notKanjiMsg": "Provide exactly one kanji character.",
        "kanjiNotFound": "Kanji not found",
        "noKanjiEntry": "No KANJIDIC2 entry for “{char}”.",
        "unknownGroup": "Unknown group",
        "unknownGroupMsg": "Groups are browsable by strokes, grade or JLPT level.",
        "noGroupMsg": "No kanji found for {by}={value}.",
        "noKanjiInGroup": "No kanji in group",
        "previous": "← Previous",
        "next": "Next →",
        "pageOf": "Page {page} of {pages}",
        "backToGroup": "Back to group",
        "kanjiPageTitle": "Kanji {char}",
        "resultsTitle": "{query} — results",
        "aboutTitle": "About Reikun",
        "aboutLede": "Reikun (例訓) is a free, open-source Japanese reading assistant — a semantic "
        "dictionary that works in both English and Japanese.",
        "whatItDoes": "What it does",
        "searchText": "look up words in English or Japanese; natural-language questions "
        '("how do you say X") are rewritten into dictionary terms automatically.',
        "breakdownBold": "Sentence breakdown",
        "breakdownText": "paste a Japanese sentence and it is split into word units with "
        "furigana, per-word glosses, and hover detail.",
        "kanjiBold": "Kanji",
        "kanjiText": "readings, meanings, common compounds, JLPT level, and animated "
        "stroke-order diagrams.",
        "liteVsFull": "Lite version",
        "liteVsFullText": "Lite is a plain, JavaScript-free version of the same dictionary: no popups, animations "
        "or grammar explanations, so it also works in text browsers and on slow connections. "
        "Theme, language and recent searches carry over between the two.",
        "howItWorks": "How it works",
        "howTextLite": "Search runs hybrid retrieval — dense vector embeddings plus BM25 — "
        "fused in Qdrant, with query routing that picks the right plan for English words, "
        "English sentences, and Japanese input. Sentence parsing uses the Sudachi morphological "
        "analyzer; embeddings are quantized ONNX models running on CPU. Every Lite page is one "
        "HTML string — there is no frontend bundle.",
        "dataSources": "Data and sources",
        "dataBefore": "Dictionary data comes from ",
        "dataAnd": " and ",
        "dataAfter": " (EDRDG, CC BY-SA 4.0). Example sentences are from ",
        "dataAfter2": " (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams derive from ",
        "dataAfter3": " (Ulrich Apel, CC BY-SA 3.0).",
        "privacy": "Privacy",
        "privacyText": "No accounts and no cross-site tracking. Search queries are logged to improve the dictionary; "
        "feedback and explanation text is stored only as one-way hashes. Theme, language, furigana and recent "
        "searches stay on your device.",
        "privacyMore": "Full privacy policy →",
        "source": "Source",
        "sourceBefore": "Reikun is built by Aniket Satbhai. The code is ",
        "sourceLink": "on GitHub",
        "sourceAfter": " under the Apache-2.0 license.",
        "version": "Version",
    },
    "ja": {
        "statusTitle": "辞書の状態",
        "statusConnected": "接続済み",
        "statusOffline": "オフライン",
        "statusUnavailable": "利用できません — しばらくしてから再度お試しください",
        "statusAriaReady": "辞書の準備完了 — {count} 項目",
        "statusAriaOffline": "辞書はオフライン — {msg}",
        "fullSwitch": "フル版へ切り替え",
        "fullShort": "フル",
        "langSwitch": "{name}に切り替え",
        "themeLight": "ライト",
        "themeDark": "ダーク",
        "themeToLight": "ライトテーマへ切り替え",
        "themeToDark": "ダークテーマへ切り替え",
        "statusChecking": "確認中",
        "taglineLite": "英語または日本語で検索し、文をふりがなと意味付きで語ごとに分解。漢字を調べられます。",
        "liteNote": "Lite版：スクリプトなしのシンプルなページ",  # noqa: RUF001
        "liteNoteLink": "違いを見る →",
        "searchPlaceholder": "英語または日本語で検索…",
        "search": "検索",
        "randomKanjiLabel": "ランダム漢字",
        "furiganaLabel": "ふりがな",
        "furiganaShown": "ふりがな表示中 — クリックで非表示",
        "furiganaHidden": "ふりがな非表示 — クリックで表示",
        "recentSearches": "最近の検索一覧",
        "exampleSearches": "検索例",
        "clear": "消去",
        "searchedForBefore": "「",
        "searchedForAfter": "」で検索",
        "tooLongJa": "「{shown}」は長すぎます — 日本語入力は{max}文字まで解析できます。"
        "単語かより短い文を入力してください。",
        "tooLong": "「{shown}」は辞書検索には長すぎます。単語か短いフレーズ"
        "（{max}文字まで）を入力してください。",  # noqa: RUF001
        "breakdown": "文の分解",
        "breakdownHint": "ホバーで意味・クリックで項目へ",
        "approximate": "おおよそ",
        "entryOne": "1 件",
        "entryMany": "{count} 件",
        "nothingFound": "見つかりませんでした。別の英語または日本語の単語をお試しください。",
        "notAWord": "「{char}」は独立した辞書の見出し語ではありません — 上のよく使う語で"
        "実際の用法をご覧ください。",
        "searchUnavailable": "検索は一時的に利用できません。しばらくしてから再度お試しください。",
        "retry": "再試行",
        "common": "一般",
        "inflectionNote": "「{query}」は <span lang=\"ja\">{head}</span> の <b>{form}</b> 形に一致",
        "conjLink": "活用 ({count})",
        "kanjiLabel": "漢字",
        "kanjiSuffix": "漢字",
        "groupSubtitle": "同じ{group}の漢字を、よく使う順に並べています。"
        "クリックで読み・筆順・熟語付きのカードを開きます。",
        "strokesCount": "{n}画",
        "freq": "頻度 #{n}",
        "relatedWords": "関連語",
        "backToSearch": "検索に戻る",
        "backTo": "「{word}」に戻る",
        "conjugations": "活用",
        "conjPageTitle": "「{word}」の活用",
        "conjSub": "「{word}」の各活用形の表記と読み方。",
        "conjNoWord": "単語が指定されていません — 検索結果カードの「活用」リンクから開いてください。",
        "noConjData": "<span lang=\"ja\">{word}</span> の活用データが見つかりません。"
        "動詞とイ形容詞だけが活用表を持っています。",
        "form": "形",
        "written": "表記",
        "kana": "かな",
        "lookupUnavailable": "照会できません",
        "meanings": "意味",
        "commonWords": "よく使う語",
        "strokeAria": "「{char}」の筆順",
        "notKanji": "漢字ではありません",
        "notKanjiMsg": "漢字1文字を指定してください。",
        "kanjiNotFound": "漢字が見つかりません",
        "noKanjiEntry": "「{char}」のKANJIDIC2項目はありません。",
        "unknownGroup": "不明なグループ",
        "unknownGroupMsg": "画数・学年・JLPTレベルごとに漢字を見られます。",
        "noGroupMsg": "{by}={value} の漢字が見つかりません。",
        "noKanjiInGroup": "グループに漢字がありません",
        "previous": "← 前へ",
        "next": "次へ →",
        "pageOf": "{page} / {pages} ページ",
        "backToGroup": "グループに戻る",
        "kanjiPageTitle": "漢字 {char}",
        "resultsTitle": "「{query}」の検索結果",
        "aboutTitle": "Reikun について",
        "aboutLede": "Reikun（例訓）は、無料のオープンソース日本語読解アシスタントです。"  # noqa: RUF001
        "英語と日本語の両方で使える意味検索型の辞書です。",
        "whatItDoes": "できること",
        "searchText": "英語または日本語で単語を調べられます。「〜は日本語で何と言いますか」の"
        "ような自然な質問は、自動的に辞書の見出し語に書き換えられます。",
        "breakdownBold": "文の分解",
        "breakdownText": "日本語の文を貼り付けると、語ごとにふりがな・意味・ホバー詳細付きで"
        "分解します。",
        "kanjiBold": "漢字",
        "kanjiText": "読み、意味、よく使う熟語、JLPTレベル、筆順アニメーションを表示します。",
        "liteVsFull": "Lite版",
        "liteVsFullText": "Lite版は同じ辞書を、JavaScriptなしの簡素なページで提供します。"
        "ポップアップ・アニメーション・文法解説はなく、テキストブラウザや低速な回線でも動作します。テーマ・言語・最近の検索は両方で共有されます。",
        "howItWorks": "仕組み",
        "howTextLite": "検索はハイブリッド検索（密ベクトル埋め込み＋BM25）をQdrantで統合し、"  # noqa: RUF001
        "英語の単語・英語の文・日本語入力に応じてルートを切り替えます。文の解析にはSudachi"
        "形態素解析器を使い、埋め込みはCPU上の量子化ONNXモデルで実行します。Lite版の各ページは"
        "1つのHTML文字列で、フロントエンドのバンドルはありません。",
        "dataSources": "データと出典",
        "dataBefore": "辞書データは ",
        "dataAnd": " と ",
        "dataAfter": "（EDRDG、CC BY-SA 4.0）によるものです。例文は ",  # noqa: RUF001
        "dataAfter2": "（Tatoeba、CC-BY 2.0 FR）、漢字の筆順図は ",  # noqa: RUF001
        "dataAfter3": "（Ulrich Apel、CC BY-SA 3.0）によるものです。",  # noqa: RUF001
        "privacy": "プライバシー",
        "privacyText": "アカウントは不要で、クロスサイトトラッキングも行いません。"
        "検索クエリは辞書改善のために記録され、"
        "フィードバックと解説の文は一方向ハッシュのみで保存されます。"
        "テーマ・言語・ふりがな・最近の検索はお使いの端末内にのみ保存されます。",
        "privacyMore": "プライバシーポリシー全文 →",
        "source": "ソース",
        "sourceBefore": "Reikun は Aniket Satbhai が開発しています。コードは ",
        "sourceLink": "GitHub",
        "sourceAfter": " で Apache-2.0 ライセンスの下で公開されています。",
        "version": "バージョン",
    },
}


def _t(lang: str, key: str, **vars: object) -> str:
    """Translate a chrome string; interpolation is ``{name}``. A plain
    ``str.replace`` keeps user text literal (no replacement-pattern expansion
    like JavaScript's ``$&``)."""
    out = _I18N.get(lang, _I18N["en"]).get(key) or _I18N["en"][key]
    for name, value in vars.items():
        out = out.replace("{" + name + "}", str(value))
    return out

