<script lang="ts">
	import { page } from '$app/state';
	import Header from '#lib/components/Header.svelte';
	import { HIRAGANA, KATAKANA, type KanaChart } from '#lib/kana.ts';
	import { t } from '#lib/i18n.svelte.ts';

	const variant = $derived.by((): 'hiragana' | 'katakana' =>
		(typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('variant') : 'hiragana') === 'katakana'
			? 'katakana'
			: 'hiragana');
	const chart = $derived(variant === 'katakana' ? KATAKANA : HIRAGANA);

	// Columns: a · i · u · e · o (kana reading order) — rows: Basic, Dakuten, Handakuten.
	const SECTIONS = $derived([
		{ key: 'kanaBasic', rows: chart.bss },
		{ key: 'kanaDakuten', rows: chart.dakuten },
		{ key: 'kanaHandakuten', rows: chart.handakuten }
	] as const);
</script>

<svelte:head>
	<title>{t('kanaTitle')} — Reikun</title>
	<meta name="description" content={t('kanaSub')} />
</svelte:head>

<Header />
<div class="kgroup-wrap kana-page">
	<h1 class="kgroup-title">{t('kanaTitle')}</h1>
	<p class="kgroup-sub">{t('kanaSub')}</p>

	<nav class="kana-tabs" aria-label={t('kanaScript')}>
		<a class="kana-tab" class:sel={variant === 'hiragana'} aria-current={variant === 'hiragana' ? 'page' : undefined} href="/kana?variant=hiragana">{t('kanaHiragana')}</a>
		<a class="kana-tab" class:sel={variant === 'katakana'} aria-current={variant === 'katakana' ? 'page' : undefined} href="/kana?variant=katakana">{t('kanaKatakana')}</a>
	</nav>

	{#each SECTIONS as section (section.key)}
		<div class="kana-section">
			<p class="kanji-section-title">{t(section.key)}</p>
			<div class="kana-grid">
				{#each section.rows as row, r (r)}
					{#each row as cell, c (c)}
						{#if cell}
							<div class="kg-card kana-cell">
								<span class="kg-glyph" lang="ja">{cell.kana}</span>
								<span class="kg-meta">{cell.romaji}</span>
							</div>
						{:else}
							<div class="kana-cell-empty" aria-hidden="true"></div>
						{/if}
					{/each}
				{/each}
			</div>
		</div>
	{/each}

	<div class="kgroup-bottom-actions">
		<a class="btn-3d" href="/">← {t('backToSearch')}</a>
	</div>
</div>
