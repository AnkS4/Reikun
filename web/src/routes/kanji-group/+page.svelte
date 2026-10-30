<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiKanjiGroup, type GroupKey, type KanjiGroupResponse } from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { t } from '#lib/i18n.svelte.ts';

	// One page of the grid; eight columns of six rows on desktop, and the
	// API cap keeps a foulest-offset request from doing more work than this.
	const PAGE_SIZE = 48;

	const fromWord = $derived(page.url.searchParams.get('from') ?? '');

	// Validated request descriptor — anything unrecognized renders the
	// bad-request notice instead of a fetch.
	let req = $derived.by((): { by: GroupKey; value: number; skip: number } | null => {
		const params = page.url.searchParams;
		const raw = params.get('by');
		const value = Number(params.get('value'));
		const by: GroupKey | null =
			raw === 'strokes' || raw === 'grade' || raw === 'jlpt' ? raw : null;
		if (!by) return null;
		return { by, value, skip: Math.max(0, Math.round(Number(params.get('page') ?? 0))) * PAGE_SIZE };
	});

	let data = $state.raw<KanjiGroupResponse | null>(null);
	let busy = $state(false);
	let error = $state('');

	$effect(() => {
		const r = req;
		data = null;
		error = '';
		if (!r) return;
		busy = true;
		apiKanjiGroup(r.by, r.value, PAGE_SIZE, r.skip)
			.then((d) => (data = d))
			.catch((e) => (error = e instanceof Error ? e.message : t('groupLoadFailed')))
			.finally(() => (busy = false));
	});

	const pageNo = $derived(req ? Math.floor(req.skip / PAGE_SIZE) + 1 : 0);
	const pages = $derived(data ? Math.ceil(data.total / PAGE_SIZE) : 0);

	// Pagination navigates via ?page= so every page is a real entry in the
	// session history (an explicit URL the back button undoes).
	function pageHref(p: number): string {
		const fromParam = fromWord ? `&from=${encodeURIComponent(fromWord)}` : '';
		return `/kanji-group?by=${req?.by}&value=${req?.value}&page=${p}${fromParam}`;
	}

	function goBack() {
		if (typeof window !== 'undefined' && window.history.length > 1) {
			window.history.back();
		} else if (fromWord) {
			goto(`/?q=${encodeURIComponent(fromWord)}`);
		} else {
			goto('/');
		}
	}

	function groupLabel(by: GroupKey): string {
		return t(by === 'jlpt' ? 'jlpt' : by);
	}

	function metaLine(k: KanjiGroupResponse['kanjis'][number]): string {
		return [
			k.stroke_count ? t('strokesCount', { n: k.stroke_count }) : '',
			k.jlpt_level ? { 4: 'N5', 3: 'N4', 2: 'N2-N3', 1: 'N1' }[k.jlpt_level] : '',
			k.freq ? t('freq', { n: k.freq }) : ''
		]
			.filter(Boolean)
			.join(' · ');
	}
</script>

<svelte:head>
	<title>{data ? `${data.label} ${t('kanjiSuffix')} — Reikun` : 'Reikun'}</title>
</svelte:head>

<Header />
<div class="kgroup-wrap">
	<nav class="group-nav-bar">
		<button type="button" class="group-back-btn" onclick={goBack} title={fromWord ? t('backTo', { word: fromWord }) : t('goBack')}>
			← {#if fromWord}{t('backTo', { word: fromWord })}{:else}{t('backToSearch')}{/if}
		</button>
		<a href="/" class="group-home-link">{t('reikunHome')}</a>
	</nav>
	{#if !req}
		<p class="notice"><Icon name="info" size={16} /> {t('unknownGroup')}</p>
	{:else}
		<h1 class="kgroup-title">
			{data?.label ?? groupLabel(req.by)} {t('kanjiSuffix')}
			{#if data}<span class="kgroup-total">{data.total}</span>{/if}
		</h1>
		<p class="kgroup-sub">
			{t('groupSubtitle', { group: groupLabel(req.by) })}
		</p>

		{#if busy}
			<div class="kgroup-loading"><span class="spinner"></span></div>
		{:else if error}
			<p class="error-banner"><Icon name="warning" size={16} /> {error}</p>
		{:else if data}
			<div class="kg-grid">
				{#each data.kanjis as k (k.literal)}
					<a class="kg-card" href="/?q={encodeURIComponent(k.literal)}" title={t('openKanji', { char: k.literal })}>
						<span class="kg-glyph" lang="ja">{k.literal}</span>
						<span class="kg-gloss">{k.meanings[0] ?? '—'}</span>
						<span class="kg-meta">{metaLine(k)}</span>
					</a>
				{/each}
			</div>
			{#if pages > 1}
				<nav class="kg-pager" aria-label={t('groupPages')}>
					{#if pageNo > 1}<a class="btn-3d" href={pageHref(pageNo - 2)}>{t('previous')}</a>{/if}
					<span class="kg-pager-label">{t('pageOf', { page: pageNo, pages })}</span>
					{#if pageNo < pages}<a class="btn-3d" href={pageHref(pageNo)}>{t('next')}</a>{/if}
				</nav>
			{/if}

			<div class="kgroup-bottom-actions">
				<button type="button" class="btn-3d" onclick={goBack}>
					← {#if fromWord}{t('backTo', { word: fromWord })}{:else}{t('backPrevious')}{/if}
				</button>
			</div>
		{/if}
	{/if}
</div>
