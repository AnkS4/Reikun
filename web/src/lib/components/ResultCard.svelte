<script lang="ts">
	import type { Level, SearchResult } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import ExampleRow from './ExampleRow.svelte';
	import Icon from './Icon.svelte';
	let {
		result,
		level,
		onPickKanji,
		active = false
	}: { result: SearchResult; level: Level; onPickKanji: (c: string) => void; active?: boolean } = $props();

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	// Anki / notes format: 高い【たかい】— high, tall, expensive
	const wordLine = $derived.by(() => {
		const head = result.kanji_form && result.kanji_form !== result.reading
			? `${result.kanji_form}【${result.reading}】`
			: result.reading || result.kanji_form || '';
		return `${head}— ${result.meanings.slice(0, 3).join(', ')}`;
	});

	async function copyWord() {
		try {
			await navigator.clipboard.writeText(wordLine);
			copied = true;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = false), 1500);
		} catch {
			/* clipboard blocked */
		}
	}

	const examples = $derived(result.example_sentences.slice(0, 3));
</script>

<div class="result-card" class:kbd-active={active}>
	<div class="result-head">
		<span class="headword" lang="ja"><Ruby parts={result.ruby} onpick={onPickKanji} /></span>
		{#if result.is_common}<span class="badge">common</span>{/if}
		<button
			type="button"
			class="btn tertiary copy-word"
			title={copied ? 'Copied' : 'Copy as 高い【たかい】— meaning'}
			aria-label={copied ? 'Copied' : 'Copy word and meaning'}
			onclick={copyWord}
		>
			<Icon name={copied ? 'check' : 'copy'} size={15} />
		</button>
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
