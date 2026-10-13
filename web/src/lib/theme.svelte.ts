/**
 * Theme store: System / Light / Dark, persisted to localStorage. app.html's
 * inline script applies the persisted choice before first paint; this module
 * keeps it in sync afterwards.
 */
import { browser } from '$app/env';
import { safeStorage } from './storage.ts';

export type ThemeChoice = 'system' | 'light' | 'dark' | 'oled';
const KEY = 'reikun-theme';
const CHOICES: readonly ThemeChoice[] = ['system', 'light', 'dark', 'oled'];

// Cached once at module load — avoids repeated matchMedia() calls in apply().
const darkQuery = browser ? matchMedia('(prefers-color-scheme: dark)') : null;

function stored(): ThemeChoice {
	if (!browser) return 'system';
	const v = safeStorage.get(KEY);
	if (v === 'amoled') return 'oled'; // legacy value — renamed to the generic term
	return v && CHOICES.includes(v as ThemeChoice) ? (v as ThemeChoice) : 'system';
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
