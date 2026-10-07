<script lang="ts">
	import KanjiTip from './KanjiTip.svelte';
	import { isKanji } from '#lib/kanji.ts';
	let {
		text,
		tips = true,
		onpick
	}: { text: string; tips?: boolean; onpick?: (char: string) => void } = $props();
</script>

{#each [...text] as ch}
	{#if tips && isKanji(ch)}<KanjiTip char={ch} {onpick} />{:else}{ch}{/if}
{/each}
