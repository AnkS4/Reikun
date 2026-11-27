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
 *   senses          — per-sense { glosses, pos }; pos is a wiktextract tag
 *                     ("verb", "adj"…), not JMdict's coarse tags
 *   inflected_forms — conjugation rows { form: label, surface, kana: null };
 *                     verbs only, up to ~200 rows (a full conjugation stack)
 *   kanji_form / ruby / related — always null / [] for es
 */

import type { components } from '../openapi';
import type { SearchResponse } from '#lib/api.ts';
import { t, type MessageKey } from '#lib/i18n.svelte.ts';

type ApiResult = components['schemas']['SearchResult'];

/** One sense of an es entry, as the card displays it. */
export interface EsSense {
	/** English glosses for this sense (the primary display). */
	glosses: string[];
	/** Raw POS tags (wiktextract, e.g. "verb", "adj") — render via esPosLabel. */
	pos: string[];
}

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
	/** Per-sense view; empty when the entry ships no senses. */
	senses: EsSense[];
	/** Conjugation rows grouped for display; empty for non-verbs. */
	inflectedForms: EsInflectionGroup[];
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
	[/\bimperative\b/, 'Imperative'],
	[/\bsubjunctive\b/, 'Subjunctive'],
	[/\bconditional\b/, 'Conditional'],
	[/\bindicative\b/, 'Indicative'],
	[/\b(infinitive|gerund|participle|impersonal)\b/, 'Non-finite forms']
];
const CONJ_OTHER = 'Other forms';

function groupInflections(rows: ApiResult['inflected_forms']): EsInflectionGroup[] {
	const groups: EsInflectionGroup[] = [];
	const byLabel = new Map<string, EsInflectionGroup>();
	for (const r of rows) {
		if (!r.surface) continue;
		const form = r.form.toLowerCase();
		let label = CONJ_OTHER;
		for (const [re, l] of CONJ_GROUPS) {
			if (re.test(form)) {
				label = l;
				break;
			}
		}
		let g = byLabel.get(label);
		if (!g) {
			g = { label, rows: [] };
			byLabel.set(label, g);
			groups.push(g);
		}
		g.rows.push({ form: r.form, surface: r.surface });
	}
	return groups;
}

/** Shape one raw result into the display view. */
export function shapeEs(r: ApiResult): EsResult {
	return {
		reading: r.reading,
		ipa: r.ipa ?? null,
		meanings: r.meanings ?? [],
		// `definitions_es` is not declared on the shared SearchResult model yet
		// (app/api.py), so the generated type doesn't carry it — read it
		// defensively and let the field land here when the model gains it.
		definitionsEs: (r as { definitions_es?: string[] | null }).definitions_es ?? [],
		senses: (r.senses ?? []).map((s) => ({ glosses: s.glosses ?? [], pos: s.pos ?? [] })),
		inflectedForms: groupInflections(r.inflected_forms ?? [])
	};
}

/** Shape a whole /es/search response. */
export function shapeEsResponse(resp: SearchResponse): EsResult[] {
	return resp.results.map(shapeEs);
}
