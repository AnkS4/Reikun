import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			// `/` prerenders its own SPA shell as index.html; the 200.html
			// fallback is Cloudflare Pages' convention for unmatched paths.
			adapter: adapter({ fallback: '200.html' }),
			preprocess: vitePreprocess()
		})
	]
});
