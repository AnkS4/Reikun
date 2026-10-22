/**
 * Scheduled-only entrypoint for the `reikun` Worker.
 *
 * Qdrant Cloud's free cluster auto-pauses on inactivity (measured in days),
 * which 503s every /search until something wakes it. Nothing pings it today,
 * so this cron hits the API's /ready — the endpoint that exercises the real
 * read path (a count + a scroll on the collection) — once a day. Free on all
 * three sides: Workers cron triggers are free, one Cloud Run request/day is
 * noise against min_instances=0, and the Qdrant free cluster doesn't bill
 * wake-ups. (A 48-hour cycle is not valid cron — hours only cycle 0-23 —
 * so a daily expression is the nearest well-under 2-day schedule; the
 * Plan.md note about 5-minute keep-alive monitors does NOT apply here:
 * daily pings cannot hold a Cloud Run instance warm.)
 *
 * HTTP requests reach this script only for paths the static-assets router
 * cannot match: the fetch handler below serves the neutral SPA shell
 * (200.html) so client-rendered routes (e.g. /kanji-group?by=grade&value=1)
 * render instead of hydrating the prerendered home page. The assets router
 * serves everything that matches, and no other request reaches the Worker.
 *
 * Optional alerting: if the `ALERT_WEBHOOK` secret is set (wrangler secret
 * put ALERT_WEBHOOK; e.g. a Discord/Slack incoming webhook), a non-2xx or a
 * network failure POSTs a short status line. Not set → console.error only,
 * visible in Workers Logs (observability enabled in wrangler.jsonc).
 */

// Baked in at wrangler-config level (`vars` in wrangler.jsonc) — the same API
// URL the frontend embeds at build time via PUBLIC_API_BASE.
export default {
	async fetch(request, env) {
		// The SPA shell — adapter-static's 200.html fallback (a neutral shell,
		// unlike index.html, which is the prerendered home page). Served with a
		// 200 so the client router can take over the requested URL.
		const shell = await env.ASSETS.fetch(new URL('/200.html', request.url));
		const headers = new Headers(shell.headers);
		headers.set('content-type', 'text/html; charset=utf-8');
		headers.set('cache-control', 'no-cache');
		return new Response(shell.body, { status: 200, headers });
	},
	async scheduled(_, env, ctx) {
		const base = env.API_URL;
		if (!base) {
			console.error("keepalive: API_URL not set");
			return;
		}
		ctx.waitUntil(
			(async () => {
				try {
					const res = await fetch(`${base}/ready`, {
						signal: AbortSignal.timeout(10_000),
					});
					if (!res.ok) {
						const body = await res.text().catch(() => "");
						console.error(`keepalive: /ready ${res.status} ${body.slice(0, 200)}`);
						await alert(env, `${base}/ready → ${res.status}`);
					} else {
						console.log("keepalive: /ready ok");
					}
				} catch (e) {
					console.error(`keepalive: /ready unreachable: ${e?.message ?? e}`);
					await alert(env, `${base}/ready unreachable: ${e?.message ?? e}`);
				}
			})(),
		);
	},
};

async function alert(env, message) {
	if (!env.ALERT_WEBHOOK) return;
	try {
		await fetch(env.ALERT_WEBHOOK, {
			method: "POST",
			headers: { "content-type": "application/json" },
			body: JSON.stringify({ text: `[reikun keep-alive] ${message}` }),
			signal: AbortSignal.timeout(10_000),
		});
	} catch {
		// The alert channel being down must not mask the original failure —
		// it already went to console.error.
	}
}
