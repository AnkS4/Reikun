<script lang="ts">
	import EsConjugationsView from '#lib/components/EsConjugationsView.svelte';
	import JaConjugationsView from '#lib/components/JaConjugationsView.svelte';
	import { currentPack } from '#lib/lang/pack.ts';
</script>

{#if currentPack() === 'es'}
	<EsConjugationsView />
{:else}
	<JaConjugationsView />
{/if}
