<script lang="ts">
	import { formatNumber, t } from '#lib/i18n.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import EsSentenceExamples from '#lib/components/EsSentenceExamples.svelte';
	import { esPosLabel, type EsResult } from '#lib/lang/es.ts';

	/**
	 * One Spanish-pack result card. Same visual language as the ja
	 * ResultCard (`.result-card` + sense blocks), but the es pack's fields:
	 * English meanings primary, native Spanish definitions secondary,
	 * IPA badge in the furigana slot, and a link to the verb's conjugation page.
	 */
	let { result, style = '' }: { result: EsResult; style?: string } = $props();

	const conjugationHref = $derived(`/conjugations?${new URLSearchParams({ word: result.reading })}`);
</script>

<div class="result-card" {style}>
	<div class="result-head">
		<span class="headword es-headword" lang="es">{result.reading}</span>
		{#if result.ipa}
			<!-- Pronunciation — the es pack's furigana slot; muted mono badge -->
			<span class="es-ipa" lang="es">{result.ipa}</span>
		{/if}
		{#each result.pos as pos (pos)}
			<span class="badge pos">{esPosLabel(pos)}</span>
		{/each}
	</div>

	{#if result.meanings.length}
		<div class="es-defs">
			<p class="es-defs-label" title="English meanings">EN</p>
			<ul class="es-defs-list" lang="en">
				{#each result.meanings as meaning, i (i)}<li>{meaning}</li>{/each}
			</ul>
		</div>
	{/if}

	{#if result.definitionsEs.length}
		<!-- Native Spanish definitions — secondary block, same structure as the
		     EN block so the two languages read side by side. -->
		<div class="es-defs es-defs-native">
			<p class="es-defs-label" title="Definiciones en español">ES</p>
			<ul class="es-defs-list" lang="es">
				{#each result.definitionsEs.slice(0, 6) as d, i (i)}<li>{d}</li>{/each}
			</ul>
		</div>
	{/if}

	<EsSentenceExamples examples={result.examples} />

	{#if result.etymologyEs.length || result.originLanguages.length}
		<section class="es-etymology" aria-label="Etymology">
			<p class="es-defs-label">Etymology</p>
			{#each result.etymologyEs as text (text)}<p lang="es">{text}</p>{/each}
			{#if result.originLanguages.length}
				<div class="es-origins">
					{#each result.originLanguages as lang (lang)}
						<a class="pill" href="/etymology?{new URLSearchParams({ lang })}" lang="es">{lang}</a>
					{/each}
				</div>
			{/if}
			<a class="es-origin-credit" href="https://es.wiktionary.org/wiki/{encodeURIComponent(result.reading)}#Español">
				Spanish Wiktionary
			</a>
		</section>
	{/if}

	{#if result.conjugationCount}
		<div class="conj-section">
			<a class="conj-toggle" href={conjugationHref} title={t('conjugationsTitle')}>
				<Icon name="split" size={16} />
				<span class="conj-label">{t('conjugations')}</span>
				<span class="conj-count">{formatNumber(result.conjugationCount)}</span>
				<Icon name="arrow-right" size={16} />
			</a>
		</div>
	{/if}
</div>

<style>
	/* Latin headword — the global .headword face is the Japanese stack. */
	.es-headword {
		font-family: var(--font);
	}

	/* IPA — the es pack's pronunciation slot: muted mono pill in the badge
	   row (small caps row on the headword line). */
	.es-ipa {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-muted);
		background: var(--surface-soft);
		border-radius: var(--radius-pill);
		padding: 0.18rem 0.6rem;
	}

	/* EN / ES labeled blocks. */
	.es-defs {
		margin-top: var(--space-3);
		padding: var(--space-2) var(--space-3);
		background: var(--surface-soft);
		border-radius: var(--radius-sm);
	}

	/* The native block sits on the card surface (the EN block keeps the soft
	   wash) so the two languages read as primary vs secondary. */
	.es-defs-native {
		background: transparent;
		border: 1px solid var(--border-soft);
	}

	/* Language tag label — mono micro caps, same voice as .variants-title. */
	.es-defs-label {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-faint);
	}

	.es-defs-list {
		margin: 0.3rem 0 0;
		padding-left: 1.2rem;
		font-size: var(--fs-body);
		color: var(--text);
		line-height: 1.5;
	}

	.es-defs-list li {
		margin: 0.15rem 0;
	}

	.es-etymology {
		margin-top: var(--space-3);
		border-top: 1px solid var(--border-soft);
		padding-top: var(--space-2);
	}

	.es-etymology p:not(.es-defs-label) {
		margin: var(--space-1) 0;
	}

	.es-origins {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-1);
		margin-top: var(--space-1);
	}

	.es-origin-credit {
		display: inline-block;
		margin-top: var(--space-1);
		color: var(--text-muted);
		font-size: var(--fs-xs);
	}

</style>
