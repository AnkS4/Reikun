<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head>
	<title>Reikun (例訓) — Semantic Japanese Dictionary</title>
</svelte:head>

<main>
	{@render children()}
</main>
