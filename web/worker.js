/**
 * Entry point for the `reikun` Worker: same-origin proxy + SPA fallback +
 * Qdrant keep-alive cron.
 *
 * The SPA and the lite UI both live behind reikun.app, and cookies are
 * host-scoped — serving the API (and with it the `/lite` variant) through the
 * same origin is what makes the cross-variant theme/recent-searches cookies
 * actually work in production. Routing:
 *
 *   /api/*   → the Cloud Run API, with the `/api` prefix stripped
 *              (the SPA bakes PUBLIC_API_BASE=/api at build time)
 *   /lite*   → the Cloud Run API's server-rendered lite UI, path as-is
 *   (other)  → static assets (handled by the assets router before this
 *              script unless `run_worker_first` lists the path), falling
 *              back to the neutral SPA shell for client-rendered deep links.
 *
 * `run_worker_first` (wrangler.jsonc) is needed because the assets router
 * otherwise serves statics before the Worker ever runs; without it /api and
 * /lite would still reach the script (nothing matches them as assets), but
 * relying on that incidental behavior makes adding an asset named e.g.
 * `lite/` silently break the proxy.
 *
 * 303 navigations matter here: the lite toggles (theme, language, furigana,
 * recent-clear, random kanji) set cookies on their redirect responses, so
 * `redirect: 'manual'` passes them through untouched — following redirects
 * server-side would swallow the Set-Cookie and silently break the toggles.
 *
 * Identity: the Worker rewrites X-Forwarded-For to the client IP Cloudflare
 * observed and signs it with X-Reikun-Proxy / X-Reikun-Client; the API trusts
 * that header pair (shared PROXY_IDENTITY_TOKEN) because every hop between
 * Worker and Cloud Run appends to XFF, which would otherwise end with a
 * single shared egress address for all visitors.
 *
 * Keep-alive cron (`scheduled`): one /ready hit per day stops the Qdrant
 * Cloud free cluster from auto-pausing. Daily is the cheapest valid cron
 * under the multi-day pause threshold (a 48-hour cycle is not valid cron —
 * hours only cycle 0-23).
 *
 * Optional alerting: if the `ALERT_WEBHOOK` secret is set (wrangler secret
 * put ALERT_WEBHOOK; e.g. a Discord/Slack incoming webhook), a non-2xx or a
 * network failure POSTs a short status line. Not set → console.error only,
 * visible in Workers Logs (observability enabled in wrangler.jsonc).
 */

// API_URL: the Cloud Run origin (`vars` in wrangler.jsonc).
// PROXY_TOKEN: shared secret with the API's PROXY_IDENTITY_TOKEN
// (set as a Worker secret / dashboard env — never committed).
export default {
	async fetch(request, env) {
		const url = new URL(request.url);
		const api = (env.API_URL || "").replace(/\/+$/, "");
		if (api) {
			if (url.pathname === "/lite" || url.pathname.startsWith("/lite/")) {
				return proxy(request, api + url.pathname + url.search, env);
			}
			if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
				const path = url.pathname.slice("/api".length) || "/";
				return proxy(request, api + path + url.search, env);
			}
		}
		// The SPA shell — adapter-static's 200.html fallback (a neutral shell,
		// unlike index.html, which is the prerendered home page). Served with a
		// 200 so the client router can take over the requested URL.
		const shell = await env.ASSETS.fetch(new URL("/200.html", request.url));
		const headers = new Headers(shell.headers);
		headers.set("content-type", "text/html; charset=utf-8");
		headers.set("cache-control", "no-cache");
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

async function proxy(request, target, env) {
	const headers = new Headers(request.headers);
	// The outgoing fetch sets Host from the target URL; a forwarded Host
	// (reikun.app) would fail Cloud Run's host validation.
	headers.delete("host");
	const client = request.headers.get("cf-connecting-ip");
	if (client) {
		// True caller, exactly once, stated by the proxy that saw it. Cloud Run
		// still appends our egress IP, so strict rightmost-XFF readers see a
		// shared address — the API keys on the signed header instead.
		headers.set("x-forwarded-for", client);
		headers.set("x-reikun-client", client);
		if (env.PROXY_TOKEN) headers.set("x-reikun-proxy", env.PROXY_TOKEN);
	}
	try {
		// The API's POST bodies are tiny JSON (feedback, explain, hover
		// batches) — buffered, so the proxy needs no streaming-request
		// scaffolding across runtimes (undici's `duplex` vs the Workers
		// runtime, which rejects that key).
		const body =
			request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
		return await fetch(target, {
			method: request.method,
			headers,
			body,
			redirect: "manual",
			signal: AbortSignal.timeout(60_000),
		});
	} catch (e) {
		console.error(`proxy: ${new URL(target).pathname} unreachable: ${e?.message ?? e}`);
		return new Response(JSON.stringify({ detail: "The dictionary API is unreachable right now." }), {
			status: 502,
			headers: { "content-type": "application/json" },
		});
	}
}

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
