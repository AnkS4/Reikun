<script lang="ts">
	import { onMount } from 'svelte';
	import { backend } from '#lib/backend.svelte.ts';
	import { apiReadyShared } from '#lib/api.ts';
	import { theme } from '#lib/theme.svelte.ts';
	import { i18n, t, LOCALES, LOCALE_NAMES, LOCALE_TAGS } from '#lib/i18n.svelte.ts';
	import { BRAND_SHORT } from '#lib/brand.ts';
	import { brandSubtext, currentPack, emblemSrc } from '#lib/lang/pack.ts';
	import { page } from '$app/state';
	import { PUBLIC_API_BASE } from '$app/env/public';
	import KanjiText from './KanjiText.svelte';
	import Popover from './Popover.svelte';
	import Icon from './Icon.svelte';

	let { hero = false, tagline = '' }: { hero?: boolean; tagline?: string } = $props();
	const isHome = $derived(page.url.pathname === '/');
	// Fixed per origin (es.reikun.app vs everything else) — safe to read once.
	const pack = currentPack();

	// Context-aware: land on the equivalent page in the lite UI instead of
	// always the home page, so switching variants feels continuous.
	const LITE_URL = $derived.by(() => {
		// Lite is served by the API at its own /lite path. An absolute API base
		// (local dev: http://localhost:8000) is a different origin, so prefix it.
		// A relative base (production: /api via the Worker proxy) means lite is
		// same-origin at /lite, not /api/lite.
		const api = (PUBLIC_API_BASE || '').replace(/\/+$/, '');
		const base = /^https?:\/\//.test(api) ? api : '';
		let path = '/';
		let search = '';
		let q = '';
		let lwLang = '';
		let lwPage = 0;
		try {
			path = page.url.pathname;
			search = page.url.search;
			const sp = page.url.searchParams;
			q = sp.get('q') ?? '';
			lwLang = sp.get('lang') ?? '';
			lwPage = Number(sp.get('page') ?? 0);
		} catch {
			// prerendering — url.search/searchParams unavailable
		}
		if (path === '/') {
			if (q) return `${base}/lite/search?q=${encodeURIComponent(q)}`;
			return `${base}/lite`;
		}
		if (path === '/about') return `${base}/lite/about`;
		if (path === '/privacy') return `${base}/lite/privacy`;
		if (path === '/kana') {
			const variant = page.url.searchParams.get('variant') === 'katakana' ? '?variant=katakana' : '';
			return `${base}/lite/kana${variant}`;
		}
		if (path.startsWith('/kanji/')) return `${base}/lite${path}${search}`;
		if (path === '/kanji-group') {
			// SPA pages by ?page= (48/page); lite pages by ?n=&offset= (items).
			const kgPage = Number(page.url.searchParams.get('page') ?? 0);
			const params = new URLSearchParams();
			const by = page.url.searchParams.get('by');
			const value = page.url.searchParams.get('value');
			if (by) params.set('by', by);
			if (value) params.set('value', value);
			params.set('n', '48');
			if (Number.isInteger(kgPage) && kgPage > 0) params.set('offset', String(kgPage * 48));
			return `${base}/lite/kanji/group?${params}`;
		}
		if (path === '/conjugations') return `${base}/lite/conjugations${search}`;
		if (path === '/loanwords') {
			if (!lwLang) return `${base}/lite/loanwords`;
			// SPA pages by ?page= (50/page); lite pages by ?offset= (item count).
			const off = Number.isInteger(lwPage) && lwPage > 0 ? `?offset=${lwPage * 50}` : '';
			return `${base}/lite/loanwords/${encodeURIComponent(lwLang)}${off}`;
		}
		return `${base}/lite`;
	});

	// The sister-edition switch: the same round icon-button grammar as the
	// lite switch, but wearing the other edition's sun — the gold Spanish
	// mark on the Japanese site, the red Japanese mark on the Spanish one
	// (the `languages` glyph is already the UI-language popover trigger).
	// Plain-English titles (es-page chrome rule: no new shared i18n keys).
	const SISTER_URL = pack === 'es' ? 'https://reikun.app' : 'https://es.reikun.app';
	const SISTER_TITLE = pack === 'es' ? 'Try the Japanese dictionary' : 'Try the Spanish dictionary';
	const SISTER_EMBLEM = pack === 'es' ? '/icons/emblem.svg' : '/icons/emblem-es.svg';

	// Readiness lives in shared reactive state (backend.ready — written by the
	// /ready request in api.ts, retries included), so the dot and entry count
	// recover when a retry succeeds: subscribing to the promise here would go
	// deaf after the first rejection. The mount ping still fires the first
	// attempt (sharing the layout's in-flight one) and retries a failed one on
	// navigation; against a cached success it's a no-op.
	onMount(() => apiReadyShared().catch(() => {}));
	const status = $derived(backend.ready);

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
	<!-- Sister-edition switch: the other edition's sun crosses between the
	     Japanese and Spanish hosts (each pack decides the target). -->
	<a class="btn tertiary header-es" href={SISTER_URL} title={SISTER_TITLE} aria-label={SISTER_TITLE} rel="noopener">
		<img class="sister-emblem" src={SISTER_EMBLEM} alt="" aria-hidden="true" />
	</a>
	{#if pack === 'ja'}
		<!-- Variant switch, drawn like the popover triggers: a plain 2rem round
		     icon button — a lightning bolt for the quick, lightweight variant,
		     matched in height and form with the status dot / appearance / language
		     controls. -->
		<a class="btn tertiary header-lite" href={LITE_URL} title={t('liteSwitch')} aria-label={t('liteSwitch')} rel="noopener">
			<Icon name="zap" size={18} />
		</a>
	{/if}
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
		<Icon name="database" size={18} />
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
	<Popover icon="palette" title={t('theme')}>
		<p class="popover-title">{t('theme')}</p>
		<div class="opt-list" role="listbox" aria-label={t('theme')}>
			{#each THEME_OPTIONS as option (option.v)}
				<button
					type="button"
					role="option"
					aria-selected={theme.choice === option.v}
					class:sel={theme.choice === option.v}
					onclick={() => theme.set(option.v)}
				>
					<span class="opt-check" aria-hidden="true"
						>{#if theme.choice === option.v}<Icon name="check" size={16} />{/if}</span
					>
					<span>{t(option.key)}</span>
				</button>
			{/each}
		</div>
		<!-- Furigana moved to the search row's あ button — the popover keeping a
		     second toggle in sync was two controls for one preference. -->
	</Popover>
	<Popover icon="languages" title={t('languageTitle')}>
		<p class="popover-title">{t('language')}</p>
		<div class="opt-list opt-langs" role="listbox" aria-label={t('languageTitle')}>
			{#each LOCALES as code (code)}
				<button
					type="button"
					role="option"
					aria-selected={i18n.locale === code}
					class:sel={i18n.locale === code}
					onclick={() => i18n.set(code)}
				>
					<span class="opt-check" aria-hidden="true"
						>{#if i18n.locale === code}<Icon name="check" size={16} />{/if}</span
					>
					<span lang={code}>{LOCALE_NAMES[code]}</span>
				</button>
			{/each}
		</div>
	</Popover>
</div>

<div class="header-bar" class:compact={!hero}>
	<div class="header-title" class:hero>
		{#if hero}
			<div class="hero-badge-tag">
				<span>{brandSubtext()}</span>
			</div>
		{/if}
		<h1 class="title-heading" class:hero-heading={hero} class:compact-title={!hero}>
			<a class="title-home" href="/" title={isHome ? undefined : t('backToSearch')}>
				<img
					src={emblemSrc()}
					alt=""
					class="brand-icon"
					aria-hidden="true"
				/>
				<span class="brand-wordmark" lang="en">{BRAND_SHORT}</span>
				{#if pack === 'es'}
					<!-- The Spanish edition is search-first and still growing — say
					     so quietly, right on the wordmark (the standard alpha spot). -->
					<span class="alpha-tag" title="Initial release — the dictionary is still growing">ALPHA</span>
				{/if}
			</a>
			{#if hero && currentPack() === 'ja'}
				<!-- 例訓 clarifies the name on the Japanese edition only — it would
				     be nonsense on the Spanish edition's header. -->
				<span class="brand-kanji" lang="ja">(<KanjiText text="例訓" />)</span>
			{/if}
		</h1>
		{#if hero && tagline}<p class="tagline">{tagline}</p>{/if}
	</div>
</div>
