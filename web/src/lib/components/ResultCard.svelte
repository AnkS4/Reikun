<script lang="ts">
	import type { Level, SearchResult } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import ExampleRow from './ExampleRow.svelte';
	import Icon from './Icon.svelte';
	let {
		result,
		level,
		onPickKanji,
		onSearchWord,
		active = false,
		searched = null
	}: {
		result: SearchResult;
		level: Level;
		onPickKanji: (c: string) => void;
		onSearchWord?: (q: string) => void;
		active?: boolean;
		searched?: string | null;
	} = $props();

	let copied = $state(false);
	let conjOpen = $state(false);
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
	{#if searched && result.inflection}
		<p class="inflection-bar">
			<span lang="ja">{searched}</span>
			— {result.inflection.toLowerCase()} form of this word
		</p>
	{/if}
	{#if result.inflected_forms?.length}
		<div class="conj-section">
			<button
				type="button"
				class="conj-toggle"
				onclick={() => (conjOpen = !conjOpen)}
				aria-expanded={conjOpen}
			>
				Conjugations <span class="conj-count">{result.inflected_forms.length}</span>
				<Icon name="expand-more" size={14} />
			</button>
			{#if conjOpen}
				<table class="conj-table">
					<tbody>
						{#each result.inflected_forms as row (row.form)}
							<tr>
								<th scope="row">{row.form}</th>
								<td lang="ja">{row.surface}</td>
								<td class="conj-kana" lang="ja">{row.kana ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>
	{/if}
	{#if onSearchWord && result.related?.length}
		<div class="related-row" aria-label="Related words">
			{#each result.related as w (w.kanji_form || w.reading)}
				<button
					type="button"
					class="related-pill"
					title="Search {w.kanji_form || w.reading}"
					onclick={() => onSearchWord(w.kanji_form || w.reading)}
				>
					<span lang="ja"><Ruby parts={w.ruby} tips={false} /></span>
					<span class="related-gloss">{w.gloss}</span>
				</button>
			{/each}
		</div>
	{/if}
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
