<script lang="ts">
	import { page } from '$app/state';
	import { ApiError, esConjugations } from '#lib/api.ts';
	import { groupInflections, type EsInflectionGroup } from '#lib/lang/es.ts';
	import { formatNumber, t } from '#lib/i18n.svelte.ts';
	import Header from './Header.svelte';
	import Icon from './Icon.svelte';

	const word = $derived((page.url.searchParams.get('word') ?? '').trim());
	const backHref = $derived(word ? `/?${new URLSearchParams({ q: word })}` : '/');
	let table = $state.raw<{ word: string; groups: EsInflectionGroup[] } | null>(null);
	let error = $state('');
	const count = $derived(table?.groups.reduce((total, group) => total + group.rows.length, 0) ?? 0);

	$effect(() => {
		const requested = word;
		table = null;
		error = '';
		if (!requested) return;
		let stale = false;
		esConjugations(requested).then(
			(result) => {
				if (!stale) table = { word: result.word, groups: groupInflections(result.inflected_forms) };
			},
			(cause: unknown) => {
				if (stale) return;
				error = cause instanceof ApiError && cause.status === 404
					? t('noConjData', { word: requested })
					: cause instanceof Error ? cause.message : t('conjLoadFailed');
			}
		);
		return () => { stale = true; };
	});
</script>

<svelte:head>
	<title>{t('conjPageTitle', { word: table?.word || word || t('conjugations') })} — Reikun</title>
</svelte:head>

<Header />
<div class="conj-page-wrap">
	<nav class="group-nav-bar">
		<a class="btn-3d" href={backHref}>← {word ? t('backTo', { word }) : t('backToSearch')}</a>
	</nav>
	{#if !word}
		<p class="notice"><Icon name="info" size={18} /> {t('noWord')}</p>
	{:else}
		<h1 class="conj-page-title">
			<span lang="es">{table?.word ?? word}</span>
			<span class="conj-page-label">{t('conjugations')}</span>
			{#if count}<span class="kgroup-total">{formatNumber(count)}</span>{/if}
		</h1>
		{#if error}
			<p class="error-banner" role="alert"><Icon name="warning" size={18} /> {error}</p>
		{:else if !table}
			<div class="kgroup-loading" role="status" aria-label={t('searching')}><span class="spinner"></span></div>
		{:else if !count}
			<p class="notice">{t('noConjData', { word })}</p>
		{:else}
			{#if table.word.toLowerCase() !== word.toLowerCase()}
				<p class="notice">
					<Icon name="info" size={18} /> {t('conjClosestMatch', { word, headword: table.word })}
				</p>
			{/if}
			{#each table.groups as group (group.label)}
				<table class="conj-page-table">
					<caption>{group.label}</caption>
					<thead>
						<tr><th scope="col">{t('form')}</th><th scope="col">{t('written')}</th></tr>
					</thead>
					<tbody>
						{#each group.rows as row}
							<tr><th scope="row">{row.form}</th><td lang="es">{row.surface}</td></tr>
						{/each}
					</tbody>
				</table>
			{/each}
		{/if}
	{/if}
</div>

<style>
	caption {
		margin: var(--space-4) 0 var(--space-1);
		color: var(--text-muted);
		font-weight: 600;
		text-align: left;
	}

	.conj-page-table th, .conj-page-table td {
		overflow-wrap: anywhere;
	}
</style>
