<script module lang="ts">
	// marked + DOMPurify load lazily on the first explain click — keeps them
	// out of the initial bundle since most searches never use them. Module
	// scope: one renderer shared by every row.
	let md = $state<((t: string) => string) | null>(null);
	let mdPromise: Promise<void> | null = null;
	async function loadMd() {
		if (md) return;
		if (!mdPromise) {
			mdPromise = Promise.all([import('marked'), import('dompurify')]).then(
				([{ marked }, { default: DOMPurify }]) => {
					// async: false narrows marked v16's parse() overload to string.
					md = (t) => DOMPurify.sanitize(marked.parse(t, { async: false }));
				}
			);
		}
		try {
			await mdPromise;
		} catch (err) {
			// A rejected import stays rejected forever otherwise — reset it so
			// the next Explain click retries instead of failing for the session.
			mdPromise = null;
			throw err;
		}
	}
</script>

<script lang="ts">
	import { explainStream, type ExampleSentence, type Level } from '#lib/api.ts';
	import KanjiText from './KanjiText.svelte';
	import Feedback from './Feedback.svelte';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n.svelte.ts';

	let {
		ex,
		level,
	}: { ex: ExampleSentence; level: Level } = $props();

	let expl = $state.raw<{
		level: string;
		text: string;
		id: number | null;
		provider: string;
		model: string;
	} | null>(null);
	let streaming = $state(false);
	let streamText = $state('');
	let failed = $state(false);
	let errorText = $state('');

	async function explain() {
		const lvl = level; // pinned: a mid-stream level change mustn't relabel this expl.
		streaming = true;
		streamText = '';
		failed = false;
		errorText = '';
		try {
			await loadMd();
			const done = await explainStream(
				{ sentence: ex.japanese, english: ex.english, level: lvl },
				(chunk) => (streamText += chunk)
			);
			expl = {
				level: lvl,
				text: streamText.trim() || t('explanationUnavailable'),
				id: done.explanation_id,
				provider: done.provider ?? '',
				model: done.model ?? ''
			};
		} catch (e) {
			// Keep whatever streamed so far in streamText — discarding it would throw away
			// content the user already read. The partial block renders with role="alert".
			errorText = e instanceof Error ? e.message : String(e);
			failed = true;
		} finally {
			streaming = false;
		}
	}
</script>

<div class="example-row">
	<div class="example-body">
		<p class="sentence" lang="ja"><KanjiText text={ex.japanese} /></p>
		{#if ex.english}<p class="en">{ex.english}</p>{/if}
	</div>
	<div class="example-actions">
		{#if !expl || expl.level !== level}
			<button
				type="button"
				class="btn-3d"
				disabled={streaming}
				onclick={explain}
				title={t('explainTitle')}
			>
				<Icon name="bot" size={16} />
				<span>{expl ? t('explainAgain') : t('explain')}</span>
				<span class="level-indicator">{level}</span>
			</button>
		{/if}
	</div>
</div>
{#if streaming}
	<div class="explain-out" role="status" aria-live="polite" aria-busy="true">
		<pre class="stream-text">{streamText}</pre><span class="spinner" aria-hidden="true"></span>
	</div>
{:else if failed}
	<div class="explain-out explain-failed" role="alert">
		{#if streamText.trim()}
			{#if md}{@html md(streamText.trim())}{:else}<pre class="stream-text">{streamText}</pre>{/if}
		{/if}
		<p class="explain-error">
			<Icon name="warning" size={18} />
			<span>{t('explanationFailed')}{errorText ? ` ${errorText}` : ''}</span>
		</p>
	</div>
{:else if expl}
	<div class="explain-out">
		{#if md}{@html md(expl.text)}{:else}<pre class="stream-text">{expl.text}</pre>{/if}
	</div>
	<p class="caption">
		{t('aiGenerated', { level: expl.level })}{expl.provider ? ` · ${expl.provider}` : ''}{expl.model
			? ` · ${expl.model}`
			: ''}
		<Feedback kind="explanation" refId={expl.id} query={ex.japanese} />
	</p>
{/if}
