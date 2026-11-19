/**
 * Static inventory of the modern Japanese syllabary for the /kana browse page.
 *
 * Two scripts (hiragana / katakana), three coverage bands ordered by gojūon
 * sequence: basic, dakuten, and handakuten. The order follows gojūon reading
 * order — the vowel row first, then each consonant row through わ/ん, with
 * empty gojūon slots kept in place so the chart keeps its shape (they render
 * as invisible placeholders to hold the 5-column grid).
 */
/**
 * Devanagari rendering of the romaji column labels — the Hindi/Marathi
 * equivalent of the Latin transliteration (same phonetic content, native
 * script). Only the vowels shift length (आ = long a like Japanese /a/);
 * everything else maps one-to-one. No UI copy changes: the chart's meta
 * line just reads the script the reader learns in.
 */
export const ROMAJI_TO_DEVANAGARI: Record<string, string> = {
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
};

/** Localized meta label for one kana cell. */
export function kanaMetaLabel(romaji: string, locale: 'en' | 'ja' | 'es' | 'hi' | 'mr'): string {
	if (locale === 'hi' || locale === 'mr') return ROMAJI_TO_DEVANAGARI[romaji] ?? romaji;
	return romaji;
}

export type KanaRow = Array<{ kana: string; romaji: string } | null>;

export type KanaChart = {
	bss: KanaRow[];
	dakuten: KanaRow[];
	handakuten: KanaRow[];
};

export const HIRAGANA: KanaChart = {
	bss: [
		[
			{ kana: 'あ', romaji: 'a' }, { kana: 'い', romaji: 'i' }, { kana: 'う', romaji: 'u' },
			{ kana: 'え', romaji: 'e' }, { kana: 'お', romaji: 'o' }
		],
		[
			{ kana: 'か', romaji: 'ka' }, { kana: 'き', romaji: 'ki' }, { kana: 'く', romaji: 'ku' },
			{ kana: 'け', romaji: 'ke' }, { kana: 'こ', romaji: 'ko' }
		],
		[
			{ kana: 'さ', romaji: 'sa' }, { kana: 'し', romaji: 'shi' }, { kana: 'す', romaji: 'su' },
			{ kana: 'せ', romaji: 'se' }, { kana: 'そ', romaji: 'so' }
		],
		[
			{ kana: 'た', romaji: 'ta' }, { kana: 'ち', romaji: 'chi' }, { kana: 'つ', romaji: 'tsu' },
			{ kana: 'て', romaji: 'te' }, { kana: 'と', romaji: 'to' }
		],
		[
			{ kana: 'な', romaji: 'na' }, { kana: 'に', romaji: 'ni' }, { kana: 'ぬ', romaji: 'nu' },
			{ kana: 'ね', romaji: 'ne' }, { kana: 'の', romaji: 'no' }
		],
		[
			{ kana: 'は', romaji: 'ha' }, { kana: 'ひ', romaji: 'hi' }, { kana: 'ふ', romaji: 'fu' },
			{ kana: 'へ', romaji: 'he' }, { kana: 'ほ', romaji: 'ho' }
		],
		[
			{ kana: 'ま', romaji: 'ma' }, { kana: 'み', romaji: 'mi' }, { kana: 'む', romaji: 'mu' },
			{ kana: 'め', romaji: 'me' }, { kana: 'も', romaji: 'mo' }
		],
		[
			{ kana: 'や', romaji: 'ya' }, null, { kana: 'ゆ', romaji: 'yu' },
			null, { kana: 'よ', romaji: 'yo' }
		],
		[
			{ kana: 'ら', romaji: 'ra' }, { kana: 'り', romaji: 'ri' }, { kana: 'る', romaji: 'ru' },
			{ kana: 'れ', romaji: 're' }, { kana: 'ろ', romaji: 'ro' }
		],
		[
			{ kana: 'わ', romaji: 'wa' }, null, null,
			{ kana: 'を', romaji: 'wo' }, { kana: 'ん', romaji: 'n' }
		]
	],
	dakuten: [
		[
			{ kana: 'が', romaji: 'ga' }, { kana: 'ぎ', romaji: 'gi' }, { kana: 'ぐ', romaji: 'gu' },
			{ kana: 'げ', romaji: 'ge' }, { kana: 'ご', romaji: 'go' }
		],
		[
			{ kana: 'ざ', romaji: 'za' }, { kana: 'じ', romaji: 'ji' }, { kana: 'ず', romaji: 'zu' },
			{ kana: 'ぜ', romaji: 'ze' }, { kana: 'ぞ', romaji: 'zo' }
		],
		[
			{ kana: 'だ', romaji: 'da' }, { kana: 'ぢ', romaji: 'ji' }, { kana: 'づ', romaji: 'zu' },
			{ kana: 'で', romaji: 'de' }, { kana: 'ど', romaji: 'do' }
		],
		[
			{ kana: 'ば', romaji: 'ba' }, { kana: 'び', romaji: 'bi' }, { kana: 'ぶ', romaji: 'bu' },
			{ kana: 'べ', romaji: 'be' }, { kana: 'ぼ', romaji: 'bo' }
		]
	],
	handakuten: [
		[
			{ kana: 'ぱ', romaji: 'pa' }, { kana: 'ぴ', romaji: 'pi' }, { kana: 'ぷ', romaji: 'pu' },
			{ kana: 'ぺ', romaji: 'pe' }, { kana: 'ぽ', romaji: 'po' }
		]
	]
};

