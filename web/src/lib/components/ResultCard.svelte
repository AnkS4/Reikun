<script lang="ts">
	import type { Level, SearchResult } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import ExampleRow from './ExampleRow.svelte';
	let {
		result,
		level,
		onPickKanji
	}: { result: SearchResult; level: Level; onPickKanji: (c: string) => void } = $props();

	const examples = $derived(result.example_sentences.slice(0, 3));
</script>

<div class="result-card">
	<div class="result-head">
		<span class="headword"><Ruby parts={result.ruby} onpick={onPickKanji} /></span>
		{#if result.is_common}<span class="badge">common</span>{/if}
	</div>
	<p class="meanings-line">{result.meanings.slice(0, 6).join('; ')}</p>
	{#if examples.length}
		<div class="example-section">
			{#each examples as ex, i (ex.japanese + i)}
				<ExampleRow {ex} {level} onpick={onPickKanji} />
			{/each}
		</div>
	{:else}
		<p class="no-example">No example sentences.</p>
	{/if}
</div>
