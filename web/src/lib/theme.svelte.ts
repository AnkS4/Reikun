/**
 * Theme store: System / Light / Dark, persisted to localStorage. app.html's
 * inline script applies the persisted choice before first paint; this module
 * keeps it in sync afterwards.
 */
import { browser } from '$app/env';

export type ThemeChoice = 'system' | 'light' | 'dark' | 'oled';
const KEY = 'reikun-theme';
const CHOICES: readonly ThemeChoice[] = ['system', 'light', 'dark', 'oled'];

// Cached once at module load — avoids repeated matchMedia() calls in apply().
const darkQuery = browser ? matchMedia('(prefers-color-scheme: dark)') : null;

function stored(): ThemeChoice {
	if (!browser) return 'system';
	const v = localStorage.getItem(KEY);
	if (v === 'amoled') return 'oled'; // legacy value — renamed to the generic term
	return v && CHOICES.includes(v as ThemeChoice) ? (v as ThemeChoice) : 'system';
}

let choice = $state<ThemeChoice>(stored());

function resolved(): 'light' | 'dark' | 'oled' {
	if (choice !== 'system') return choice;
	// NOTE: 'oled' is intentionally the default dark resolution for system preference (not 'dark').
	return darkQuery?.matches ? 'oled' : 'light';
}

function apply(): void {
	if (!browser) return;
	document.documentElement.dataset.theme = resolved();
}

if (browser) {
	apply();
	darkQuery?.addEventListener('change', apply);
}

export const theme = {
	get choice() {
		return choice;
	},
	set(c: ThemeChoice) {
		choice = c;
		localStorage.setItem(KEY, c);
		apply();
	}
};
