<script lang="ts">
	import { page } from '$app/state';
	import {
		ApiError, esEtymologyEntries, esEtymologyFacets,
		type LoanwordsPageResponse, type LoanwordsResponse
	} from '#lib/api.ts';
	import EsCard from '#lib/components/EsCard.svelte';
	import Header from '#lib/components/Header.svelte';
	import { formatNumber, t } from '#lib/i18n.svelte.ts';
	import { shapeEs } from '#lib/lang/es.ts';

	const PAGE_SIZE = 20;
	const lang = $derived(page.url.searchParams.get('lang') ?? '');
	const pageNo = $derived.by(() => {
		const index = Number(page.url.searchParams.get('page') ?? 0);
		return Number.isSafeInteger(index) && index >= 0 && index <= 10_000 ? index : 0;
	});

	let data = $state.raw<LoanwordsResponse | LoanwordsPageResponse | null>(null);
	let error = $state('');
	$effect(() => {
		const load = lang ? esEtymologyEntries(lang, PAGE_SIZE, pageNo * PAGE_SIZE) : esEtymologyFacets();
		let stale = false;
		data = null;
		error = '';
		load.then(
			(value) => { if (!stale) data = value; },
			(cause: unknown) => {
				if (stale) return;
				error = cause instanceof ApiError && cause.status === 404
					? 'No entries are tagged with this source language.'
					: cause instanceof Error ? cause.message : t('searchFailed');
			}
		);
		return () => { stale = true; };
	});

	const listing = $derived(data && 'results' in data ? data : null);
	const facets = $derived(data && 'sources' in data ? data.sources : []);
	const results = $derived(listing?.results.map(shapeEs) ?? []);
	const pages = $derived(listing ? Math.ceil(listing.total / PAGE_SIZE) : 0);

	function browseHref(source: string, index = 0): string {
		const params = new URLSearchParams({ lang: source });
		if (index) params.set('page', String(index));
		return `/etymology?${params}`;
	}
</script>

<svelte:head>
	<title>{listing ? `${listing.name} — ` : ''}Etymology — Reikun</title>
	<meta name="description" content="Browse Spanish words by source language, using Spanish Wiktionary etymology categories." />
</svelte:head>

<Header />
<div class="kgroup-wrap">
	<h1 class="kgroup-title">
		{#if listing}<span lang="es">{listing.name}</span>{:else}Etymology{/if}
		{#if listing}<span class="kgroup-total">{formatNumber(listing.total)}</span>{/if}
	</h1>
	<p class="kgroup-sub">Source-language categories from <a href="https://es.wiktionary.org/">Spanish Wiktionary</a>.</p>

	{#if error}
		<p class="error-banner" role="alert">{error}</p>
	{:else if !data}
		<div class="kgroup-loading" role="status" aria-label={t('searching')}><span class="spinner"></span></div>
	{:else if listing}
		{#if !results.length}<p>No entries on this page.</p>{/if}
		{#each results as result}
			<EsCard {result} />
		{/each}
		{#if pages > 1}
			<nav class="kg-pager" aria-label={t('groupPages')}>
				{#if pageNo > 0}<a class="btn-3d" href={browseHref(lang, Math.min(pageNo - 1, pages - 1))}>{t('previous')}</a>{/if}
				{#if pageNo < pages}
					<span class="kg-pager-label">{t('pageOf', { page: formatNumber(pageNo + 1), pages: formatNumber(pages) })}</span>
				{/if}
				{#if pageNo + 1 < pages}<a class="btn-3d" href={browseHref(lang, pageNo + 1)}>{t('next')}</a>{/if}
			</nav>
		{/if}
	{:else if facets.length}
		<div class="kg-grid">
			{#each facets as source (source.lang)}
				<a class="kg-card" href={browseHref(source.lang)}>
					<span class="kv-value" lang="es">{source.name}</span>
					<span class="kg-meta">{formatNumber(source.count)} entries</span>
				</a>
			{/each}
		</div>
	{:else}
		<p>No etymology categories available yet.</p>
	{/if}
	{#if lang}
		<div class="kgroup-bottom-actions"><a class="btn-3d" href="/etymology">← {t('loanwordsAll')}</a></div>
	{/if}
</div>
