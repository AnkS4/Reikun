/**
 * Static inventory of the modern Japanese syllabary for the /kana browse page.
 *
 * Two scripts (hiragana / katakana), three coverage bands ordered by gojūon
 * sequence: basic, dakuten, and handakuten. The order follows gojūon reading
 * order — the vowel row first, then each consonant row through わ/ん, with
 * empty gojūon slots kept in place so the chart keeps its shape (they render
 * as invisible placeholders to hold the 5-column grid).
 *
 * The data lives in `kana.json` at the repo root — the single source shared
 * with the Lite UI, exactly like the `i18n/*.json` tables. Edit kana.json;
 * both surfaces follow. This module re-exports it typed for TS consumers.
 */
import KANA_JSON from '../../../kana.json';

export type KanaRow = Array<{ kana: string; romaji: string } | null>;

export type KanaChart = {
	basic: KanaRow[];
	dakuten: KanaRow[];
	handakuten: KanaRow[];
};

const DATA = KANA_JSON as unknown as {
	hiragana: KanaChart;
	katakana: KanaChart;
	romajiToDevanagari: Record<string, string>;
};

export const HIRAGANA: KanaChart = DATA.hiragana;

export const KATAKANA: KanaChart = DATA.katakana;

/**
 * Devanagari rendering of the romaji column labels — the Hindi/Marathi
 * equivalent of the Latin transliteration (same phonetic content, native
 * script). Only the vowels shift length (आ = long a like Japanese /a/);
 * everything else maps one-to-one. Shared as kana.json's `romajiToDevanagari`.
 */
export const ROMAJI_TO_DEVANAGARI: Record<string, string> = DATA.romajiToDevanagari;

/** Localized meta label for one kana cell. */
export function kanaMetaLabel(romaji: string, locale: 'en' | 'ja' | 'es' | 'hi' | 'mr'): string {
	if (locale === 'hi' || locale === 'mr') return ROMAJI_TO_DEVANAGARI[romaji] ?? romaji;
	return romaji;
}
