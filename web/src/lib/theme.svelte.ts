/**
 * Theme store: System / Light / Dark / OLED, persisted to localStorage.
 * The `lite_theme` cookie is the shared channel with the server-rendered lite
 * UI (different port, cookies are not port-scoped) and is authoritative in
 * both directions — switching the theme in either variant applies to both on
 * the next load. lite's single dark maps onto the oled canvas, preserving an
 * existing dark/oled preference. app.html's inline script applies the same
 * resolution before first paint; this module keeps it in sync afterwards.
 */
import { browser } from '$app/env';
import { safeStorage } from '#lib/storage.ts';

export type ThemeChoice = 'system' | 'light' | 'dark' | 'oled';
const KEY = 'reikun-theme';
const CHOICES: readonly ThemeChoice[] = ['system', 'light', 'dark', 'oled'];

// Cross-variant sync: the lite UI (server-rendered, on the API origin's port)
// stores its theme in the `lite_theme` cookie (see app/lite.py). Cookies are
// NOT port-scoped, so both variants see it on shared localhost hosts — the
// full version writes it too, and reads it when nothing is stored locally.
// A pinned light is shared as 'light'; dark and oled both share as 'dark'
// (lite has a single dark = oled-black); system is shared as "no cookie".
const SHARED_COOKIE = 'lite_theme';
const COOKIE_AGE = 2_592_000; // 30 days — same as lite's _COOKIE_MAX_AGE

function readSharedCookie(): 'light' | 'dark' | null {
	if (!browser) return null;
	const m = document.cookie.match(/(?:^|;\s*)lite_theme=(light|dark|oled)(?:;|$)/);
	if (!m) return null;
	return m[1] === 'light' ? 'light' : 'dark'; // oled (legacy) resolves to dark
}

function syncSharedCookie(c: ThemeChoice): void {
	if (!browser) return;
	// A pinned choice is shared with the lite UI through the cookie; system
	// removes it so lite falls back to its own system resolution.
	const value = c === 'system' ? '' : c === 'light' ? 'light' : 'dark';
	document.cookie =
		value === ''
			? `${SHARED_COOKIE}=; path=/; max-age=0; samesite=lax`
			: `${SHARED_COOKIE}=${value}; path=/; max-age=${COOKIE_AGE}; samesite=lax`;
}

// Cached once at module load — avoids repeated matchMedia() calls in apply().
const darkQuery = browser ? matchMedia('(prefers-color-scheme: dark)') : null;

function stored(): ThemeChoice {
	if (!browser) return 'system';
	// The shared cookie is authoritative in both directions: whichever variant
	// you switched last decides the look for both. Map lite's single dark onto
	// the dark flavour you already had here — an existing dark/oled choice
	// keeps its flavour, otherwise the oled canvas (lite's dark IS oled-black).
	const c = readSharedCookie();
	if (c) {
		if (c === 'dark') {
			const v = safeStorage.get(KEY); // never throws (see below)
			if (v === 'dark' || v === 'oled') return v as ThemeChoice;
			return 'oled';
		}
		return 'light';
	}
	const v = safeStorage.get(KEY); // never throws — a blocked store must not take the app down at import time
	if (v === 'amoled') return 'oled'; // legacy value — renamed to the generic term
	if (v && CHOICES.includes(v as ThemeChoice)) return v as ThemeChoice;
	return 'system';
}

let choice = $state<ThemeChoice>(stored());

function resolved(): 'light' | 'dark' | 'oled' {
	if (choice !== 'system') return choice;
	// NOTE: 'oled' is intentionally the default dark resolution for system preference (not 'dark').
	return darkQuery?.matches ? 'oled' : 'light';
}

// Browser-UI colour per resolved theme — keep in sync with --bg in app.css and
// the inline script in app.html.
const CHROME_COLOR = { light: '#fcfaf6', dark: '#0f1620', oled: '#000000' } as const;

function apply(): void {
	if (!browser) return;
	const r = resolved();
	document.documentElement.dataset.theme = r;
	document.getElementById('theme-color')?.setAttribute('content', CHROME_COLOR[r]);
	syncSharedCookie(choice);
}

if (browser) {
	apply();
	darkQuery?.addEventListener('change', apply);
	// Another tab changed the theme — follow it.
	addEventListener('storage', (e) => {
		if (e.key !== KEY) return;
		choice = stored();
		apply();
	});
}

export const theme = {
	get choice() {
		return choice;
	},
	set(c: ThemeChoice) {
		choice = c;
		safeStorage.set(KEY, c);
		apply();
	}
};
