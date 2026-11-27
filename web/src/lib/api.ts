/**
 * Typed client for the Reikun API (app/api.py) — schema types come from the
 * generated openapi.d.ts (scripts/export_openapi.py + openapi-typescript).
 *
 * The base URL is a *public* build-time value: this is a static site, so
 * PUBLIC_API_BASE is baked in at build time (set in the host's project env).
 */
import createClient from 'openapi-fetch';
import { PUBLIC_API_BASE } from '$app/env/public';
import type { components, paths } from './openapi';
import { backend } from './backend.svelte.ts';
import { t } from './i18n.svelte.ts';

export type SearchResponse = components['schemas']['SearchResponseModel'];
export type SearchResult = components['schemas']['SearchResult'];
export type SenseResult = components['schemas']['SenseResult'];
export type ExampleSentence = components['schemas']['ExampleSentence'];
export type Segment = components['schemas']['Segment'];
export type RubyPart = components['schemas']['RubyPart'];
export type KanjiCard = components['schemas']['KanjiCard'];
export type KanjiHover = components['schemas']['KanjiHover'];
export type StrokeData = components['schemas']['StrokeData'];
export type KanjiGroupResponse = components['schemas']['KanjiGroupResponse'];
export type LoanwordsResponse = components['schemas']['LoanwordsResponse'];
export type LoanwordsPageResponse = components['schemas']['LoanwordsPageResponse'];
export type LoanwordFacet = components['schemas']['LoanwordFacet'];
export type ReadyInfo = components['schemas']['ReadyResponse'];
export type ExplainRequest = components['schemas']['ExplainRequest'];
export type Level = ExplainRequest['level'];

export const LEVELS: readonly Level[] = ['N5', 'N4', 'N3', 'N2', 'N1'];

export const API_BASE = PUBLIC_API_BASE.replace(/\/+$/, '');

const client = createClient<paths>({ baseUrl: API_BASE });

export class ApiError extends Error {
	/** `status` 0 = no HTTP response at all (offline, DNS, CORS, or our own timeout). */
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

/** Transient = worth an automatic retry: no response, timeouts, gateway blips. */
export const isTransient = (e: unknown): boolean =>
	e instanceof ApiError && (e.status === 0 || e.status === 502 || e.status === 503 || e.status === 504);

export const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

/** Turn an openapi-fetch error body into a useful message (FastAPI uses `detail`). */
function asError(err: unknown, status: number): ApiError {
	const body = err as { detail?: unknown } | undefined;
	let msg: string;
	if (typeof body?.detail === 'string') {
		msg = body.detail;
	} else if (Array.isArray(body?.detail)) {
		msg = (body.detail as { msg?: string }[]).map((d) => d.msg ?? d).join('; ');
	} else if (status === 502 || status === 503 || status === 504) {
		msg = t('errorGateway');
	} else {
		msg = t('errorRequestFailed', { status });
	}
	return new ApiError(status, msg);
}

/** Raw fetch failures (TypeError: Failed to fetch / NetworkError…, timeouts) → friendly ApiError(0). */
function normalize(e: unknown): unknown {
	if (e instanceof ApiError) return e;
	if (e instanceof TypeError) return new ApiError(0, t('errorUnreachable'));
	if (e instanceof DOMException && (e.name === 'TimeoutError' || e.name === 'AbortError')) {
		return new ApiError(0, t('errorTimeout'));
	}
	return e;
}

/** AbortSignal.timeout() with a fallback for older WebViews that lack it. */
function timeoutSignal(ms: number): AbortSignal {
	if (typeof AbortSignal.timeout === 'function') return AbortSignal.timeout(ms);
	const ctrl = new AbortController();
	setTimeout(() => ctrl.abort(new DOMException('Timed out', 'TimeoutError')), ms);
	return ctrl.signal;
}

// A Cloud Run cold start (container boot + model load) can take 10–30 s, so each
// attempt gets a generous window; the backoff keeps retries from hammering it.
const TIMEOUT_MS = 25_000;
const RETRY_DELAYS_MS = [800, 1600];

/**
 * Run one logical API operation with a per-attempt timeout, automatic retries
 * for transient failures, and cold-start reporting (see backend.svelte.ts).
 * Errors are normalised to ApiError so callers can show `e.message` as-is.
 */
async function call<T>(op: (signal: AbortSignal) => Promise<T>, timeoutMs = TIMEOUT_MS): Promise<T> {
	const done = backend.begin();
	let last: unknown;
	for (let attempt = 0; ; attempt++) {
		try {
			const result = await op(timeoutSignal(timeoutMs));
			done(true);
			return result;
		} catch (raw) {
			last = normalize(raw);
			if (!isTransient(last) || attempt >= RETRY_DELAYS_MS.length) break;
			await sleep(RETRY_DELAYS_MS[attempt]);
		}
	}
	done(!isTransient(last)); // a 4xx/422 still proves the server answered
	throw last;
}

export function apiReady(): Promise<ReadyInfo> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/ready', { signal });
		if (error) throw asError(error, response.status);
		return data;
	}, 35_000); // also wakes Qdrant Cloud's free cluster, which can sleep too
}

