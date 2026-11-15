<script lang="ts">
	import KanjiTip from './KanjiTip.svelte';
	import { isKanji } from '#lib/kanji.ts';
	let { text, tips = true }: { text: string; tips?: boolean } = $props();
</script>

{#each [...text] as ch}
	{#if tips && isKanji(ch)}<KanjiTip char={ch} />{:else}{ch}{/if}
{/each}
