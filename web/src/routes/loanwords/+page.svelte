<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		apiLoanwords,
		apiLoanwordsLang,
		ApiError,
		LEVELS,
		type Level,
		type LoanwordsPageResponse,
		type LoanwordsResponse
	} from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import ResultCard from '#lib/components/ResultCard.svelte';
	import { t } from '#lib/i18n.svelte.ts';

	const PAGE_SIZE = 50;

	const lang = $derived(page.url.searchParams.get('lang') ?? '');
	const level = $derived.by((): Level => {
		const l = page.url.searchParams.get('level') ?? '';
		return (LEVELS as readonly string[]).includes(l) ? (l as Level) : 'N5';
	});
	const pageNo = $derived.by(() => {
		const p = Number(page.url.searchParams.get('page') ?? 0);
		return Number.isInteger(p) && p >= 0 ? p : 0;
	});

	let facets = $state.raw<LoanwordsResponse | null>(null);
	let listing = $state.raw<LoanwordsPageResponse | null>(null);
	let busy = $state(false);
	let error = $state('');
	let notFound = $state(false);

	$effect(() => {
		const l = lang;
		facets = null;
		listing = null;
		error = '';
		notFound = false;
		let dropped = false;
		busy = true;
		if (l) {
			apiLoanwordsLang(l, PAGE_SIZE, pageNo * PAGE_SIZE)
				.then((d) => {
					if (dropped) return;
					listing = d;
				})
				.catch((e) => {
					if (dropped) return;
					if (e instanceof ApiError && e.status === 404) notFound = true;
					else error = e instanceof Error ? e.message : t('searchFailed');
				})
				.finally(() => {
					if (!dropped) busy = false;
				});
		} else {
			apiLoanwords()
				.then((d) => {
					if (dropped) return;
					facets = d;
				})
				.catch((e) => {
					if (dropped) return;
					error = e instanceof Error ? e.message : t('searchFailed');
				})
				.finally(() => {
					if (!dropped) busy = false;
				});
		}
		return () => {
			dropped = true;
		};
	});

	const pages = $derived(listing ? Math.ceil(listing.total / PAGE_SIZE) : 0);

	function pageHref(p: number): string {
		return `/loanwords?lang=${encodeURIComponent(lang)}&page=${p}`;
	}

	function searchWord(q: string) {
		goto(`/?q=${encodeURIComponent(q)}`);
	}
</script>

<svelte:head>
	<title>{listing ? `${listing.name} — ${t('loanwordsTitle')} — Reikun` : `${t('loanwordsTitle')} — Reikun`}</title>
	<meta name="description" content={t('loanwordsTagline')} />
</svelte:head>

<Header />
<div class="kgroup-wrap">
	<h1 class="kgroup-title">
		{#if listing}{listing.name}{:else}{t('loanwordsTitle')}{/if}
		{#if listing}<span class="kgroup-total">{listing.total.toLocaleString()}</span>{/if}
	</h1>
	<p class="kgroup-sub">{t('loanwordsTagline')}</p>

	{#if busy}
		<div class="kgroup-loading"><span class="spinner"></span></div>
	{:else if error}
		<p class="error-banner"><Icon name="warning" size={16} /> {error}</p>
	{:else if notFound}
		<p class="notice"><Icon name="info" size={16} /> {t('loanwordsUnknownMsg')}</p>
	{:else if listing}
		<p class="kgroup-sub">{t('loanwordsFromTagline', { name: listing.name })}</p>
		{#each listing.results as r, i (`${r.id ?? r.text}-${i}`)}
			<ResultCard result={r} {level} onPickKanji={searchWord} onSearchWord={searchWord} style={`animation-delay: ${Math.min(i, 8) * 40}ms`} />
		{/each}
		{#if pages > 1}
			<nav class="kg-pager" aria-label={t('groupPages')}>
				{#if pageNo > 0}<a class="btn-3d" href={pageHref(pageNo - 1)}>{t('previous')}</a>{/if}
				<span class="kg-pager-label">{t('pageOf', { page: pageNo + 1, pages })}</span>
				{#if pageNo + 1 < pages}<a class="btn-3d" href={pageHref(pageNo + 1)}>{t('next')}</a>{/if}
			</nav>
		{/if}
		<p><a class="btn-3d" href="/loanwords">← {t('loanwordsAll')}</a></p>
	{:else if facets}
		<div class="lw-chips">
			{#each facets.sources as src (src.lang)}
				<a class="pill lw-chip" href="/loanwords?lang={encodeURIComponent(src.lang)}">
					<span>{src.name}</span>
					<span class="lw-count">{src.count.toLocaleString()}</span>
				</a>
			{/each}
		</div>
	{/if}
</div>
