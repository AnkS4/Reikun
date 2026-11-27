<script lang="ts">
	import { apiEsExplain, ES_CEFR_LEVELS, type EsCefrLevel, type EsExampleSentence } from '#lib/api.ts';
	import { i18n, t } from '#lib/i18n.svelte.ts';

	let { examples }: { examples: EsExampleSentence[] } = $props();
	let level = $state<EsCefrLevel>('A1');
	let busyId = $state<number | null>(null);
	let explanations = $state<Record<number, string>>({});
	let errors = $state<Record<number, string>>({});

	async function explain(example: EsExampleSentence) {
		busyId = example.spanish_id;
		errors[example.spanish_id] = '';
		try {
			const response = await apiEsExplain({
				sentence: example.spanish,
					english: example.english,
					level,
					language: i18n.locale === 'es' ? 'es' : 'en'
			});
			explanations[example.spanish_id] = response.text;
		} catch (error) {
			errors[example.spanish_id] = error instanceof Error ? error.message : t('esExplainFailed');
		} finally {
			busyId = null;
		}
	}
</script>

{#if examples.length}
	<details class="es-examples">
		<summary><span>{t('esExamples')}</span><span class="conj-count">{examples.length}</span></summary>
		<div class="es-example-controls">
			<label for="es-cefr-level">{t('esCefrLevel')}</label>
			<select id="es-cefr-level" bind:value={level}>
				{#each ES_CEFR_LEVELS as option (option)}<option value={option}>{option}</option>{/each}
			</select>
		</div>
		{#each examples as example (example.spanish_id)}
			<article class="es-example">
				<p lang="es">{example.spanish}</p>
				<p lang="en">{example.english}</p>
				<p class="es-example-credit">
					<a href="https://tatoeba.org/en/sentences/show/{example.spanish_id}" target="_blank" rel="noopener noreferrer">
						{t('esTatoebaSentence', { id: example.spanish_id })}
					</a>
					{#if example.spanish_author}{t('esTatoebaBy', { author: example.spanish_author })}{/if};
					<a href="https://tatoeba.org/en/sentences/show/{example.english_id}" target="_blank" rel="noopener noreferrer">
						{t('esTatoebaTranslation', { id: example.english_id })}
					</a>
					{#if example.english_author}{t('esTatoebaBy', { author: example.english_author })}{/if} · {example.license}
				</p>
				<button type="button" class="btn tertiary es-explain-button" disabled={busyId === example.spanish_id} onclick={() => explain(example)}>
					{busyId === example.spanish_id ? t('esExplaining') : t('esExplain') + ' · ' + level}
				</button>
				{#if explanations[example.spanish_id]}
					<p class="es-explanation" aria-live="polite">{explanations[example.spanish_id]}</p>
				{:else if errors[example.spanish_id]}
					<p class="error-banner" role="alert">{errors[example.spanish_id]}</p>
				{/if}
			</article>
		{/each}
	</details>
{/if}

<style>
	.es-examples {
		margin-top: var(--space-3);
		border-top: 1px solid var(--border-soft);
		padding-top: var(--space-2);
	}

	.es-examples > summary {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		cursor: pointer;
		font-weight: 500;
		list-style: none;
	}

	.es-examples > summary::-webkit-details-marker {
		display: none;
	}

	.es-example-controls {
		display: flex;
		align-items: center;
		gap: var(--space-2);
		margin-top: var(--space-2);
	}

	.es-example-controls select {
		padding: 0.2rem var(--space-2);
	}

	.es-example {
		margin-top: var(--space-3);
		padding-top: var(--space-2);
		border-top: 1px solid var(--border-soft);
	}

	.es-example p {
		margin: var(--space-1) 0;
	}

	.es-example-credit {
		color: var(--text-muted);
		font-size: var(--fs-xs);
		line-height: 1.5;
		overflow-wrap: anywhere;
	}

	.es-explain-button {
		min-height: 2rem;
		padding: 0.2rem var(--space-2);
		font-size: var(--fs-sm);
	}

	.es-explanation {
		white-space: pre-wrap;
	}
</style>
