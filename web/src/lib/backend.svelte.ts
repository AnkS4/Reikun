/**
 * Shared "is the API slow or unreachable?" state.
 *
 * The API sits on a scale-to-zero host (Cloud Run), so the first request after
 * a quiet spell can take 10–30 s. api.ts wraps every request in begin()/done:
 * if one is still pending after SLOW_MS the state flips to 'waking' and
 * <WakeBanner> tells the user the server is starting — from any page, for any
 * button — instead of the UI just sitting there.
 *
 *   idle   no request made yet
 *   ready  the last request got an HTTP answer from the API
 *   waking a request has been pending longer than SLOW_MS (cold start / retry)
 *   down   retries exhausted without ever reaching the API
 */
export type BackendState = 'idle' | 'waking' | 'ready' | 'down';

const SLOW_MS = 1200;

let state = $state<BackendState>('idle');
let seq = 0;
const active = new Set<number>();

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
		const timer = setTimeout(() => {
			if (active.has(id)) state = 'waking';
		}, SLOW_MS);
		return (reachable) => {
			clearTimeout(timer);
			active.delete(id);
			if (reachable) state = 'ready';
			else if (active.size === 0) state = 'down';
		};
	}
};