let readyPromise: Promise<ReadyInfo> | null = null;
// Monotonic attempt id: a superseded attempt (WakeBanner's retry started a
// newer one) must not publish its late outcome over the newer attempt's.
let readySeq = 0;

/**
 * One /ready request shared by the layout (which fires it at app start to wake
 * the server) and the header's status dot. A failure clears the cache so a
 * later call retries. The outcome lands in shared reactive state
 * (backend.ready) rather than living only in the returned promise, so a
 * successful retry updates the header even though it never re-subscribed.
 */
export function apiReadyShared(): Promise<ReadyInfo> {
	if (!readyPromise) {
		const seq = ++readySeq;
		readyPromise = apiReady().then(
			(r) => {
				if (seq === readySeq) backend.setReady(true, r.entries);
				return r;
			},
			(e) => {
				if (seq === readySeq) {
					backend.setReady(false, null, e instanceof Error ? e.message : t('apiUnreachable'));
					readyPromise = null;
				}
				throw e;
			}
		);
	}
	return readyPromise;
}

/** Forget any cached result and ping again — the banner's Retry button. */
export function apiWake(): Promise<ReadyInfo> {
	readyPromise = null;
	return apiReadyShared();
}

export function apiSearch(q: string, n: number): Promise<SearchResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/search', { params: { query: { q, n } }, signal });
		if (error) throw asError(error, response.status);
		return data;
	});
}

/** Spanish pack search (/es/search) — same response shape, different corpus. */
export function esSearch(q: string, n: number): Promise<SearchResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/es/search', { params: { query: { q, n } }, signal });
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiKanjiBatch(chars: string): Promise<Record<string, KanjiHover | null>> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/kanji', { params: { query: { chars } }, signal });
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiKanjiCard(char: string): Promise<KanjiCard> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/kanji/{char}', {
			params: { path: { char }, query: { strokes: true } },
			signal
		});
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiRandomKanji(level: Level): Promise<string> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/kanji/random', { params: { query: { level } }, signal });
		if (error) throw asError(error, response.status);
		return data.kanji;
	});
}

export type GroupKey = 'strokes' | 'grade' | 'jlpt' | 'freq';
export type KanjiGroupsResponse = components['schemas']['KanjiGroupsResponse'];

export function apiKanjiGroups(): Promise<KanjiGroupsResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/kanji/groups', { signal });
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiKanjiGroup(by: GroupKey, value: number, n = 40, offset = 0): Promise<KanjiGroupResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/kanji/group', {
			params: { query: { by, value, n, offset } },
			signal
		});
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiLoanwords(): Promise<LoanwordsResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/loanwords', { signal });
		if (error) throw asError(error, response.status);
		return data;
	});
}

export function apiLoanwordsLang(lang: string, n = 50, offset = 0): Promise<LoanwordsPageResponse> {
	return call(async (signal) => {
		const { data, error, response } = await client.GET('/loanwords/{lang}', {
			params: { path: { lang }, query: { n, offset } },
			signal
		});
		if (error) throw asError(error, response.status);
		return data;
	});
}

