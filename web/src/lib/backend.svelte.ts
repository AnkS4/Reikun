/**
 * Shared "is the API cold-starting or unreachable?" state.
 *
 * The API sits on a scale-to-zero host (Cloud Run), so the first request after
 * a quiet spell can take 10–30 s. api.ts wraps every request in begin()/done:
 * if a request is still pending after SLOW_MS *and* the API has not answered
 * recently, the state flips to 'waking' and <WakeBanner> tells the user the
 * server is starting. Normal slow queries (mobile latency, a large kanji
 * batch) must not masquerade as a cold start; their own loading UI covers them.
 *
 *   idle   no request made yet
 *   ready  the last request got an HTTP answer from the API
 *   waking a cold-start request is still pending after SLOW_MS
 *   down   retries exhausted without ever reaching the API
 */
export type BackendState = 'idle' | 'waking' | 'ready' | 'down';

const SLOW_MS = 2500;
// A success this recent means any new slowness is ordinary load, not a cold
// start. Cloud Run only scales to zero after a few minutes of no traffic.
const COLD_IDLE_MS = 60_000;

let state = $state<BackendState>('idle');
let seq = 0;
let lastOkAt = 0;
const active = new Set<number>();

function likelyColdStart(): boolean {
	return lastOkAt === 0 || Date.now() - lastOkAt > COLD_IDLE_MS;
}

export const backend = {
	get state(): BackendState {
		return state;
	},

	/**
	 * Mark one logical operation (including its automatic retries) as started.
	 * Call the returned function exactly once with whether the API was reachable
	 * (any HTTP response counts — a 404 or 422 still proves the server is up).
	 */
	begin(): (reachable: boolean) => void {
		const id = ++seq;
		active.add(id);
		// Only a plausible cold start may show the banner. If the API answered
		// within the last minute, a slow request is just load — the page's own
		// spinner/skeleton already communicates that.
		const timer = likelyColdStart()
			? setTimeout(() => {
					if (active.has(id) && likelyColdStart()) state = 'waking';
				}, SLOW_MS)
			: null;
		return (reachable) => {
			if (timer !== null) clearTimeout(timer);
			active.delete(id);
			if (reachable) {
				lastOkAt = Date.now();
				state = 'ready';
			} else if (active.size === 0) state = 'down';
		};
	}
};
