/** Mirrors app/kanji_lookup.py's is_kanji — the CJK ranges, nothing else. */
export const isKanji = (ch: string): boolean => {
	const cp = ch.codePointAt(0);
	if (cp === undefined || ch.length !== (cp > 0xffff ? 2 : 1)) return false;
	return (
		(cp >= 0x4e00 && cp <= 0x9fff) ||
		(cp >= 0x3400 && cp <= 0x4dbf) ||
		(cp >= 0xf900 && cp <= 0xfaff) ||
		(cp >= 0x20000 && cp <= 0x2a6df)
	);
};
