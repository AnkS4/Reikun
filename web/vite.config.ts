import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter({ fallback: '200.html' }),
			preprocess: vitePreprocess(),
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
