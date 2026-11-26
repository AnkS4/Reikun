import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig, loadEnv } from 'vite';
import pkg from './package.json' with { type: 'json' };

export default defineConfig(({ mode }) => {
	// VITE_* values from the environment or a .env file (host default: local API).
	const env = loadEnv(mode, '.', 'VITE_API_PROXY_');
	const proxyTarget = env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000';
	// PUBLIC_* values too — the CSP below must mirror what this build actually
	// bakes in (both are inlined at build time, so an unset token means the
	// beacon never loads and the policy stays tight).
	const publicEnv = loadEnv(mode, '.', 'PUBLIC_');

	// Cloudflare Web Analytics: when PUBLIC_CF_ANALYTICS_TOKEN is set,
	// +layout.svelte injects the beacon from static.cloudflareinsights.com at
	// runtime, and the beacon reports back to cloudflareinsights.com. Allow
	// exactly those two origins, and only then — without a token script-src
	// keeps the same tight policy as before the beacon existed. Typed via
	// the same Config['csp'] shape the directives object below feeds (kit
	// allows ActionSource on script-src but not connect-src), so the
	// conditional pushes stay inside kit's Source union instead of widening
	// the lists to plain string[] (which the directives field rejects).
	type CspList<K extends 'script-src' | 'connect-src'> = NonNullable<
		NonNullable<NonNullable<import('@sveltejs/kit/vite').Config['csp']>['directives']>[K]
	>;
	const scriptSrc: CspList<'script-src'> = ['self', 'sha256-u5qiMJj6cmTN2Q7HXdXBEfOVVdG1Ow5zDPgJLM1bx0k='];
	const connectSrc: CspList<'connect-src'> = ['self'];
	if (publicEnv.PUBLIC_CF_ANALYTICS_TOKEN) {
		scriptSrc.push('https://static.cloudflareinsights.com');
		connectSrc.push('https://cloudflareinsights.com');
	}
	// The browser calls PUBLIC_API_BASE directly (src/lib/api.ts), so the
	// origin it names must be in connect-src in every mode — a self-hosted
	// production build with an absolute cross-origin base (the env.ts schema
	// explicitly supports that: "Base URL of the Reikun API") would otherwise
	// have every API call blocked by the policy baked below. Unset in
	// development falls back to the env.ts default (http://localhost:8000);
	// production deploys bake a same-origin /api path (docker-compose), which
	// 'self' already covers, keeping the tight list.
	const apiBase =
		publicEnv.PUBLIC_API_BASE || (mode === 'development' ? 'http://localhost:8000' : '');
	if (/^https?:\/\//.test(apiBase)) {
		// Absolute http(s) bases only — a relative /api needs no origin. The
		// cast keeps the push inside kit's Source union (new URL().origin is a
		// plain string to TS); an origin always fits HostSource's shape.
		connectSrc.push(new URL(apiBase).origin as CspList<'connect-src'>[number]);
	}

	return {
	// Build-time app version for the About page (`__APP_VERSION__` global,
	// declared in src/app.d.ts). The release checklist keeps web/package.json
	// equal to pyproject.toml, so this is the same version the API reports —
	// inlined into the bundle, no runtime request.
	define: { __APP_VERSION__: JSON.stringify(pkg.version) },
	preview: {
		proxy: {
			'/api': {
				target: proxyTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			},
			'/lite': {
				target: proxyTarget,
				changeOrigin: true
			}
		}
	},
	plugins: [
		sveltekit({
			adapter: adapter({ fallback: '200.html' }),
			// Local preview parity with production: the browser talks to the same
			// origin at /api (and /lite), and the preview server proxies to the
			// API container — exactly like the Cloudflare Worker does in prod.
			// VITE_API_PROXY_TARGET overrides the default local API address.
			// (docker-compose's web service bakes PUBLIC_API_BASE=/api.)
			preprocess: vitePreprocess(),
			// Real CSP in place of the frame-ancestors-only posture: SvelteKit
			// hashes its own inline boot scripts; every hand-written script is an
			// external file (theme-init.js). 'unsafe-inline' stays only on styles
			// (inline style attributes, e.g. the body's `display: contents`).
			csp: {
				mode: 'hash',
				directives: {
					'default-src': ['self'],
					// The inline JSON-LD block in app.html (structured data, static
					// content) is not hashed by SvelteKit — pin its sha256 manually
					// (sha256 of the script's exact inner content). If you edit the
					// JSON-LD, update this hash or it is ignored (crawlers lose the
					// WebApplication entry; nothing breaks). The analytics origins
					// and the API origin (PUBLIC_API_BASE) are appended to these
					// two lists conditionally above.
					'script-src': scriptSrc,
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'font-src': ['self'],
					'connect-src': connectSrc,
					'object-src': ['none'],
					'base-uri': ['none'],
					'form-action': ['self'],
					'frame-ancestors': ['none']
				}
			},
			prerender: {
				handleUnseenRoutes: 'ignore',
				// With PUBLIC_API_BASE=/api, links to /api and /lite are same-origin,
				// so the crawler follows them. Those paths are served by the Worker
				// proxy (web/worker.js), not by this static build: skip them, and
				// keep every other broken link a build error.
				handleHttpError: ({ path, message }) => {
					if (/^\/(api|lite)(\/|$)/.test(path)) return;
					throw new Error(message);
				}
			}
		})
	]
	};
});
