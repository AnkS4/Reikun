/**
 * Kanji hover-card cache: components call wantKanji() for each kanji they
 * render; requests are deduped, then flushed to one /kanji batch call per
 * microtask (a whole sentence of tips costs a single round-trip).
 */
import { SvelteMap } from 'svelte/reactivity';
import { apiKanjiBatch, type KanjiHover } from '#lib/api.ts';
import { isKanji } from '#lib/kanji.ts';

export const hovers = new SvelteMap<string, KanjiHover | null>();
const queued = new Set<string>();
const inflight = new Set<string>();
let scheduled = false;

export function wantKanji(chars: Iterable<string>): void {
	for (const c of chars) {
		if (isKanji(c) && !hovers.has(c) && !inflight.has(c)) queued.add(c);
	}
	if (queued.size && !scheduled) {
		scheduled = true;
		queueMicrotask(flush);
	}
}

async function flush(): Promise<void> {
	scheduled = false;
	const chars = Array.from(queued).slice(0, 100); // endpoint's max_length
	for (const c of chars) queued.delete(c);
	if (!chars.length) return;
	// >100 unique kanji queued: send this batch, then flush the remainder.
	if (queued.size) {
		scheduled = true;
		queueMicrotask(flush);
	}
	for (const c of chars) inflight.add(c);
	try {
		const data = await apiKanjiBatch(chars.join(''));
		for (const c of chars) hovers.set(c, data[c] ?? null);
	} catch {
		// Tips are best-effort — an unreachable API leaves plain text.
		for (const c of chars) hovers.set(c, null);
	} finally {
		for (const c of chars) inflight.delete(c);
	}
}
