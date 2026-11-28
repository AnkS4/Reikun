<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { esSearch, type SearchResponse } from '#lib/api.ts';
	import { shapeEsResponse, type EsResult } from '#lib/lang/es.ts';
	import Header from '#lib/components/Header.svelte';
	import EsCard from '#lib/components/EsCard.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { formatNumber, t } from '#lib/i18n.svelte.ts';
	import { BRAND_SHORT } from '#lib/brand.ts';
	import { currentPack } from '#lib/lang/pack.ts';
	import { pushRecent } from '#lib/recent.ts';

	// Retrieval is ~25 ms — a page of ten costs the same as five; "Show more" refetches.
	const DEFAULT_RESULTS = 10;
	const PAGE_RESULTS = 10;
	const MAX_RESULTS = 50;

	// Four pinned searches: a Spanish verb, an English verb (no "to"), and
	// one phrase in each language. Short enough to read at a glance.
	const EXAMPLES = [
		['hablar', 'es'],
		['meander', 'en'],
		['sobremesa', 'es'],
		['raining cats and dogs', 'en']
	];

	// Hero tagline + meta description — es-page specific chrome (the shared
	// t('tagline') describes the Japanese dictionary); plain English until es
	// keys exist in shared i18n.
	const TAGLINE =
		'Search Spanish words — English meanings, native Spanish definitions and full conjugation tables.';

	// Reassigned whole, never mutated.
	let resp = $state.raw<SearchResponse | null>(null);
	let searching = $state(false);
	let error = $state('');
	let committed = $state('');
	let wantResults = $state(DEFAULT_RESULTS);
	let qInput = $state('');
	let searchInput = $state<HTMLInputElement>();

	// Shape once per response — the lang/es seam owns the payload knowledge.
	let results = $derived<EsResult[]>(resp ? shapeEsResponse(resp) : []);
	const hasResults = $derived(resp !== null);

	// URL → search: ?q= drives everything (deep links, back/forward, pills).
	// Same pattern as the main search page (routes/+page.svelte) minus the
	// ja-specific extras (xref deep links, segmentation, kanji).
	let handledUrl = '';
	let reqSeq = 0;
	$effect(() => {
		const q = (page.url.searchParams.get('q') ?? '').trim();
		const changedQuery = q !== committed;
		if (changedQuery) {
			wantResults = DEFAULT_RESULTS; // reset before urlKey below
			// Dropping the visible results abandons whatever search produced
			// them: bump the sequence so its late response can't land over the
			// cleared state (Back from a slow ?q= must not resurrect results).
			++reqSeq;
			searching = false;
			resp = null;
		}
		const urlKey = `${q}|${wantResults}`;
		if (urlKey === handledUrl) return;
		handledUrl = urlKey;
		qInput = q;
		committed = q;
		if (!q) {
			resp = null;
			error = '';
			return;
		}
		if (changedQuery) pushRecent(q);
		runSearch(q);
	});

	// Stale-response guard: a superseded search can't overwrite newer results.
	// Timeouts, retries and the wake banner live in the API layer (api.ts).
	async function runSearch(q: string) {
		const seq = ++reqSeq;
		searching = true;
		error = '';
		try {
			const r = await esSearch(q, wantResults);
			if (seq === reqSeq) resp = r;
		} catch (e) {
			if (seq === reqSeq) {
				resp = null;
				error = e instanceof Error ? e.message : t('searchFailed');
			}
		} finally {
			if (seq === reqSeq) searching = false;
		}
	}

	function setQuery(v: string) {
		const u = new URL(page.url.href);
		if (v) u.searchParams.set('q', v);
		else u.searchParams.delete('q');
		goto(u, { reset: false });
	}

	function commit(v: string) {
		// Touch drops the caret so the keyboard collapses off the results;
		// desktop keeps it — pills chain searches.
		if (matchMedia('(pointer: coarse)').matches) searchInput?.blur();
		else searchInput?.focus({ preventScroll: true });
		// Same query again (re-submit) → search directly; a changed query goes
		// through ?q= so history records it.
		if (v === committed) {
			if (v) {
				pushRecent(v);
				runSearch(v);
			}
		} else setQuery(v);
	}

	function submit(e: SubmitEvent) {
		e.preventDefault();
		commit(qInput.trim());
	}

	function showNext() {
		// wantResults is part of urlKey — the effect refires with the larger n.
		wantResults = Math.min(wantResults + PAGE_RESULTS, MAX_RESULTS);
	}

	// One always-mounted live region: screen readers hear search progress and
	// the outcome without having to find the visual stats line.
	const announce = $derived(
		searching
			? t('searching')
			: error
				? error
				: resp
					? resp.results.length === 1
						? t('resultsForOne', { query: committed })
						: t('resultsForMany', { count: formatNumber(resp.results.length), query: committed })
					: ''
	);
