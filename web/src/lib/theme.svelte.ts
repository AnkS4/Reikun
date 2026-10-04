/**
 * Theme store: System / Light / Dark, persisted to localStorage. app.html's
 * inline script applies the persisted choice before first paint; this module
 * keeps it in sync afterwards.
 */
import { browser } from '$app/env';

export type ThemeChoice = 'system' | 'light' | 'dark';
const KEY = 'reikun-theme';
const CHOICES: readonly ThemeChoice[] = ['system', 'light', 'dark'];

function stored(): ThemeChoice {
	if (!browser) return 'system';
	const v = localStorage.getItem(KEY) as ThemeChoice | null;
	return v && CHOICES.includes(v) ? v : 'system';
}

let choice = $state<ThemeChoice>(stored());

function resolved(): 'light' | 'dark' {
	if (choice !== 'system') return choice;
	return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function apply(): void {
	if (!browser) return;
	document.documentElement.dataset.theme = resolved();
}

if (browser) {
	apply();
	matchMedia('(prefers-color-scheme: dark)').addEventListener('change', apply);
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
