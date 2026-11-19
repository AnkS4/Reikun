import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';
import pkg from './package.json' with { type: 'json' };

export default defineConfig({
	// Build-time app version for the About page (`__APP_VERSION__` global,
	// declared in src/app.d.ts). The release checklist keeps web/package.json
	// equal to pyproject.toml, so this is the same version the API reports —
	// inlined into the bundle, no runtime request.
	define: { __APP_VERSION__: JSON.stringify(pkg.version) },
	preview: {
		proxy: {
			'/api': {
				target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			},
			'/lite': {
				target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
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
					// content) is not hashed by SvelteKit — pin its sha256 manually.
					// If you edit the JSON-LD, update this hash or it is ignored
					// (crawlers lose the WebApplication entry; nothing breaks).
					'script-src': ['self', 'sha256-96O4ANVx5qN/vB/eYqW/7eBVA7RBWLIFsIwfLNI09Ak='],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'font-src': ['self'],
					'connect-src': ['self'],
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
});
