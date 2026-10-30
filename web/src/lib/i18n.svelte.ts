/**
 * Tiny interface-chrome i18n: English and Japanese.
 *
 * The app is a mixed-language product by design — UI chrome is localized,
 * while JMdict glosses, example sentences and LLM explanations stay English
 * data/content. Only static chrome labels live here.
 *
 * Initial locale is English so prerendered HTML and the first client render
 * agree; `init()` applies the persisted choice on mount (a preference flash,
 * never a hydration mismatch).
 */
import { browser } from '$app/env';
import { safeStorage } from './storage.ts';

export const LOCALES = ['en', 'ja'] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_NAMES: Record<Locale, string> = {
	en: 'English',
	ja: '日本語'
};
/** BCP 47 tags used for locale-aware number formatting. */
export const LOCALE_TAGS: Record<Locale, string> = {
	en: 'en',
	ja: 'ja-JP'
};

const KEY = 'reikun-locale';

const en = {
	skipToContent: 'Skip to main content',
	language: 'Language',
	languageTitle: 'Interface language',

	backToSearch: 'Back to search',
	statusTitle: 'Dictionary status',
	statusConnecting: 'Connecting…',
	statusWaking: 'Waking up the dictionary',
	statusConnected: 'Connected',
	statusReadyWords: '{count} words and phrases ready to search',
	statusOffline: 'Offline',
	statusReachError: "Couldn't reach the dictionary — {msg}",
	statusAriaConnecting: 'Connecting to the dictionary…',
	statusAriaReady: 'Dictionary ready — {count} entries',
	statusAriaOffline: 'Dictionary offline — {msg}',
	apiUnreachable: 'API unreachable',
	appearanceTitle: 'Appearance — theme',
	appearance: 'Appearance',
	theme: 'Theme',
	themeSystem: 'System',
	themeLight: 'Light',
	themeDark: 'Dark',
	themeOled: 'OLED',

	tagline:
		'Search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji, and get grammar explanations.',
	hint: 'Type or tap an example below',
	searchPlaceholder: 'Search English or Japanese…',
	search: 'Search',
	randomKanji: 'Random {level} kanji',
	furiganaShown: 'Furigana shown — click to hide readings',
	furiganaHidden: 'Furigana hidden — click to show readings',
	furiganaToggle: 'Toggle furigana readings',
	jlptTitle: 'JLPT level for grammar explanations',
	jlptLevel: 'JLPT Level',
	searching: 'Searching…',
	entryOne: '1 entry',
	entryMany: '{count} entries',
	resultsForOne: '{query} — 1 entry',
	resultsForMany: '{count} entries for {query}',
	searchFailed: 'Search failed',
	randomFailed: 'Could not get a random kanji.',
	statsInfo: 'Query route, timing and cache details',
	technicalInfo: 'Technical info',
	route: 'route',
	total: 'total',
	cache: 'cache',
	cacheHit: 'hit',
	stages: 'stages',
	phaseRewrite: 'rewrite {ms} ms',
	phaseEmbed: 'embed {ms} ms',
	phaseRetrieve: 'retrieve {ms} ms',
	phaseParse: 'parse {ms} ms',
	searchedForBefore: 'Searched for ',
	searchedForAfter: '',
	tooLongJa:
		'“{shown}” is too long — Japanese input is parsed up to {max} characters; enter a word or a shorter sentence.',
	tooLong:
		'“{shown}” is too long for a dictionary lookup — enter a single word or a short phrase ({max} characters max).',
	notAWord:
		'“{char}” isn’t a standalone dictionary word — see the common words above for it in use.',
	nothingFound: 'Nothing found. Try a different English or Japanese word.',
	showMoreTitle: 'Refetches the search with up to {max} results',
	showMore: 'Show {count} more',
	exampleSearches: 'Example searches',
	recent: 'Recent',
	clear: 'Clear',
	recentSearches: 'Recent searches',
	scrollTop: 'Scroll to top',

	common: 'common',
	copyAsTitle: 'Copy as “word【reading】— meaning”',
	copyWordAria: 'Copy word and meaning',
	copied: 'Copied',
	inflectionForm: '{form} form of this word',
	conjugations: 'Conjugations',
	conjugationsTitle: 'View all conjugations',
	relatedWords: 'Related words',
	searchWord: 'Search {word}',
	noExamples: 'No example sentences.',

	explain: 'Explain',
	explainAgain: 'Explain again',
	explainTitle: 'JLPT-calibrated grammar explanation for this sentence',
	aiGenerated: 'AI-generated for {level}',
	explanationUnavailable: 'Explanation unavailable.',
	explanationError: '**Explanation unavailable:** {error}',

	rateSearch: 'Rate this search',
	rateExplanation: 'Rate this explanation',
	helpful: 'Helpful',
	notHelpful: 'Not helpful',

	wakeTitle: 'Waking up the dictionary…',
	wakeSub: 'The server sleeps when idle — the first request can take up to 30 seconds.',
	wakeDownTitle: "Can't reach the dictionary server.",
	wakeDownSub: 'Check your connection, or give it a moment and retry.',
	retry: 'Retry',

	shareTitle: 'Share this search',
	share: 'Share',
	linkCopied: 'Link copied',
	linkCopiedSr: 'Link copied to clipboard',

	breakdown: 'Sentence Breakdown',
	breakdownHint: 'Hover for definitions · Click to view entry',
	jumpTo: 'Jump to {word}',
	approximate: 'Approximate',
	approximateTitle: 'Fallback segmenter used',

	meanings: 'Meanings',
	commonWords: 'Common words',
	noKanjiEntry: 'No KANJIDIC2 entry for “{char}”.',
	kanjiLoadFailed: 'Failed to load kanji details',
	onTip:
		"On'yomi — the Sino-Japanese reading, borrowed with the character from Chinese. Used mostly in multi-kanji compounds (電話, 学校).",
	kunTip:
		"Kun'yomi — the native Japanese reading attached to the character's meaning. Used for standalone words and with okurigana (食べる, 山).",

	tipMeanings: 'Meanings',
	tipOn: 'On',
	tipKun: 'Kun',
	tipSearch: 'Search {char} →',
	tipAria: 'Kanji {char} details',

	conjPageTitle: '{word} conjugations',
	backTo: 'Back to {word}',
	goBack: 'Go back',
	reikunHome: 'Reikun home',
	noWord: 'No word specified — pick a conjugation from any search result card.',
	conjugationsLabel: 'conjugations',
	conjSubtitle:
		"All inflected forms of {word}. Click the back arrow or use your browser's back button to return.",
	form: 'Form',
	written: 'Written',
	kana: 'Kana',
	noConjData: 'No conjugation data found for “{word}”.',
	conjLoadFailed: 'Failed to load conjugation data',
	conjugationFallback: 'Conjugation',

	strokes: 'strokes',
	grade: 'grade',
	jlpt: 'JLPT level',
	kanjiSuffix: 'kanji',
	unknownGroup:
		"Unknown group — pick one from any kanji card's badges (strokes, grade or JLPT).",
	groupSubtitle:
		'Every kanji with the same {group}, frequency-ranked most-common first. Click one to open its full card with readings, stroke order and words.',
	openKanji: 'Open {char}',
	groupPages: 'Group pages',
	previous: '← Previous',
	next: 'Next →',
	pageOf: 'Page {page} of {pages}',
	backPrevious: 'Back to previous search',
	strokesCount: '{n} strokes',
	freq: 'Freq #{n}',
	groupLoadFailed: 'Failed to load the kanji group',

	aboutTitle: 'About Reikun',
	aboutMeta:
		'About Reikun (例訓) — Semantic Japanese Dictionary & Reading Assistant: bilingual search, sentence breakdowns with furigana, kanji stroke order, and JLPT-calibrated grammar explanations.',
	aboutLede:
		'Reikun (例訓) is a free, open-source Japanese reading assistant — a semantic dictionary that works in both English and Japanese.',
	whatItDoes: 'What it does',
	searchText:
		'look up words in English or Japanese; natural-language questions ("how do you say X") are rewritten into dictionary terms automatically.',
	breakdownBold: 'Sentence breakdown',
	breakdownText:
		'paste a Japanese sentence and it is split into word units with furigana, per-word glosses, and hover detail.',
	kanjiBold: 'Kanji',
	kanjiText:
		'readings, meanings, common compounds, JLPT level, and animated stroke-order diagrams.',
	grammarBold: 'Grammar explanations',
	grammarText:
		'concise explanations calibrated to a JLPT level (N5–N1), generated on demand by a LLM provider.',
	howItWorks: 'How it works',
	howText:
		'Search runs hybrid retrieval — dense vector embeddings plus BM25 — fused in Qdrant, with query routing that picks the right plan for English words, English sentences, and Japanese input. Sentence parsing uses the Sudachi morphological analyzer; embeddings are quantized ONNX models running on CPU. The frontend is a static SvelteKit site; the API is a FastAPI service.',
	dataSources: 'Data and sources',
	dataBefore: 'Dictionary data comes from ',
	dataAnd: ' and ',
	dataAfter: ' (EDRDG, CC BY-SA 4.0). Example sentences are from ',
	dataAfter2: ' (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams derive from ',
	dataAfter3: ' (Ulrich Apel, CC BY-SA 3.0).',
	privacy: 'Privacy',
	privacyText:
		'No cookies and no cross-site tracking. Search query text is logged to improve embeddings and ranking; feedback query text and explanation sentences are stored only as SHA-256 hashes. Recent searches are stored locally in your browser.',
	llmProviderText:
		'Grammar explanations and English descriptive query rewrites are generated on demand by a LLM provider. When you request an explanation, the Japanese sentence, its English translation, and the selected JLPT level are sent to the provider. Long English descriptive queries may also be sent for rewriting.',
	source: 'Source',
	sourceBefore: 'Reikun is built by Aniket Satbhai. The code is ',
	sourceLink: 'on GitHub',
	sourceAfter: ' under the Apache-2.0 license.',


	footerAbout: 'About',
	footerDataBefore: 'Dictionary data powered by ',
	footerDataAnd: ' and ',
	footerDataAfter: ' (EDRDG, CC BY-SA 4.0). Sentences from ',
	footerDataAfter2: ' (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams from ',
	footerDataAfter3: ' (Ulrich Apel, CC BY-SA 3.0).',

	errorUnreachable:
		"Can't reach the dictionary server. It may still be waking up — try again in a few seconds.",
	errorTimeout:
		'The server took too long to respond. It may be waking up — please try again.',
	errorStreamEnded: 'The explanation stream ended unexpectedly. Please try again.',
	errorGateway:
		'The dictionary server is starting up or temporarily unavailable. Please try again shortly.',
	errorRequestFailed: 'Request failed ({status})',
	replayStroke: 'Replay the stroke-order animation',
	strokeDiagram: 'Stroke order diagram'
} as const;