export async function apiFeedback(
	kind: 'search' | 'explanation',
	refId: number | null,
	rating: 1 | -1,
	query: string | null
): Promise<void> {
	await client.POST('/feedback', {
		body: { kind, ref_id: refId, rating, query },
		signal: timeoutSignal(8_000)
	});
	// 201 has no meaningful body; failures are telemetry noise — callers ignore.
}

export interface ExplainDone {
	explanation_id: number | null;
	latency_ms: number;
	provider?: string;
	model?: string;
}

type SsePayload = {
	text?: string;
	error?: string;
	done?: boolean;
	explanation_id?: number | null;
	latency_ms?: number;
	provider?: string;
	model?: string;
};

/**
 * POST /explain/stream — SSE: `data: {"text": …}` chunks, then a `done` event
 * (or `error`). fetch+reader rather than EventSource because it's a POST. The
 * `done` frame is required: EOF without one rejects, so a stream the server
 * never finished surfaces as a failure over the partial text already shown.
 *
 * Only the connect phase (request → response headers) has a timeout and
 * automatic retries — that is where a cold start bites. Once text is flowing
 * the stream is left alone: a timer that outlived the headers would abort a
 * healthy, still-streaming explanation.
 */
export async function explainStream(
	req: ExplainRequest,
	onText: (chunk: string) => void
): Promise<ExplainDone> {
	const res = await call(async () => {
		const ctrl = new AbortController();
		const timer = setTimeout(() => ctrl.abort(new DOMException('Timed out', 'TimeoutError')), 30_000);
		try {
			const r = await fetch(`${API_BASE}/explain/stream`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(req),
				signal: ctrl.signal
			});
			if (!r.ok || !r.body) {
				const body = await r.json().catch(() => null);
				throw asError(body, r.status);
			}
			return r;
		} finally {
			clearTimeout(timer);
		}
	});
	const body = res.body!;
	const reader = body.getReader();
	const dec = new TextDecoder();
	let buf = '';
	let done: ExplainDone | null = null;
	try {
		for (;;) {
			const { done: eof, value } = await reader.read();
			if (eof) break;
			buf += dec.decode(value, { stream: true });
			let match: RegExpMatchArray | null;
			while ((match = buf.match(/\r?\n\r?\n/))) {
				const idx = match.index!;
				const frame = buf.slice(0, idx).replace(/\r/g, '');
				buf = buf.slice(idx + match[0].length);
				if (!frame.startsWith('data: ')) continue; // keep-alive comments etc.
				let payload: SsePayload;
				try {
					payload = JSON.parse(frame.slice(6)) as SsePayload;
				} catch {
					continue; // one malformed frame shouldn't sink the whole explanation
				}
				if (payload.text) {
					onText(payload.text);
				} else if (payload.error) {
					throw new ApiError(502, payload.error);
				} else if (payload.done) {
					done = {
						explanation_id: payload.explanation_id ?? null,
						latency_ms: payload.latency_ms ?? 0,
						provider: payload.provider,
						model: payload.model
					};
				}
			}
		}
	} catch (e) {
		// Release the socket instead of leaving the stream to GC — an error
		// frame aborts the read loop mid-body.
		await reader.cancel().catch(() => {});
		// A connection cut mid-explanation (proxy EOF, crash, process kill)
		// surfaces here as a body-level network error, not a clean EOF — the
		// done frame is the only proof the explanation finished, so a
		// non-ApiError with no `done` is the same truncation the post-loop
		// check catches for a clean EOF. Server error frames (ApiError) keep
		// their own message. Either way the partial text stays on screen.
		if (!done && !(e instanceof ApiError)) throw new ApiError(502, t('errorStreamEnded'));
		throw normalize(e);
	} finally {
		// cancel() already released the lock on the error path; release it on
		// the success path (a double release is harmless but throws).
		try {
			reader.releaseLock();
		} catch {
			/* already released */
		}
	}
	// The server ends every normal stream with an explicit done frame — EOF
	// without one means the connection died mid-explanation (proxy cut, crash,
	// process kill). The chunks already handed to onText stay on screen: the
	// caller's catch path keeps the partial text and flags it as failed rather
	// than dressing an unfinished stream up as a complete result with a
	// fabricated (null-id, zero-latency) footer.
	if (!done) throw new ApiError(502, t('errorStreamEnded'));
	return done;
}
