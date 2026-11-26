<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiSearch, type SearchResult } from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { t } from '#lib/i18n.svelte.ts';

	// Conjugation data can arrive two ways:
	// 1. Via SvelteKit navigation state (instant, no extra fetch — from ResultCard link)
	// 2. Via ?word= query param fallback (direct link / refresh — re-searches the word)

	type ConjRow = { form: string; surface: string; kana?: string | null };

	let word = $derived(page.url.searchParams.get('word') ?? '');
	let reading = $derived(page.url.searchParams.get('reading') ?? '');

	function goBack() {
		if (typeof window !== 'undefined' && window.history.length > 1) {
			window.history.back();
		} else if (word) {
			goto(`/?q=${encodeURIComponent(word)}`);
		} else {
			goto('/');
		}
	}

	// Navigation state carries the rows when clicking from a ResultCard
	let stateRows = $derived.by((): ConjRow[] | null => {
		const s = page.state as { conjRows?: ConjRow[] } | undefined;
		return s?.conjRows ?? null;
	});

	// Fallback: fetch from API when landing directly (bookmark, shared link)
	let fetchedRows = $state.raw<ConjRow[] | null>(null);
	let busy = $state(false);
	let error = $state('');
	let fetchedHeadword = $state('');
	// False when the table came from the fallback match below — the requested
	// ?word= has no conjugation table of its own, so the page must not present
	// the matched entry's inflections under the requested form.
	let exactMatch = $state(true);

	$effect(() => {
		const w = word;
		fetchedRows = null;
		fetchedHeadword = '';
		exactMatch = true;
		error = '';
		if (!w || stateRows) {
			busy = false;
			return; // nav state already has data
		}
		// Stale-response guard: navigating to another word must not let the
		// slowest in-flight fetch overwrite the visible table with older data
		// (the cleanup flips `dropped` before the next run's response lands).
		let dropped = false;
		busy = true;
		apiSearch(w, 3)
			.then((resp) => {
				if (dropped) return;
				// Find the entry whose dictionary form matches the word param;
				// failing that, the first entry that ships a table at all
				// (inflections of the closest match, not of the requested word).
				const match = resp.results.find(
					(r: SearchResult) =>
						r.inflected_forms?.length &&
						(r.kanji_form === w || r.reading === w)
				) ?? resp.results.find((r: SearchResult) => r.inflected_forms?.length);
				if (match) {
					fetchedRows = match.inflected_forms;
					fetchedHeadword = match.kanji_form || match.reading || w;
					exactMatch = match.kanji_form === w || match.reading === w;
				} else {
					error = t('noConjData', { word: w });
				}
			})
			.catch((e) => {
				if (dropped) return;
				error = e instanceof Error ? e.message : t('conjLoadFailed');
			})
			.finally(() => {
				if (!dropped) busy = false;
			});
		return () => {
			dropped = true;
		};
	});

	const rows = $derived(stateRows ?? fetchedRows ?? []);
	// Exact matches (and the nav-state table, carried for the requested word)
	// head with the requested word, as before. A fallback match heads with the
	// entry that actually carries the table — the requested form has no
	// conjugations of its own to label these rows with.
	const heading = $derived(
		exactMatch || !fetchedRows ? word || t('conjugations') : fetchedHeadword
	);
	// The ?reading= param describes the requested form — meaningless next to a
	// different entry's headword, so it only shows while that entry is exact.
	const displayReading = $derived(
		reading && reading !== word && (exactMatch || !fetchedRows) ? reading : ''
	);
</script>

<svelte:head>
	<title>{t('conjPageTitle', { word: heading })} — Reikun</title>
</svelte:head>

<Header />
<div class="conj-page-wrap">
	<nav class="group-nav-bar">
		<button type="button" class="btn-3d" onclick={goBack} title={word ? t('backTo', { word }) : t('goBack')}>
			← {#if word}{t('backTo', { word })}{:else}{t('backToSearch')}{/if}
		</button>
	</nav>
	{#if !word}
		<p class="notice"><Icon name="info" size={18} /> {t('noWord')}</p>
	{:else}
		<h1 class="conj-page-title" lang="ja">
			{heading}
			{#if displayReading}<span class="conj-page-reading">【{displayReading}】</span>{/if}
			<span class="conj-page-label">{t('conjugations')}</span>
			{#if rows.length}<span class="kgroup-total">{rows.length}</span>{/if}
		</h1>
		<p class="conj-page-sub">
			{t('conjSubtitle', { word: heading })}
		</p>

		{#if fetchedRows && !exactMatch}
			<!-- Fallback match: the requested word has no table of its own — say
			     so; the heading above is the closest entry that does. -->
			<p class="notice">
				<Icon name="info" size={18} /> {t('conjClosestMatch', { word, headword: heading })}
			</p>
		{/if}

		{#if busy}
			<div class="kgroup-loading"><span class="spinner"></span></div>
		{:else if error}
			<p class="error-banner"><Icon name="warning" size={18} /> {error}</p>
		{:else if rows.length}
			<table class="conj-page-table">
				<thead>
					<tr>
						<th>{t('form')}</th>
						<th>{t('written')}</th>
						<th>{t('kana')}</th>
					</tr>
				</thead>
				<tbody>
					{#each rows as row (row.form)}
						<tr>
							<th scope="row">{row.form}</th>
							<td lang="ja">{row.surface}</td>
							<td class="conj-kana" lang="ja">{row.kana ?? '—'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}

		<div class="conj-page-back">
			<button type="button" class="btn-3d" onclick={goBack}>
				<!-- goBack() searches the requested form (?q=<word>), not the
				     matched headword the table above heads with — label the
				     destination, not the heading. -->
				← {t('backTo', { word: word || heading })}
			</button>
		</div>
	{/if}
</div>
