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

	$effect(() => {
		const w = word;
		fetchedRows = null;
		fetchedHeadword = '';
		error = '';
		if (!w || stateRows) return; // nav state already has data
		busy = true;
		apiSearch(w, 3)
			.then((resp) => {
				// Find the entry whose dictionary form matches the word param
				const match = resp.results.find(
					(r: SearchResult) =>
						r.inflected_forms?.length &&
						(r.kanji_form === w || r.reading === w)
				) ?? resp.results.find((r: SearchResult) => r.inflected_forms?.length);
				if (match) {
					fetchedRows = match.inflected_forms;
					fetchedHeadword = match.kanji_form || match.reading || w;
				} else {
					error = t('noConjData', { word: w });
				}
			})
			.catch((e) => {
				error = e instanceof Error ? e.message : t('conjLoadFailed');
			})
			.finally(() => (busy = false));
	});

	const rows = $derived(stateRows ?? fetchedRows ?? []);
	const heading = $derived(word || fetchedHeadword || t('conjugationFallback'));
	const displayReading = $derived(reading && reading !== word ? reading : '');
</script>

<svelte:head>
	<title>{t('conjPageTitle', { word: heading })} — Reikun</title>
</svelte:head>

<Header />
<div class="conj-page-wrap">
	<nav class="group-nav-bar">
		<button type="button" class="group-back-btn" onclick={goBack} title={word ? t('backTo', { word }) : t('goBack')}>
			← {#if word}{t('backTo', { word })}{:else}{t('backToSearch')}{/if}
		</button>
		<a href="/" class="group-home-link">{t('reikunHome')}</a>
	</nav>
	{#if !word}
		<p class="notice"><Icon name="info" size={16} /> {t('noWord')}</p>
	{:else}
		<h1 class="conj-page-title" lang="ja">
			{heading}
			{#if displayReading}<span class="conj-page-reading">【{displayReading}】</span>{/if}
			<span class="conj-page-label">{t('conjugationsLabel')}</span>
			{#if rows.length}<span class="kgroup-total">{rows.length}</span>{/if}
		</h1>
		<p class="conj-page-sub">
			{t('conjSubtitle', { word: heading })}
		</p>

		{#if busy}
			<div class="kgroup-loading"><span class="spinner"></span></div>
		{:else if error}
			<p class="error-banner"><Icon name="warning" size={16} /> {error}</p>
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
				← {t('backTo', { word: heading })}
			</button>
		</div>
	{/if}
</div>
