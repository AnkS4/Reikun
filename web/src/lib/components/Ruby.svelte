<script lang="ts">
	import type { RubyPart } from '#lib/api.ts';
	import KanjiText from './KanjiText.svelte';
	let {
		parts,
		tips = true,
		onpick
	}: { parts: RubyPart[]; tips?: boolean; onpick?: (char: string) => void } = $props();
</script>

{#each parts as p}
	{#if p.rt}<ruby><KanjiText text={p.text} {tips} {onpick} /><rt>{p.rt}</rt></ruby>{:else}<KanjiText
			text={p.text}
			{tips}
			{onpick}
		/>{/if}
{/each}
