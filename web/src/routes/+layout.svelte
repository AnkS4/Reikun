<script lang="ts">
	import { page } from '$app/state';
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head>
	<title>Reikun (例訓) — Semantic Japanese Dictionary</title>
	<!-- Canonical is per-route (the SPA is also served on the workers.dev mirror);
	     only emitted post-hydration on / since SSR is off there. -->
	<link rel="canonical" href="https://reikun.app{page.url.pathname}" />
</svelte:head>

<main>
	{@render children()}
</main>
