/**
 * Explicit environment-variable schema (SvelteKit 3). PUBLIC_API_BASE is
 * public (reachable from client code) and static (build-time inlined — this
 * is a static site, so the API URL is baked into the build). Set it in the
 * host's project env for production deploys.
 */
import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_API_BASE: {
		public: true,
		static: true,
		schema: (value) => value || 'http://localhost:8000',
		description: 'Base URL of the Reikun API (no trailing slash)'
	},
	PUBLIC_CF_ANALYTICS_TOKEN: {
		public: true,
		static: true,
		schema: (value) => value || '',
		description:
			'Cloudflare Web Analytics beacon token — optional; get it from the CF dashboard ' +
			'(Web Analytics → enable reikun.app → copy the JS snippet token). Empty string disables the beacon.'
	}
});
