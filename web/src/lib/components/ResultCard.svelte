<script lang="ts">
	import { goto } from '$app/navigation';
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
	let timer: ReturnType<typeof setTimeout> | undefined;

	/** Build URL for the conjugations page. */
	const conjHref = $derived.by(() => {
		const word = result.kanji_form || result.reading;
		if (!word) return '';
		const params = new URLSearchParams({ word });
		if (result.reading && result.reading !== word) params.set('reading', result.reading);
		return `/conjugations?${params}`;
	});

	/** Navigate to the conjugations page, passing pre-loaded data via state. */
	function openConj(e: MouseEvent) {
		e.preventDefault();
		if (!conjHref) return;
		goto(conjHref, { state: { conjRows: result.inflected_forms } });
	}

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
			<a
				class="conj-toggle"
				href={conjHref}
				onclick={openConj}
				title="View all conjugations"
			>
				<Icon name="book-open" size={13} />
				<span class="conj-label">Conjugations</span>
				<span class="conj-count">{result.inflected_forms.length}</span>
				<Icon name="arrow-right" size={11} />
			</a>
		</div>
	{/if}
	{#if onSearchWord && result.related?.length}
		<div class="related-row" aria-label="Related words">
			{#each result.related as w, i ((w.kanji_form || w.reading) + (w.reading ?? '') + i)}
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
