<script lang="ts">
	// Thin dispatcher: which dictionary this origin serves. The Spanish
	// edition's host (es.reikun.app) renders the Spanish search home; every
	// other origin renders the Japanese original (prerendered — the pack is
	// 'ja' at build time and the Worker serves the neutral shell for the es
	// host's "/", so hydration never mismatches).
	import { currentPack } from '#lib/lang/pack.ts';
	import EsSearchView from '#lib/components/EsSearchView.svelte';
	import HomeView from '#lib/components/HomeView.svelte';
</script>

{#if currentPack() === 'es'}
	<EsSearchView />
{:else}
	<HomeView />
{/if}