export const KATAKANA: KanaChart = {
	bss: [
		[
			{ kana: 'ア', romaji: 'a' }, { kana: 'イ', romaji: 'i' }, { kana: 'ウ', romaji: 'u' },
			{ kana: 'エ', romaji: 'e' }, { kana: 'オ', romaji: 'o' }
		],
		[
			{ kana: 'カ', romaji: 'ka' }, { kana: 'キ', romaji: 'ki' }, { kana: 'ク', romaji: 'ku' },
			{ kana: 'ケ', romaji: 'ke' }, { kana: 'コ', romaji: 'ko' }
		],
		[
			{ kana: 'サ', romaji: 'sa' }, { kana: 'シ', romaji: 'shi' }, { kana: 'ス', romaji: 'su' },
			{ kana: 'セ', romaji: 'se' }, { kana: 'ソ', romaji: 'so' }
		],
		[
			{ kana: 'タ', romaji: 'ta' }, { kana: 'チ', romaji: 'chi' }, { kana: 'ツ', romaji: 'tsu' },
			{ kana: 'テ', romaji: 'te' }, { kana: 'ト', romaji: 'to' }
		],
		[
			{ kana: 'ナ', romaji: 'na' }, { kana: 'ニ', romaji: 'ni' }, { kana: 'ヌ', romaji: 'nu' },
			{ kana: 'ネ', romaji: 'ne' }, { kana: 'ノ', romaji: 'no' }
		],
		[
			{ kana: 'ハ', romaji: 'ha' }, { kana: 'ヒ', romaji: 'hi' }, { kana: 'フ', romaji: 'fu' },
			{ kana: 'ヘ', romaji: 'he' }, { kana: 'ホ', romaji: 'ho' }
		],
		[
			{ kana: 'マ', romaji: 'ma' }, { kana: 'ミ', romaji: 'mi' }, { kana: 'ム', romaji: 'mu' },
			{ kana: 'メ', romaji: 'me' }, { kana: 'モ', romaji: 'mo' }
		],
		[
			{ kana: 'ヤ', romaji: 'ya' }, null, { kana: 'ユ', romaji: 'yu' },
			null, { kana: 'ヨ', romaji: 'yo' }
		],
		[
			{ kana: 'ラ', romaji: 'ra' }, { kana: 'リ', romaji: 'ri' }, { kana: 'ル', romaji: 'ru' },
			{ kana: 'レ', romaji: 're' }, { kana: 'ロ', romaji: 'ro' }
		],
		[
			{ kana: 'ワ', romaji: 'wa' }, null, null,
			{ kana: 'ヲ', romaji: 'wo' }, { kana: 'ン', romaji: 'n' }
		]
	],
	dakuten: [
		[
			{ kana: 'ガ', romaji: 'ga' }, { kana: 'ギ', romaji: 'gi' }, { kana: 'グ', romaji: 'gu' },
			{ kana: 'ゲ', romaji: 'ge' }, { kana: 'ゴ', romaji: 'go' }
		],
		[
			{ kana: 'ザ', romaji: 'za' }, { kana: 'ジ', romaji: 'ji' }, { kana: 'ズ', romaji: 'zu' },
			{ kana: 'ゼ', romaji: 'ze' }, { kana: 'ゾ', romaji: 'zo' }
		],
		[
			{ kana: 'ダ', romaji: 'da' }, { kana: 'ヂ', romaji: 'ji' }, { kana: 'ヅ', romaji: 'zu' },
			{ kana: 'デ', romaji: 'de' }, { kana: 'ド', romaji: 'do' }
		],
		[
			{ kana: 'バ', romaji: 'ba' }, { kana: 'ビ', romaji: 'bi' }, { kana: 'ブ', romaji: 'bu' },
			{ kana: 'ベ', romaji: 'be' }, { kana: 'ボ', romaji: 'bo' }
		]
	],
	handakuten: [
		[
			{ kana: 'パ', romaji: 'pa' }, { kana: 'ピ', romaji: 'pi' }, { kana: 'プ', romaji: 'pu' },
			{ kana: 'ペ', romaji: 'pe' }, { kana: 'ポ', romaji: 'po' }
		]
	]
};
