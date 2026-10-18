<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { onNavigate } from '$app/navigation';
	import { API_BASE, apiReadyShared } from '#lib/api.ts';
	import WakeBanner from '#lib/components/WakeBanner.svelte';
	import '../app.css';
	let { children } = $props();

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
	<title>Reikun (例訓) — Semantic Japanese Dictionary</title>
	<!-- Canonical is per-route (the app is also served on the workers.dev
	     mirror); prerendered into the HTML since SSR is on. -->
	<link rel="canonical" href="https://reikun.app{page.url.pathname}" />
	<!-- The API is on another origin: open the connection while the JS boots. -->
	{#if API_BASE}<link rel="preconnect" href={API_BASE} crossorigin="anonymous" />{/if}
</svelte:head>

<a class="skip-link" href="#main">Skip to main content</a>

<WakeBanner />

<main id="main" tabindex="-1">
	{@render children()}
</main>
