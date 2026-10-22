// Last few searches, kept only in this browser (localStorage). Goes through
// safeStorage so blocked storage (in-app browsers, Safari "Block all cookies")
// degrades to "no history" instead of throwing.
import { safeStorage } from '#lib/storage.ts';

const KEY = 'reikun:recent';
const MAX = 8;
const MAX_CHARS = 150; // matches the API's query cap — never render junk from a tampered entry

export function loadRecent(): string[] {
	try {
		const v: unknown = JSON.parse(safeStorage.get(KEY) ?? '[]');
		if (!Array.isArray(v)) return [];
		// Deduped: a duplicate entry would be a duplicate key in the recent
		// list's each block (Svelte throws on that), and a list written by an
		// older build may still hold one.
		const seen = new Set<string>();
		return v
			.filter((x): x is string => typeof x === 'string' && x.length > 0 && x.length <= MAX_CHARS)
			.filter((x) => (seen.has(x) ? false : (seen.add(x), true)))
			.slice(0, MAX);
	} catch {
		return [];
	}
}

export function pushRecent(q: string): string[] {
	const list = [q, ...loadRecent().filter((x) => x !== q)].slice(0, MAX);
	safeStorage.set(KEY, JSON.stringify(list));
	return list;
}

export function clearRecent(): void {
	safeStorage.remove(KEY);
}
