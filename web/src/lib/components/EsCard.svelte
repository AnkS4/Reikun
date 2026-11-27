<script lang="ts">
	import { t } from '#lib/i18n.svelte.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { esPosLabel, type EsResult } from '#lib/lang/es.ts';

	/**
	 * One Spanish-pack result card. Same visual language as the ja
	 * ResultCard (`.result-card` + sense blocks), but the es pack's fields:
	 * English meanings/senses primary, native Spanish definitions secondary,
	 * IPA badge in the furigana slot, conjugation table inline (the ja card
	 * links out to /conjugations — an es page has no such page yet, and the
	 * es tables are self-contained, so they collapse in place under
	 * <details>; a verb ships 100–200 rows and must not push the next
	 * results off screen by default).
	 */
	let { result, style = '' }: { result: EsResult; style?: string } = $props();

	// Total rows across groups — the summary's count.
	const conjCount = $derived(result.inflectedForms.reduce((n, g) => n + g.rows.length, 0));
</script>

<div class="result-card" {style}>
	<div class="result-head">
		<span class="headword es-headword" lang="es">{result.reading}</span>
		{#if result.ipa}
			<!-- Pronunciation — the es pack's furigana slot; muted mono badge -->
			<span class="es-ipa" lang="es">{result.ipa}</span>
		{/if}
	</div>

	<!-- English side first: per-sense blocks (glosses + POS) when the entry
	     ships senses, else the flattened meanings list. -->
	<div class="es-defs">
		<!-- "EN" is a language tag, not chrome prose — plain string on purpose
		     (title carries the explanation for pointer users). -->
		<p class="es-defs-label" title="English meanings">EN</p>
		{#if result.senses.length}
			{#each result.senses as s, si (si)}
				<div class="sense-block">
					<div class="sense-line">
						{#if s.glosses.length}
							<p class="sense-glosses">{s.glosses.join('; ')}</p>
						{/if}
						{#if s.pos.length}
							<p class="sense-badges">
								{#each s.pos.slice(0, 3) as tag (tag)}<span class="badge pos">{esPosLabel(tag)}</span>{/each}
							</p>
						{/if}
					</div>
				</div>
			{/each}
		{:else if result.meanings.length}
			<p class="meanings-line">{result.meanings.join('; ')}</p>
		{/if}
	</div>

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

	{#if result.inflectedForms.length}
		<details class="es-conj">
			<summary>
				<Icon name="split" size={16} />
				<span class="es-conj-label">{t('conjugations')}</span>
				<span class="conj-count">{conjCount}</span>
				<Icon name="expand-more" size={16} />
			</summary>
			{#each result.inflectedForms as group (group.label)}
				<p class="es-conj-group-label">{group.label}</p>
				<!-- The conjugations page's table classes, reused as-is (2-column
				     variant: es rows have no kana column). -->
				<table class="conj-page-table">
					<thead>
						<tr>
							<th scope="col">{t('form')}</th>
							<th scope="col">{t('written')}</th>
						</tr>
					</thead>
					<tbody>
						<!-- Index keys: the same surface can ship twice under different
						     tag sets (builder unions en+es edition rows). -->
						{#each group.rows as row, ri (ri)}
							<tr>
								<th scope="row">{row.form}</th>
								<td lang="es">{row.surface}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/each}
		</details>
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

	/* Collapsible conjugation table. The summary mirrors the ja card's
	   .conj-toggle chip (same palette vars), with a chevron instead of the
	   arrow — open/close, not navigation. */
	.es-conj {
		margin-top: var(--space-3);
	}

	.es-conj summary {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		border: 1px solid var(--conj-border);
		background: var(--conj-bg);
		color: var(--conj);
		border-radius: var(--radius-xs);
		padding: 0.24rem 0.65rem;
		font: inherit;
		font-size: var(--fs-xs);
		font-weight: 500;
		cursor: pointer;
		list-style: none;
		transition:
			color var(--dur-base) var(--ease),
			background-color var(--dur-base) var(--ease),
			border-color var(--dur-base) var(--ease);
	}

	.es-conj summary::-webkit-details-marker {
		display: none;
	}

	.es-conj summary:hover {
		border-color: var(--conj-border-hover);
		background: var(--conj-bg-hover);
		color: var(--conj-hover);
	}

	.es-conj summary :global(svg:last-child) {
		opacity: 0.6;
		transition: transform var(--dur-base) var(--ease);
	}

	.es-conj[open] summary :global(svg:last-child) {
		transform: rotate(180deg);
	}

	.es-conj-group-label {
		margin: var(--space-3) 0 var(--space-1);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-faint);
	}

	/* Tables are wide on phones — let them scroll in place instead of
	   stretching the card (the conj page's labels are shorter). */
	.es-conj table {
		display: block;
		overflow-x: auto;
	}
</style>
