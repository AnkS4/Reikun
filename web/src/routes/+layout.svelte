<script lang="ts">
	import { page } from '$app/state';
	import { onNavigate } from '$app/navigation';
	import { API_BASE } from '#lib/api.ts';
	import '../app.css';
	let { children } = $props();

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
	<title>Reikun (例訓) — Semantic Japanese Dictionary</title>
	<!-- Canonical is per-route (the app is also served on the workers.dev
	     mirror); prerendered into the HTML since SSR is on. -->
	<link rel="canonical" href="https://reikun.app{page.url.pathname}" />
	<!-- The API is on another origin: open the connection while the JS boots. -->
	{#if API_BASE}<link rel="preconnect" href={API_BASE} crossorigin="anonymous" />{/if}
</svelte:head>

<a class="skip-link" href="#main">Skip to main content</a>

<main id="main" tabindex="-1">
	{@render children()}
</main>
