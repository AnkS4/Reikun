/**
 * Spanish language pack — the web-side seam of the LanguagePack architecture
 * (local/research/sister-sites/spanish-sister-site-plan.md §3): this module is
 * the single place that knows the shape of the /es/search payload. Components
 * render `EsResult` views and never touch the raw API types, so the ja pack's
 * SearchResult assumptions (kanji forms, ruby, JMdict POS tags) can't leak in.
 *
 * How the es payload differs from the ja one it reuses (both are the shared
 * `SearchResult` schema — the es pack fills a subset and a few extra fields):
 *   reading         — the Spanish word (the headword)
 *   ipa             — pronunciation; often null (the es pack's furigana slot)
 *   meanings        — ENGLISH glosses, the primary display (what the embedder
 *                     sees, exactly like JMdict glosses for the ja pack)
 *   definitions_es  — native Spanish definitions, the secondary display
 *   senses          — native per-sense data; pos is a wiktextract tag
 *                     ("verb", "adj"…), not JMdict's coarse tags
 *   inflected_forms — conjugation rows { form: label, surface, kana: null };
 *                     verbs only, native table with English-edition supplements
 *   kanji_form / ruby / related — always null / [] for es
 */

import type { components } from '../openapi';
import type { SearchResponse } from '#lib/api.ts';
import { t, type MessageKey } from '#lib/i18n.svelte.ts';

type ApiResult = components['schemas']['SearchResult'];

/** Conjugation rows bucketed by mood/non-finite group, payload order kept. */
export interface EsInflectionGroup {
	/** Group heading, e.g. "Indicative" (plain English — see esPosLabel). */
	label: string;
	/** Form label + written surface, e.g. "first-person singular present indicative" / "hablo". */
	rows: { form: string; surface: string }[];
}

/** Display view of one es entry — everything the /es card needs, nothing else. */
export interface EsResult {
	/** The Spanish word. */
	reading: string;
	/** IPA transcription, when the extract ships one. */
	ipa: string | null;
	/** English glosses — the primary display. */
	meanings: string[];
	/** Native Spanish definitions — the secondary display. */
	definitionsEs: string[];
	/** Raw Wiktionary POS tags. The builder writes the same POS on each sense. */
	pos: string[];
	etymologyEs: string[];
	originLanguages: string[];
	/** Tatoeba Spanish-English pairs with sentence-ID and contributor attribution. */
	examples: components['schemas']['EsExampleSentence'][];
	/** Number of sourced conjugation rows available on the verb's own page. */
	conjugationCount: number;
}

/** POS tags whose wording matches shared chrome reuse their i18n keys. */
const POS_KEYS: Record<string, MessageKey> = {
	verb: 'posVerb',
	noun: 'posNoun',
	adv: 'posAdv',
	interj: 'posIntj'
};

/**
 * wiktextract's tag set is wider than the ja pack's coarse tags; tags without
 * a fitting shared key get a plain-English label (localized es keys can't be
 * added without touching files outside this layer's scope — swap them in when
 * they land in shared i18n). Unknown tags fall back to the raw value.
 */
const POS_LABELS: Record<string, string> = {
	adj: 'Adjective',
	name: 'Proper noun',
	prep: 'Preposition',
	prep_phrase: 'Prepositional phrase',
	pron: 'Pronoun',
	conj: 'Conjunction',
	det: 'Determiner',
	num: 'Numeral',
	article: 'Article',
	participle: 'Participle',
	abbrev: 'Abbreviation'
};

/** Tag → display label. Lives here (not in the component) because the mapping
 *  is es-pack knowledge; called in the template so it stays locale-reactive. */
export function esPosLabel(tag: string): string {
	const key = POS_KEYS[tag];
	if (key) return t(key);
	return POS_LABELS[tag] ?? tag;
}

/**
 * Group label lookup for conjugation rows. The `form` label is wiktextract's
 * tags joined with spaces ("first-person singular indicative present") — tag
 * order varies, so this matches anywhere in the string; first hit wins and the
 * group order below is the display order (finite moods before non-finite).
 */
const CONJ_GROUPS: [RegExp, string][] = [
	[/\bcombined-form\b/, 'With object pronouns'],
	[/\bconditional\b/, 'Conditional'],
	[/\bsubjunctive\b/, 'Subjunctive'],
	[/\bimperative\b/, 'Imperative'],
	[/\bindicative\b/, 'Indicative'],
	[/\b(infinitive|gerund|participle|impersonal)\b/, 'Non-finite forms']
];
const CONJ_ORDER = [
	'Indicative', 'Conditional', 'Subjunctive', 'Imperative', 'Non-finite forms', 'With object pronouns'
];

export function groupInflections(rows: ApiResult['inflected_forms']): EsInflectionGroup[] {
	const groups: EsInflectionGroup[] = [];
	const byLabel = new Map<string, EsInflectionGroup>();
	for (const r of rows) {
		if (!r.surface || !/\p{L}/u.test(r.surface)) continue;
		const form = r.form.toLowerCase();
		const label = CONJ_GROUPS.find(([pattern]) => pattern.test(form))?.[1];
		if (!label) continue;
		let g = byLabel.get(label);
		if (!g) {
			g = { label, rows: [] };
			byLabel.set(label, g);
			groups.push(g);
		}
		g.rows.push({ form: r.form.replaceAll('-', ' '), surface: r.surface });
	}
	return groups.sort((a, b) => CONJ_ORDER.indexOf(a.label) - CONJ_ORDER.indexOf(b.label));
}

/** Shape one raw result into the display view. */
export function shapeEs(r: ApiResult): EsResult {
	const meanings = r.meanings ?? [];
	const definitionsEs = r.definitions_es ?? [];
	// Native-only entries also carry their Spanish definitions in `meanings`
	// for retrieval. Keep them out of the English display.
	const nativeOnly = meanings.length === definitionsEs.length
		&& meanings.every((meaning, i) => meaning === definitionsEs[i]);
	return {
		reading: r.reading,
		ipa: r.ipa ?? null,
		meanings: nativeOnly ? [] : meanings,
		definitionsEs,
		pos: [...new Set((r.senses ?? []).flatMap((sense) => sense.pos ?? []))],
		etymologyEs: r.etymology_es ?? [],
		originLanguages: r.origin_languages ?? [],
		examples: r.examples_es ?? [],
		conjugationCount: r.inflected_forms?.length ?? 0
	};
}

/** Shape a whole /es/search response. */
export function shapeEsResponse(resp: SearchResponse): EsResult[] {
	return resp.results.map(shapeEs);
}
