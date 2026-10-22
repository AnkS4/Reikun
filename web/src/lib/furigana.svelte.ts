/**
 * Furigana visibility store — a persisted show/hide reading preference,
 * the reading-practice counterpart to the theme store.
 *
 * Ruby.svelte gates its <rt> output on this, so one flag covers result
 * headwords, example rows, segment chips and kanji-card word lists alike.
 * Default: on. Safe on the server (no storage read) so prerendered routes
 * paint default-on and hydration re-evaluates.
 */
import { browser } from '$app/env';
import { safeStorage } from '#lib/storage.ts';

const KEY = 'reikun-furigana';

function stored(): boolean {
	if (!browser) return true;
	// Any stored value other than 'off' means on — so a corrupted entry can
	// never remove readings silently; the toggle writes 'on'/'off' itself.
	return safeStorage.get(KEY) !== 'off';
}

let on = $state(stored());

export const furigana = {
	get on() {
		return on;
	},
	toggle() {
		on = !on;
		safeStorage.set(KEY, on ? 'on' : 'off');
	}
};
