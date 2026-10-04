/**
 * Typed client for the Reikun API (app/api.py) — schema types come from the
 * generated api.d.ts (scripts/dump_openapi.py + openapi-typescript).
 *
 * The base URL is a *public* build-time value: this is a static site, so
 * PUBLIC_API_BASE is baked in at build time (set in the host's project env).
 */
import createClient from 'openapi-fetch';
import { PUBLIC_API_BASE } from '$app/env/public';
import type { components, paths } from './openapi';

export type SearchResponse = components['schemas']['SearchResponseModel'];
export type SearchResult = components['schemas']['SearchResult'];
export type Segment = components['schemas']['Segment'];
export type RubyPart = components['schemas']['RubyPart'];
export type KanjiCard = components['schemas']['KanjiCard'];
export type KanjiHover = components['schemas']['KanjiHover'];
export type CommonWord = components['schemas']['CommonWord'];
export type ReadingChip = components['schemas']['ReadingChip'];
export type MetaBadge = components['schemas']['MetaBadge'];
export type StrokeData = components['schemas']['StrokeData'];
export type ExplainRequest = components['schemas']['ExplainRequest'];
export type Level = ExplainRequest['level'];

export interface ExampleSentence {
	japanese: string;
	english: string;
}
export type LevelStr = 'N5' | 'N4' | 'N3' | 'N2' | 'N1';
export const LEVELS: readonly LevelStr[] = ['N5', 'N4', 'N3', 'N2', 'N1'];

export const API_BASE = PUBLIC_API_BASE.replace(/\/+$/, '');

const client = createClient<paths>({ baseUrl: API_BASE });

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

/** Transient = worth an automatic retry: gateway blips, upstream timeouts, network errors. */
export const isTransient = (e: unknown): boolean =>
	e instanceof TypeError ||
	(e instanceof ApiError && (e.status === 502 || e.status === 503 || e.status === 504));

export const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

/** Turn an openapi-fetch error body into a useful message (FastAPI uses `detail`). */
function asError(err: unknown, status: number): ApiError {
	const body = err as { detail?: unknown } | undefined;
	const msg =
		typeof body?.detail === 'string'
			? body.detail
			: Array.isArray(body?.detail)
				? body.detail.map((d: { msg?: string }) => d.msg ?? d).join('; ')
				: `Request failed (${status})`;
	return new ApiError(status, msg);
}

export interface ReadyInfo {
	status: string;
	collection: string;
	entries: number;
	llm: string;
}

// /ready returns a bare dict (no response_model) — raw fetch keeps the error detail.
export async function apiReady(): Promise<ReadyInfo> {
	const res = await fetch(`${API_BASE}/ready`);
	if (!res.ok) {
		const body = (await res.json().catch(() => null)) as { detail?: string } | null;
		throw new ApiError(res.status, body?.detail ?? `API not ready (${res.status})`);
	}
	return res.json() as Promise<ReadyInfo>;
}

export async function apiSearch(q: string, n: number): Promise<SearchResponse> {
	const { data, error, response } = await client.GET('/search', { params: { query: { q, n } } });
	if (error) throw asError(error, response.status);
	return data;
}

export async function apiKanjiBatch(chars: string): Promise<Record<string, KanjiHover | null>> {
	const { data, error, response } = await client.GET('/kanji', { params: { query: { chars } } });
	if (error) throw asError(error, response.status);
	return data;
}

export async function apiKanjiCard(char: string): Promise<KanjiCard> {
	const { data, error, response } = await client.GET('/kanji/{char}', {
		params: { path: { char }, query: { strokes: true } }
	});
	if (error) throw asError(error, response.status);
	return data;
}

export async function apiRandomKanji(level: string): Promise<string> {
	// /kanji/random returns a bare dict — the failure detail needs the raw response.
	const res = await fetch(`${API_BASE}/kanji/random?level=${level}`);
	if (!res.ok) {
		const body = (await res.json().catch(() => null)) as { detail?: string } | null;
		throw new ApiError(res.status, body?.detail ?? `Request failed (${res.status})`);
	}
	return ((await res.json()) as { kanji: string }).kanji;
}

export async function apiFeedback(
	kind: 'search' | 'explanation',
	refId: number | null,
	rating: 1 | -1,
	query: string | null
): Promise<void> {
	await client.POST('/feedback', { body: { kind, ref_id: refId, rating, query } });
	// 201 has no meaningful body; failures are telemetry noise — callers ignore.
}

export interface ExplainDone {
	explanation_id: number | null;
	latency_ms: number;
	model?: string;
}

/**
 * POST /explain/stream — SSE: `data: {"text": …}` chunks, then a `done` event
 * (or `error`). fetch+reader rather than EventSource because it's a POST.
 */
export async function explainStream(
	req: ExplainRequest,
	onText: (chunk: string) => void
): Promise<ExplainDone> {
	const res = await fetch(`${API_BASE}/explain/stream`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(req)
	});
	if (!res.ok || !res.body) {
		const body = await res.json().catch(() => null);
		throw asError(body, res.status);
	}
	const reader = res.body.getReader();
	const dec = new TextDecoder();
	let buf = '';
	let done: ExplainDone | null = null;
	for (;;) {
		const { done: eof, value } = await reader.read();
		if (eof) break;
		buf += dec.decode(value, { stream: true });
		let idx: number;
		while ((idx = buf.indexOf('\n\n')) >= 0) {
			const frame = buf.slice(0, idx);
			buf = buf.slice(idx + 2);
			if (!frame.startsWith('data: ')) continue;
			const payload = JSON.parse(frame.slice(6)) as {
				text?: string;
				error?: string;
				done?: boolean;
				explanation_id?: number | null;
				latency_ms?: number;
				model?: string;
			};
			if (payload.text) onText(payload.text);
			else if (payload.error) throw new ApiError(502, payload.error);
			else if (payload.done)
				done = {
					explanation_id: payload.explanation_id ?? null,
					latency_ms: payload.latency_ms ?? 0,
					model: payload.model
				};
		}
	}
	return done ?? { explanation_id: null, latency_ms: 0 };
}
