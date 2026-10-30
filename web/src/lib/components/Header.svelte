<script lang="ts">
	import { onMount } from 'svelte';
	import { apiReadyShared } from '#lib/api.ts';
	import { theme } from '#lib/theme.svelte.ts';
	import { i18n, t, LOCALES, LOCALE_NAMES, LOCALE_TAGS } from '#lib/i18n.svelte.ts';
	import { BRAND_SUBTEXT } from '#lib/brand.ts';
	import KanjiText from './KanjiText.svelte';
	import Popover from './Popover.svelte';
	import Icon from './Icon.svelte';

	let { hero = false, tagline = '' }: { hero?: boolean; tagline?: string } = $props();

	// Only reassigned as a whole — raw state avoids proxying the response object.
	let status = $state.raw<{ ok: boolean; entries: number | null; error?: string } | null>(null);
	onMount(() => {
		apiReadyShared()
			.then((r) => (status = { ok: true, entries: r.entries }))
			.catch((e) =>
				(status = {
					ok: false,
					entries: null,
					error: e instanceof Error ? e.message : t('apiUnreachable')
				})
			);
	});

	const THEME_OPTIONS = [
		{ v: 'system' as const, key: 'themeSystem' as const },
		{ v: 'light' as const, key: 'themeLight' as const },
		{ v: 'dark' as const, key: 'themeDark' as const },
		{ v: 'oled' as const, key: 'themeOled' as const }
	];

	function count(n: number | null | undefined): string {
		return n?.toLocaleString(LOCALE_TAGS[i18n.locale]) ?? '—';
	}
</script>

<div class="header-controls">
	<!-- svelte-ignore a11y_no_noninteractive_tabindex — focusable so keyboard users can open the status tooltip -->
	<span
		class="status-dot"
		class:ok={status?.ok}
		class:err={status && !status.ok}
		role="img"
		tabindex="0"
		aria-label={status === null
			? t('statusAriaConnecting')
			: status.ok
				? t('statusAriaReady', { count: count(status.entries) })
				: t('statusAriaOffline', { msg: status.error ?? '' })}
	>
		<Icon name="database" size={15} />
		<span class="status-pop" role="tooltip">
			<span class="popover-title">{t('statusTitle')}</span>
			{#if status === null}
				<span class="status-line"><span class="status-mark"></span>{t('statusConnecting')}</span>
				<span class="status-sub">{t('statusWaking')}</span>
			{:else if status.ok}
				<span class="status-line"><span class="status-mark ok"></span>{t('statusConnected')}</span>
				<span class="status-sub">{t('statusReadyWords', { count: count(status.entries) })}</span>
			{:else}
				<span class="status-line"><span class="status-mark err"></span>{t('statusOffline')}</span>
				<span class="status-sub">{t('statusReachError', { msg: status.error ?? '' })}</span>
			{/if}
		</span>
	</span>
	<Popover icon="palette" title={t('appearanceTitle')}>
		<p class="popover-title">{t('appearance')}</p>
		<div class="segmented" role="group" aria-label={t('theme')}>
			{#each THEME_OPTIONS as option (option.v)}
				<button
					type="button"
					class:sel={theme.choice === option.v}
					aria-pressed={theme.choice === option.v}
					onclick={() => theme.set(option.v)}>{t(option.key)}</button
				>
			{/each}
		</div>
		<!-- Furigana moved to the search row's あ button — the popover keeping a
		     second toggle in sync was two controls for one preference. -->
	</Popover>
	<Popover icon="languages" title={t('languageTitle')}>
		<p class="popover-title">{t('language')}</p>
		<div class="segmented lang-segmented" role="group" aria-label={t('languageTitle')}>
			{#each LOCALES as code (code)}
				<button
					type="button"
					class:sel={i18n.locale === code}
					aria-pressed={i18n.locale === code}
					onclick={() => i18n.set(code)}>{LOCALE_NAMES[code]}</button
				>
			{/each}
		</div>
	</Popover>
</div>

<div class="header-bar" class:compact={!hero}>
	<div class="header-title" class:hero>
		{#if hero}
			<div class="hero-badge-tag">
				<Icon name="book-open" size={13} />
				<span>{BRAND_SUBTEXT}</span>
			</div>
		{/if}
		<h1 class="title-heading" class:hero-heading={hero} class:compact-title={!hero}>
			<a class="title-home" href="/" title={t('backToSearch')}>
				<img
					src="/icons/emblem.svg"
					alt=""
					class="brand-icon"
					aria-hidden="true"
				/>
				<span>Reikun</span>
			</a>
			<span class="brand-kanji" lang="ja">(<KanjiText text="例訓" />)</span>
		</h1>
		{#if hero && tagline}<p class="tagline">{tagline}</p>{/if}
	</div>
</div>