</script>

<svelte:head>
	<title>{committed ? `${committed} — ${BRAND_SHORT}` : `${BRAND_SHORT} — Español`}</title>
	<meta name="description" content={TAGLINE} />
	{#if currentPack() === 'es'}
		<!-- The es edition's own origin: the share metadata points here (the
		     site-wide statics in app.html describe the Japanese original). -->
		<meta property="og:title" content="Reikun — The open Spanish dictionary" />
		<meta property="og:description" content={TAGLINE} />
		<meta property="og:url" content="https://es.reikun.app/" />
		<meta property="og:image" content="https://es.reikun.app/images/og-image-es.png" />
	{/if}
</svelte:head>

<Header home={!committed} hero={!hasResults && !searching} tagline={TAGLINE} />

<form class="search-row" role="search" onsubmit={submit}>
	<div class="search-pair">
		<input
			type="search"
			id="search"
			placeholder={hasResults ? t('searchPlaceholder') : ''}
			aria-label={t('search')}
			bind:value={qInput}
			bind:this={searchInput}
			autocomplete="off"
			autocapitalize="none"
			spellcheck="false"
		/>
		<button
			type="button"
			class="search-clear"
			class:visible={!!qInput}
			aria-label={t('clear')}
			title={t('clear')}
			tabindex={qInput ? 0 : -1}
			onclick={() => {
				qInput = '';
				searchInput?.focus();
			}}
		>
			<Icon name="close" size={20} />
		</button>
		<button type="submit" class="search-submit" aria-label={t('search')} title={t('search')}>
			<Icon name="search" size={20} />
		</button>
	</div>
</form>

<div class="sr-only" role="status" aria-live="polite">{announce}</div>

{#if searching && !resp}
	<div class="kgroup-loading"><span class="spinner"></span></div>
{/if}
{#if error}
	<div class="error-banner" role="alert"><Icon name="warning" size={20} /> {error}</div>
{/if}

{#if resp}
	<div class="stats-line">
		<span class="stats-count"
			>{resp.results.length === 1 ? t('entryOne') : t('entryMany', { count: formatNumber(resp.results.length) })}</span
		>
		<span class="stats-details"><span class="stats-label">{t('total')}</span>{formatNumber(resp.latency_ms)} ms</span>
	</div>

	{#if !resp.results.length}
		<!-- es-page wording — plain English; the shared t('nothingFound') names
		     the Japanese dictionary's languages. -->
		<div class="warning">
			<Icon name="warning" size={20} /> Nothing found. Try a different Spanish or English word.
		</div>
	{/if}

	{#each results as r, i (i)}
		<EsCard result={r} style={`animation-delay: ${Math.min(i, 8) * 40}ms`} />
	{/each}

	{#if resp.results.length >= wantResults && wantResults < MAX_RESULTS}
		<button
			type="button"
			class="btn-3d"
			onclick={showNext}
			title={t('showMoreTitle', { max: formatNumber(MAX_RESULTS) })}
		>
			<Icon name="expand-more" size={16} /> {t('showNext', { count: formatNumber(PAGE_RESULTS) })}
		</button>
	{/if}
{:else if !searching && !error}
	<div class="pills" aria-label={t('exampleSearches')}>
		{#each EXAMPLES as [ex, lang] (ex)}
			<button type="button" class="pill" onclick={() => commit(ex)}>
				<Icon name="search" size={16} />
				<span {lang}>{ex}</span>
			</button>
		{/each}
	</div>
	<div class="browse" aria-label={t('browse')}>
		<p class="popover-title">{t('browse')}</p>
		<div class="browse-grid two-up">
			<a class="browse-tile" href="/etymology">
				<span class="browse-icon"><Icon name="blend" size={22} /></span>
				<span class="browse-name">Etymology</span>
				<span class="browse-desc">Browse Spanish words by source language</span>
			</a>
			<a class="browse-tile" href="/families">
				<span class="browse-icon"><Icon name="school" size={22} /></span>
				<span class="browse-name">Word families</span>
				<span class="browse-desc">Words that share an etymological root</span>
			</a>
		</div>
	</div>
{/if}
