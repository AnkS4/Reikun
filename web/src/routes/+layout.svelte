<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { onNavigate } from '$app/navigation';
	import { API_BASE, apiReadyShared } from '#lib/api.ts';
	import { PUBLIC_CF_ANALYTICS_TOKEN } from '$app/env/public';
	import WakeBanner from '#lib/components/WakeBanner.svelte';
	import Footer from '#lib/components/Footer.svelte';
	import { i18n, t } from '#lib/i18n.svelte.ts';
	import { BRAND_TITLE } from '#lib/brand.ts';
	import '../app.css';
	let { children } = $props();

	// Persisted interface language. SSR/first render stay English (so the
	// prerendered HTML matches); the stored choice applies right after mount.
	onMount(() => i18n.init());

	// Cloudflare Web Analytics — a free cookieless beacon (no consent banner
	// needed), tracked per page-load; the beacon script covers SPA route
	// changes itself. Token comes from the CF dashboard at build time; unset
	// (empty string) → nothing loads, zero cost.
	onMount(() => {
		if (!PUBLIC_CF_ANALYTICS_TOKEN || document.querySelector('script[data-cf-beacon]')) return;
		const s = document.createElement('script');
		s.defer = true;
		s.src = 'https://static.cloudflareinsights.com/beacon.min.js';
		s.dataset.cfBeacon = JSON.stringify({ token: PUBLIC_CF_ANALYTICS_TOKEN });
		document.head.appendChild(s);
	});

	// Wake the API (and its Qdrant behind it) the moment the app loads, so the
	// cold start overlaps with the user reading the page instead of their first click.
	// Header reads the same shared promise for its status dot; failures surface
	// through <WakeBanner>, so there is nothing to handle here.
	onMount(() => {
		apiReadyShared().catch(() => {});
	});

	// Cross-fade between routes (/ <-> /about) where the browser supports view
	// transitions. Same-page ?q= changes are excluded — results shouldn't fade
	// on every search — and reduced-motion users get an instant swap.
	onNavigate((nav) => {
		if (!document.startViewTransition) return;
		if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		if (nav.from?.url.pathname === nav.to?.url.pathname) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await nav.complete;
			});
		});
	});
</script>

<svelte:head>
	<title>{BRAND_TITLE}</title>
	<!-- Canonical is per-route (the app is also served on the workers.dev
	     mirror); prerendered into the HTML since SSR is on. -->
	<link rel="canonical" href="https://reikun.app{page.url.pathname}" />
	<!-- The API is on another origin: open the connection while the JS boots. -->
	{#if API_BASE}<link rel="preconnect" href={API_BASE} crossorigin="anonymous" />{/if}
</svelte:head>

<a class="skip-link" href="#main">{t('skipToContent')}</a>

<WakeBanner />

<main id="main" tabindex="-1">
	{@render children()}
</main>

<Footer />
