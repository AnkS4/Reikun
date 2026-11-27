/**
 * The active language pack — which dictionary this origin serves.
 *
 * The Spanish edition serves from es.reikun.app (its own host); every other
 * origin is the Japanese original. The pack is fixed per origin, so a plain
 * function (not reactive state) is enough — components call it where needed.
 *
 * Why the pack exists: the same SPA build serves both sites. The prerendered
 * home (index.html) is the Japanese one; the Worker serves the neutral shell
 * (200.html) for the es host's "/" so the client can render the Spanish home
 * instead (web/worker.js).
 */
export type Pack = 'ja' | 'es';

const ES_HOST = 'es.reikun.app';

export function currentPack(): Pack {
	if (typeof location !== 'undefined' && location.hostname === ES_HOST) return 'es';
	return 'ja';
}

/** The emblem artwork per pack — the Spanish sun takes the flag's gold. */
export function emblemSrc(pack: Pack = currentPack()): string {
	return pack === 'es' ? '/icons/emblem-es.svg' : '/icons/emblem.svg';
}

/** The product's wordmark line per pack (kept in English — the same
 *  untranslatable-subtext rule as brand.ts). */
export function brandSubtext(pack: Pack = currentPack()): string {
	return pack === 'es'
		? 'The open Spanish dictionary & reading assistant'
		: 'Semantic Japanese Dictionary & Reading Assistant';
}
