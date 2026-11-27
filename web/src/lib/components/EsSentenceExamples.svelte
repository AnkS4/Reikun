<script lang="ts">
	import type { EsExampleSentence } from '#lib/api.ts';
	import { t } from '#lib/i18n.svelte.ts';

	let { examples }: { examples: EsExampleSentence[] } = $props();
</script>

{#if examples.length}
	<details class="es-examples">
		<summary><span>{t('esExamples')}</span><span class="conj-count">{examples.length}</span></summary>
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
</style>
