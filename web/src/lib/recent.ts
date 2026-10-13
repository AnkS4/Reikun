// Last few searches, kept only in this browser (localStorage).
const KEY = 'reikun:recent';
const MAX = 8;

export function loadRecent(): string[] {
	try {
		const v = JSON.parse(localStorage.getItem(KEY) ?? '[]');
		return Array.isArray(v) ? v.filter((x) => typeof x === 'string').slice(0, MAX) : [];
	} catch {
		return [];
	}
}

export function pushRecent(q: string): string[] {
	const list = [q, ...loadRecent().filter((x) => x !== q)].slice(0, MAX);
	try {
		localStorage.setItem(KEY, JSON.stringify(list));
	} catch {
		/* storage blocked */
	}
	return list;
}

export function clearRecent(): void {
	try {
		localStorage.removeItem(KEY);
	} catch {
		/* storage blocked */
	}
}
