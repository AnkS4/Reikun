<script lang="ts">
	import { ApiError, apiKanjiCard, type KanjiCard as Card } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import StrokeSvg from './StrokeSvg.svelte';
	import Icon from './Icon.svelte';
	let { char }: { char: string } = $props();

	let card = $state<Card | null>(null);
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
				else loadError = e instanceof Error ? e.message : 'Failed to load kanji details';
			});
	});

	// ui/common.py _READING_TYPES — label, furigana, hover explanation
	const READING_TYPES = [
		{
			key: 'on' as const,
			text: '音読み',
			reading: 'おんよみ',
			tip: "On'yomi — the Sino-Japanese reading, borrowed with the character from Chinese. Used mostly in multi-kanji compounds (電話, 学校)."
		},
		{
			key: 'kun' as const,
			text: '訓読み',
			reading: 'くんよみ',
			tip: "Kun'yomi — the native Japanese reading attached to the character's meaning. Used for standalone words and with okurigana (食べる, 山)."
		}
	];
</script>

{#if card}
	<div class="kanji-card">
		<div class="kanji-card-left">
			<p class="kanji-big">{char}</p>
			{#if card.stroke}
				<StrokeSvg stroke={card.stroke} />
			{/if}
			{#if card.meta.length}
				<div class="meta-badges">
					{#each card.meta as m}
						<span class="meta-badge" title={m.tip}>{m.label}</span>
					{/each}
				</div>
			{/if}
		</div>
		<div class="kanji-card-right">
			<div class="kanji-section">
				<p class="kanji-section-title">Meanings</p>
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

			{#each READING_TYPES as rt}
				{@const chips = card.readings[rt.key] ?? []}
				{#if chips.length}
					<div class="kanji-section">
						<div class="reading-row">
							<!-- svelte-ignore a11y_no_noninteractive_tabindex — focusable tooltip label -->
							<span class="rlabel kanji-tip" tabindex="0"
								><ruby>{rt.text}<rt>{rt.reading}</rt></ruby><span class="kanji-tip-body"
									>{rt.tip}</span
								></span
							>
							<span class="reading-list">
								{#each chips as chip}
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
					<p class="kanji-section-title">Common words</p>
					<div class="common-words">
						{#each card.common_words as w}
							{@const head = w.kanji_form || w.reading}
							<a class="kanji-word-row" href="/?q={encodeURIComponent(head)}" title="Search {head}">
								<span class="kanji-word-head"><Ruby parts={w.ruby} tips={false} /></span>
								<span class="kanji-word-gloss">{w.gloss}</span>
							</a>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</div>
{:else if missing}
	<div class="notice"><Icon name="info" size={16} /> No KANJIDIC2 entry for “{char}”.</div>
{:else if loadError}
	<div class="error-banner"><Icon name="warning" size={16} /> {loadError}</div>
{:else}
	<div class="kanji-card">
		<div class="kanji-card-left"><p class="kanji-big">{char}</p></div>
		<div class="kanji-card-right kanji-loading"><span class="spinner"></span></div>
	</div>
{/if}