export type MessageKey = keyof typeof en;

const ja: Record<MessageKey, string> = {
	skipToContent: '本文へスキップ',
	language: '言語',
	languageTitle: '表示言語',

	backToSearch: '検索に戻る',
	statusTitle: '辞書の状態',
	statusConnecting: '接続中…',
	statusWaking: '辞書を起動しています',
	statusConnected: '接続済み',
	statusReadyWords: '{count} 語を検索できます',
	statusOffline: 'オフライン',
	statusReachError: '辞書に接続できません — {msg}',
	statusAriaConnecting: '辞書に接続中…',
	statusAriaReady: '辞書の準備完了 — {count} 項目',
	statusAriaOffline: '辞書はオフライン — {msg}',
	apiUnreachable: 'APIに接続できません',
	appearanceTitle: '外観 — テーマ',
	appearance: '外観',
	theme: 'テーマ',
	themeSystem: 'システム',
	themeLight: 'ライト',
	themeDark: 'ダーク',
	themeOled: 'OLED',

	tagline:
		'英語または日本語で検索し、文をふりがなと意味付きで語ごとに分解。漢字を調べ、JLPTレベルに合わせた文法解説も読めます。',
	hint: '下の例を入力またはタップ',
	searchPlaceholder: '英語または日本語で検索…',
	search: '検索',
	randomKanji: '{level} の漢字をランダムに表示',
	furiganaShown: 'ふりがな表示中 — クリックで非表示',
	furiganaHidden: 'ふりがな非表示 — クリックで表示',
	furiganaToggle: 'ふりがなの表示を切り替え',
	jlptTitle: '文法解説のJLPTレベル',
	jlptLevel: 'JLPTレベル',
	searching: '検索中…',
	entryOne: '1 件',
	entryMany: '{count} 件',
	resultsForOne: '「{query}」の検索結果 1 件',
	resultsForMany: '「{query}」の検索結果 {count} 件',
	searchFailed: '検索に失敗しました',
	randomFailed: 'ランダムな漢字を取得できませんでした。',
	statsInfo: '検索ルート・時間・キャッシュの詳細',
	technicalInfo: '技術情報',
	route: 'ルート',
	total: '合計',
	cache: 'キャッシュ',
	cacheHit: 'ヒット',
	stages: '内訳',
	phaseRewrite: '書き換え {ms} ms',
	phaseEmbed: '埋め込み {ms} ms',
	phaseRetrieve: '検索 {ms} ms',
	phaseParse: '解析 {ms} ms',
	searchedForBefore: '「',
	searchedForAfter: '」で検索',
	tooLongJa:
		'「{shown}」は長すぎます — 日本語入力は{max}文字まで解析できます。単語かより短い文を入力してください。',
	tooLong:
		'「{shown}」は辞書検索には長すぎます。単語か短いフレーズ（{max}文字まで）を入力してください。',
	notAWord:
		'「{char}」は単独の辞書項目ではありません。上の「よく使う語」をご覧ください。',
	nothingFound: '見つかりませんでした。別の英語または日本語の単語をお試しください。',
	showMoreTitle: '最大{max}件で再検索します',
	showMore: 'さらに{count}件表示',
	exampleSearches: '検索例',
	recent: '最近の検索',
	clear: '消去',
	recentSearches: '最近の検索一覧',
	scrollTop: 'トップへ戻る',

	common: '一般',
	copyAsTitle: '「見出し【読み】— 意味」の形式でコピー',
	copyWordAria: '単語と意味をコピー',
	copied: 'コピーしました',
	inflectionForm: 'この語の {form} 形',
	conjugations: '活用',
	conjugationsTitle: 'すべての活用形を見る',
	relatedWords: '関連語',
	searchWord: '「{word}」を検索',
	noExamples: '例文はありません。',

	explain: '解説',
	explainAgain: 'もう一度解説',
	explainTitle: 'この文のJLPT別文法解説',
	aiGenerated: '{level}向けにAIが生成',
	explanationUnavailable: '解説を取得できませんでした。',
	explanationError: '**解説を取得できませんでした:** {error}',

	rateSearch: 'この検索を評価',
	rateExplanation: 'この解説を評価',
	helpful: '役に立った',
	notHelpful: '役に立たなかった',

	wakeTitle: '辞書を起動しています…',
	wakeSub: 'サーバーは待機時にスリープします。最初のリクエストは最大30秒かかることがあります。',
	wakeDownTitle: '辞書サーバーに接続できません。',
	wakeDownSub: '接続を確認するか、少し待って再試行してください。',
	retry: '再試行',

	shareTitle: 'この検索を共有',
	share: '共有',
	linkCopied: 'リンクをコピーしました',
	linkCopiedSr: 'リンクをクリップボードにコピーしました',

	breakdown: '文の分解',
	breakdownHint: 'ホバーで意味・クリックで項目へ',
	jumpTo: '「{word}」へ移動',
	approximate: 'おおよそ',
	approximateTitle: '代替の分割方法を使用',

	meanings: '意味',
	commonWords: 'よく使う語',
	noKanjiEntry: '「{char}」のKANJIDIC2項目はありません。',
	kanjiLoadFailed: '漢字の詳細を読み込めませんでした',
	onTip: '音読み — 中国語から取り入れた漢字音。主に複数漢字の熟語で使われます（電話、学校）。',
	kunTip: '訓読み — 漢字の意味に対応する日本語の読み。単独の語や送りがな付きで使われます（食べる、山）。',

	tipMeanings: '意味',
	tipOn: '音',
	tipKun: '訓',
	tipSearch: '「{char}」を検索 →',
	tipAria: '漢字「{char}」の詳細',

	conjPageTitle: '「{word}」の活用',
	backTo: '「{word}」に戻る',
	goBack: '戻る',
	reikunHome: 'Reikun ホーム',
	noWord: '単語が指定されていません。検索結果カードから活用形を選んでください。',
	conjugationsLabel: '活用',
	conjSubtitle:
		'「{word}」のすべての活用形です。戻る矢印かブラウザの戻るボタンで戻れます。',
	form: '形',
	written: '表記',
	kana: 'かな',
	noConjData: '「{word}」の活用データが見つかりません。',
	conjLoadFailed: '活用データを読み込めませんでした',
	conjugationFallback: '活用',

	strokes: '画数',
	grade: '学年',
	jlpt: 'JLPTレベル',
	kanjiSuffix: '漢字',
	unknownGroup:
		'不明なグループです。漢字カードのバッジ（画数・学年・JLPT）から選んでください。',
	groupSubtitle:
		'同じ{group}の漢字を頻度順に並べています。クリックすると読み・筆順・語句を含むカードが開きます。',
	openKanji: '「{char}」を開く',
	groupPages: 'グループのページ',
	previous: '← 前へ',
	next: '次へ →',
	pageOf: '{page} / {pages} ページ',
	backPrevious: '前の検索に戻る',
	strokesCount: '{n}画',
	freq: '頻度 #{n}',
	groupLoadFailed: '漢字グループを読み込めませんでした',

	aboutTitle: 'Reikun について',
	aboutMeta:
		'Reikun（例訓）について — 意味検索型 日本語辞書＆読解アシスタント。英語・日本語検索、ふりがな付きの文分解、漢字の筆順、JLPT別の文法解説。',
	aboutLede:
		'Reikun（例訓）は、無料のオープンソース日本語読解アシスタントです。英語と日本語の両方で使える意味検索型の辞書です。',
	whatItDoes: 'できること',
	searchText:
		'英語または日本語で単語を調べられます。「〜は日本語で何と言いますか」のような自然な質問は、自動的に辞書の見出し語に書き換えられます。',
	breakdownBold: '文の分解',
	breakdownText:
		'日本語の文を貼り付けると、語ごとにふりがな・意味・ホバー詳細付きで分解します。',
	kanjiBold: '漢字',
	kanjiText:
		'読み、意味、よく使う熟語、JLPTレベル、筆順アニメーションを表示します。',
	grammarBold: '文法解説',
	grammarText:
		'JLPTレベル（N5〜N1）に合わせた簡潔な解説を、LLMプロバイダーがオンデマンドで生成します。',
	howItWorks: '仕組み',
	howText:
		'検索はハイブリッド検索（密ベクトル埋め込み＋BM25）をQdrantで統合し、英語の単語・英語の文・日本語入力に応じてルートを切り替えます。文の解析にはSudachi形態素解析器を使い、埋め込みはCPU上の量子化ONNXモデルで実行します。フロントエンドは静的SvelteKitサイト、APIはFastAPIサービスです。',
	dataSources: 'データと出典',
	dataBefore: '辞書データは ',
	dataAnd: ' と ',
	dataAfter: '（EDRDG、CC BY-SA 4.0）によるものです。例文は ',
	dataAfter2: '（Tatoeba、CC-BY 2.0 FR）、漢字の筆順図は ',
	dataAfter3: '（Ulrich Apel、CC BY-SA 3.0）によるものです。',
	privacy: 'プライバシー',
	privacyText:
		'Cookie を使用せず、クロスサイトトラッキングも行いません。検索クエリの本文は、埋め込みとランキングの改善のために記録されます。フィードバックのクエリ本文と解説の文は SHA-256 ハッシュのみで保存されます。最近の検索はブラウザ内に保存されます。',
	llmProviderText:
		'文法解説と英語の説明的クエリの書き換えは、LLMプロバイダーがオンデマンドで生成します。解説をリクエストすると、日本語の文・その英訳・選択したJLPTレベルがプロバイダーに送信されます。長い英語の説明的クエリも書き換えのために送信される場合があります。',
	source: 'ソース',
	sourceBefore: 'Reikun は Aniket Satbhai が開発しています。コードは ',
	sourceLink: 'GitHub',
	sourceAfter: ' で Apache-2.0 ライセンスの下で公開されています。',


	footerAbout: '概要',
	footerDataBefore: '辞書データは ',
	footerDataAnd: ' と ',
	footerDataAfter: '（EDRDG、CC BY-SA 4.0）によるものです。例文は ',
	footerDataAfter2: '（Tatoeba、CC-BY 2.0 FR）、漢字の筆順図は ',
	footerDataAfter3: '（Ulrich Apel、CC BY-SA 3.0）によるものです。',

	errorUnreachable:
		'辞書サーバーに接続できません。起動中の可能性があります — 数秒後にもう一度お試しください。',
	errorTimeout:
		'サーバーの応答が遅すぎます。起動中の可能性があります — もう一度お試しください。',
	errorStreamEnded: '解説のストリームが途中で終了しました。もう一度お試しください。',
	errorGateway:
		'辞書サーバーは起動中か、一時的に利用できません。しばらくしてからもう一度お試しください。',
	errorRequestFailed: 'リクエストに失敗しました（{status}）',
	replayStroke: '筆順アニメーションを再生',
	strokeDiagram: '筆順図'
};

const DICTS: Record<Locale, Record<MessageKey, string>> = { en, ja };

let locale = $state<Locale>('en');
let initialized = false;

function apply(l: Locale): void {
	if (browser) document.documentElement.lang = l;
}

/** Translate a chrome string; interpolation is `{name}`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
	let out = DICTS[locale][key] ?? en[key];
	if (vars) {
		for (const [name, value] of Object.entries(vars)) {
			// A replacer function keeps `$&`/`$'` in user text literal — a
			// string replacement would expand them as replacement patterns.
			out = out.replaceAll(`{${name}}`, () => String(value));
		}
	}
	return out;
}

export const i18n = {
	get locale(): Locale {
		return locale;
	},
	set(next: Locale): void {
		locale = next;
		safeStorage.set(KEY, next);
		apply(next);
	},
	/** Apply the persisted locale after hydration (SSR starts at English). */
	init(): void {
		if (initialized || !browser) return;
		initialized = true;
		const stored = safeStorage.get(KEY);
		const next: Locale = LOCALES.includes(stored as Locale) ? (stored as Locale) : 'en';
		locale = next;
		apply(next);
	}
};
