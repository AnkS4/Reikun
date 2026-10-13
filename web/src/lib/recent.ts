// Last few searches, kept only in this browser (localStorage).
import { safeStorage } from './storage.ts';

const KEY = 'reikun:recent';
const MAX = 8;

export function loadRecent(): string[] {
	try {
		const v = JSON.parse(safeStorage.get(KEY) ?? '[]');
		return Array.isArray(v) ? v.filter((x) => typeof x === 'string').slice(0, MAX) : [];
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
