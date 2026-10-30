<script module lang="ts">
	// Reading categories — label, furigana, hover explanation
	const READING_TYPES = [
		{
			key: 'on' as const,
			text: '音読み',
			reading: 'おんよみ',
			tipKey: 'onTip' as const
		},
		{
			key: 'kun' as const,
			text: '訓読み',
			reading: 'くんよみ',
			tipKey: 'kunTip' as const
		}
	];
</script>

<script lang="ts">
	import { ApiError, apiKanjiCard, type KanjiCard as Card } from '#lib/api.ts';
	import { clampTip } from '#lib/tooltip.ts';
	import Ruby from './Ruby.svelte';
	import StrokeSvg from './StrokeSvg.svelte';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n.svelte.ts';
	import { furigana } from '#lib/furigana.svelte.ts';
	let { char }: { char: string } = $props();

	let card = $state.raw<Card | null>(null);
	let missing = $state(false);
	let loadError = $state('');
	$effect(() => {
		const c = char;
		card = null;
		missing = false;
		loadError = '';
		apiKanjiCard(c)
			.then((d) => {
				if (char === c) card = d;
			})
			.catch((e) => {
				if (char !== c) return;
				if (e instanceof ApiError && e.status === 404) missing = true;
				else loadError = e instanceof Error ? e.message : t('kanjiLoadFailed');
			});
	});
</script>

{#if card}
	<div class="kanji-card">
		<div class="kanji-card-left">
			<p class="kanji-big" lang="ja">{char}</p>
			{#if card.stroke}
				<StrokeSvg stroke={card.stroke} />
			{/if}
			{#if card.meta.length}
				<div class="meta-badges">
					{#each card.meta as m (m.label)}
						{#if m.group}
							<!-- Group badges are browse keys: the kanji of the whole
							     group live on their own page (paginated there). -->
							<a
								class="meta-badge clickable meta-badge-{m.group.by}"
								href={`/kanji-group?by=${m.group.by}&value=${m.group.value}&from=${encodeURIComponent(char)}`}
								title={m.tip}
							>
								{#if m.group.by === 'strokes'}
									<Icon name="pencil" size={11} />
								{:else if m.group.by === 'grade'}
									<Icon name="school" size={11} />
								{:else if m.group.by === 'jlpt'}
									<Icon name="sparkles" size={11} />
								{/if}
								<span>{m.label}</span>
								<Icon name="arrow-right" size={10} />
							</a>
						{:else}
							<span class="meta-badge" title={m.tip}>{m.label}</span>
						{/if}
					{/each}
				</div>
			{/if}
		</div>
		<div class="kanji-card-right">
			<div class="kanji-section">
				<p class="kanji-section-title">{t('meanings')}</p>
				{#if card.meanings.length}
					<p class="meanings">
						<span class="first">{card.meanings[0]}</span>{#if card.meanings.length > 1}<span
								class="rest">, {card.meanings.slice(1).join(', ')}</span
							>{/if}
					</p>
				{:else}
					<p class="meanings">—</p>
				{/if}
			</div>

			{#each READING_TYPES as rt (rt.key)}
				{@const chips = card.readings[rt.key] ?? []}
				{#if chips.length}
					<div class="kanji-section">
						<div class="reading-row">
							<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
							<span class="rlabel kanji-tip" tabindex="0" {@attach clampTip}
								>{#if furigana.on}<ruby>{rt.text}<rt>{rt.reading}</rt></ruby>{:else}{rt.text}{/if}<span
									class="kanji-tip-body">{t(rt.tipKey)}</span
								></span
							>
							<span class="reading-list">
								{#each chips as chip, i (chip.stem + (chip.okurigana ?? '') + i)}
									<span class="reading-chip"
										>{chip.stem}{#if chip.okurigana}<span class="oku">{chip.okurigana}</span
											>{/if}</span
									>
								{/each}
							</span>
						</div>
					</div>
				{/if}
			{/each}

			{#if card.common_words.length}
				<div class="kanji-section">
					<p class="kanji-section-title">{t('commonWords')}</p>
					<div class="common-words">
						{#each card.common_words as w, i ((w.kanji_form || w.reading) + i)}
							{@const head = w.kanji_form || w.reading}
							<a class="kanji-word-row" href="/?q={encodeURIComponent(head)}" title={t('searchWord', { word: head })}>
								<span class="kanji-word-head" lang="ja"><Ruby parts={w.ruby} tips={false} /></span>
								<span class="kanji-word-gloss">{w.gloss}</span>
							</a>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
{:else if missing}
	<div class="notice"><Icon name="info" size={16} /> {t('noKanjiEntry', { char })}</div>
{:else if loadError}
	<div class="error-banner"><Icon name="warning" size={16} /> {loadError}</div>
{:else}
	<div class="kanji-card">
		<div class="kanji-card-left"><p class="kanji-big">{char}</p></div>
		<div class="kanji-card-right kanji-loading"><span class="spinner"></span></div>
	</div>
{/if}
