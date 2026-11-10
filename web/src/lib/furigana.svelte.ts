/**
 * Furigana visibility store — a persisted show/hide reading preference,
 * the reading-practice counterpart to the theme store.
 *
 * Ruby.svelte gates its <rt> output on this, so one flag covers result
 * headwords, example rows, segment chips and kanji-card word lists alike.
 * Default: on. Safe on the server (no storage read) so prerendered routes
 * paint default-on and hydration re-evaluates.
 *
 * Cross-variant sync: the lite UI (server-rendered, on the API origin's port)
 * stores its furigana preference in the `lite_furi` cookie (see app/lite.py).
 * Cookies are NOT port-scoped, so both variants see it on shared localhost
 * hosts — the full version writes it too, and reads it when nothing is stored
 * locally. A pinned "off" is shared as '0'; anything else means on.
 */
import { browser } from '$app/env';
import { safeStorage } from '#lib/storage.ts';

const KEY = 'reikun-furigana';
const SHARED_COOKIE = 'lite_furi';
const COOKIE_AGE = 2_592_000; // 30 days — same as lite's _COOKIE_MAX_AGE

function readSharedCookie(): boolean | null {
	if (!browser) return null;
	const m = document.cookie.match(/(?:^|;\s*)lite_furi=(0|1)(?:;|$)/);
	if (!m) return null;
	return m[1] === '1';
}

function syncSharedCookie(on: boolean): void {
	if (!browser) return;
	document.cookie = `${SHARED_COOKIE}=${on ? '1' : '0'}; path=/; max-age=${COOKIE_AGE}; samesite=lax`;
}

function stored(): boolean {
	if (!browser) return true;
	// The shared cookie is authoritative in both directions.
	const c = readSharedCookie();
	if (c !== null) return c;
	// Fall back to localStorage for the full-variant-only preference.
	return safeStorage.get(KEY) !== 'off';
}

let on = $state(stored());

function apply(): void {
	if (!browser) return;
	syncSharedCookie(on);
}

if (browser) {
	apply();
	addEventListener('storage', (e) => {
		if (e.key !== KEY) return;
		on = stored();
		apply();
	});
	// Poll the shared cookie on focus, since cookies have no change event.
	addEventListener('visibilitychange', () => {
		if (document.visibilityState !== 'visible') return;
		const c = readSharedCookie();
		if (c !== null && c !== on) {
			on = c;
			safeStorage.set(KEY, on ? 'on' : 'off');
		}
	});
}

export const furigana = {
	get on() {
		return on;
	},
	toggle() {
		on = !on;
		safeStorage.set(KEY, on ? 'on' : 'off');
		apply();
	}
};
