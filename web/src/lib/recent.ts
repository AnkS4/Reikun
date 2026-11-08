// Last few searches. Two stores with one shared truth: the `lite_recent`
// cookie is the cross-variant channel with the server-rendered lite UI
// (app/lite.py reads and writes the same cookie; cookies are not port-scoped,
// the same trick as the lite_theme sync — whichever variant searched last
// wins). localStorage keeps this browser's copy around for when cookies are
// blocked (in-app browsers, Safari "Block all cookies"): without the shared
// channel those browsers still get per-browser history. Every cookie access
// is best-effort — a blocked/oversized cookie degrades to the local copy.
import { safeStorage } from '#lib/storage.ts';

const KEY = 'reikun:recent';
// Must match app/lite.py: cookie name, cap, per-entry length and age.
const COOKIE = 'lite_recent';
const MAX = 8;
const MAX_CHARS = 150; // matches the API's query cap — never render junk from a tampered entry
const COOKIE_BUDGET = 2400; // encoded value must stay under the ~4KB browser cap (lite enforces the same)
const MAX_AGE = 2_592_000; // 30 days

function normalize(list: unknown): string[] | null {
	if (!Array.isArray(list)) return null;
	// Deduped: a duplicate entry would be a duplicate key in the recent
	// list's each block (Svelte throws on that), and a list written by an
	// older build may still hold one.
	const seen = new Set<string>();
	return list
		.filter((x): x is string => typeof x === 'string' && x.length > 0 && x.length <= MAX_CHARS)
		.filter((x) => (seen.has(x) ? false : (seen.add(x), true)))
		.slice(0, MAX);
}

function readCookie(): string[] | null {
	let raw: string | undefined;
	try {
		raw = document.cookie.match(/(?:^|;\s*)lite_recent=([^;]*)/)?.[1];
	} catch {
		return null;
	}
	if (raw === undefined) return null; // absent → caller falls back to localStorage
	try {
		raw = decodeURIComponent(raw).replace(/^"|"$/g, ''); // servers may quote the value ("[]")
	} catch {
		return null;
	}
	if (raw === '') return []; // explicit empty: a variant just cleared the shared list
	try {
		return normalize(JSON.parse(raw));
	} catch {
		return null;
	}
}

/** Write the shared cookie within the size budget (newest first; the oldest
 * entries fall off first). Best-effort: blocked storage throws and is
 * swallowed — the localStorage copy still records the history. */
function writeCookie(list: string[]): void {
	for (let n = list.length; n >= 1; n--) {
		const encoded = encodeURIComponent(JSON.stringify(list.slice(0, n)));
		if (encoded.length > COOKIE_BUDGET && n > 1) continue;
		try {
			document.cookie = `${COOKIE}=${encoded}; Path=/; Max-Age=${MAX_AGE}; SameSite=Lax`;
		} catch {
			// cookie storage blocked — localStorage already has this entry
		}
		return;
	}
}

function readLocal(): string[] | null {
	let value: unknown;
	try {
		value = JSON.parse(safeStorage.get(KEY) ?? 'null');
	} catch {
		return null;
	}
	return normalize(value);
}

export function loadRecent(): string[] {
	const shared = readCookie();
	if (shared !== null) {
		// The cookie is authoritative — keep this browser's fallback aligned.
		try {
			safeStorage.set(KEY, JSON.stringify(shared));
		} catch {
			// blocked storage
		}
		return shared;
	}
	// No (or unreadable) shared cookie: this browser's own list — and seed the
	// shared channel from it so the other variant picks the history up.
	const local = readLocal();
	if (local !== null) writeCookie(local);
	return local ?? [];
}

export function pushRecent(q: string): string[] {
	const list = [q, ...loadRecent().filter((x) => x !== q)].slice(0, MAX);
	try {
		safeStorage.set(KEY, JSON.stringify(list));
	} catch {
		// blocked storage — cookie below still carries the shared record
	}
	writeCookie(list);
	return list;
}

export function clearRecent(): void {
	try {
		safeStorage.remove(KEY);
	} catch {
		// blocked storage
	}
	// Store the empty list in the shared cookie (don't just expire it): the
	// lite UI reads this cookie server-side, and an *absent* cookie would tell
	// both variants "unknown — fall back to local history", resurrecting the
	// cleared list. An explicit [] is the cleared tombstone every reader honours.
	try {
		document.cookie = `${COOKIE}=[]; Path=/; Max-Age=${MAX_AGE}; SameSite=Lax`;
	} catch {
		// blocked cookie storage
	}
}
