<script lang="ts">
	import { explainStream, type ExampleSentence, type Level } from '#lib/api.ts';
	import KanjiText from './KanjiText.svelte';
	import Feedback from './Feedback.svelte';
	import Icon from './Icon.svelte';

	let {
		ex,
		level,
		onpick
	}: { ex: ExampleSentence; level: Level; onpick?: (char: string) => void } = $props();

	let expl = $state<{ level: string; text: string; id: number | null; model: string } | null>(null);
	let streaming = $state(false);
	let streamText = $state('');

	// marked + DOMPurify load lazily on the first explain click — keeps them
	// out of the initial bundle since most searches never use them.
	let md = $state<((t: string) => string) | null>(null);
	async function loadMd() {
		if (md) return;
		const [{ marked }, { default: DOMPurify }] = await Promise.all([
			import('marked'),
			import('dompurify')
		]);
		md = (t) => DOMPurify.sanitize(marked.parse(t, { async: false }) as string);
	}

	async function explain() {
		streaming = true;
		streamText = '';
		try {
			await loadMd();
			const done = await explainStream(
				{ sentence: ex.japanese, english: ex.english, level },
				(chunk) => (streamText += chunk)
			);
			expl = {
				level,
				text: streamText.trim() || 'Explanation unavailable.',
				id: done.explanation_id,
				model: done.model ?? ''
			};
		} catch (e) {
			expl = {
				level,
				text: `**Explanation unavailable:** ${e instanceof Error ? e.message : e}`,
				id: null,
				model: ''
			};
		} finally {
			streaming = false;
		}
	}
</script>

<div class="example-row">
	<div class="example-body">
		<p class="sentence"><KanjiText text={ex.japanese} {onpick} /></p>
		{#if ex.english}<p class="en">{ex.english}</p>{/if}
	</div>
	{#if !expl || expl.level !== level}
		<button
			class="btn {expl ? 'tertiary' : 'secondary'}"
			disabled={streaming}
			onclick={explain}
			title="JLPT-calibrated grammar explanation for this sentence"
		>
			<Icon name="school" size={15} />
			{expl ? 'Explain again' : 'Explain grammar'} · {level}
		</button>
	{/if}
</div>
{#if streaming}
	<div class="explain-out"><pre class="stream-text">{streamText}</pre><span class="spinner"></span></div>
{:else if expl}
	<div class="explain-out">{@html md ? md(expl.text) : ''}</div>
	<p class="caption">
		AI-generated for {expl.level}{expl.model ? ` · ${expl.model}` : ''}
		<Feedback kind="explanation" refId={expl.id} query={ex.japanese} />
	</p>
{/if}
