/** Mirrors app/kanji_lookup.py's is_kanji/kanji_in — the CJK ranges, nothing else. */
const KANJI_RE = /[一-鿿㐀-䶿豈-﫿𠀀-𪛟]/u;

export const isKanji = (ch: string): boolean => [...ch].length === 1 && KANJI_RE.test(ch);

/** Unique kanji in `text`, in order of first appearance. */
export const kanjiIn = (text: string): string[] => [...new Set([...text].filter(isKanji))];
