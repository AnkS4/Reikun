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
		// `level` is display-only (ResultCard badges) but must survive
		// pagination so page 2 doesn't silently reset to N5.
		const lvl = page.url.searchParams.get('level');
		const lvlParam = lvl ? `&level=${encodeURIComponent(lvl)}` : '';
		return `/loanwords?lang=${encodeURIComponent(lang)}&page=${p}${lvlParam}`;
	}

	function searchWord(q: string, ref?: { seq?: string; sno?: string | null }) {
		// Xref chips carry the target entry seq + sense — the search page's
		// ?seq=&sense= deep link scrolls to that sense block.
		const u = new URLSearchParams({ q });
		if (ref?.seq) {
			u.set('seq', ref.seq);
			if (ref.sno) u.set('sense', ref.sno);
		}
		goto(`/?${u}`);
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
		<div class="kgroup-bottom-actions"><a class="btn-3d" href="/loanwords">← {t('loanwordsAll')}</a></div>
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
		<div class="kgroup-bottom-actions"><a class="btn-3d" href="/loanwords">← {t('loanwordsAll')}</a></div>
	{:else if facets}
		<!-- Same card grid the kanji-group value pickers use: facet label in
		     the glyph slot, count + unit in the mono meta line. -->
		<div class="kg-grid">
			{#each facets.sources as src (src.lang)}
				<a class="kg-card" href="/loanwords?lang={encodeURIComponent(src.lang)}">
					<span class="kv-value">{src.name}</span>
					<span class="kg-meta">{src.count.toLocaleString()} {t('wordsSuffix')}</span>
				</a>
			{/each}
		</div>
	{/if}
</div>
