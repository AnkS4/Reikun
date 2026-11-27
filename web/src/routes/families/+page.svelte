<script lang="ts">
	import { page } from '$app/state';
	import { esFamilies, type EsFamily, type EsFamiliesResponse } from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import { formatNumber, t } from '#lib/i18n.svelte.ts';

	const selected = $derived(page.url.searchParams.get('word') ?? '');
	let data = $state.raw<EsFamiliesResponse | null>(null);
	let error = $state('');
	$effect(() => {
		let stale = false;
		data = null;
		error = '';
		esFamilies().then(
			(value) => { if (!stale) data = value; },
			(cause: unknown) => { if (!stale) error = cause instanceof Error ? cause.message : t('searchFailed'); }
		);
		return () => { stale = true; };
	});

	const family = $derived<EsFamily | null>(
		data?.families.find((item) => item.word.toLowerCase() === selected.toLowerCase()) ?? null
	);

	function wordHref(word: string): string {
		return `/?q=${encodeURIComponent(word)}`;
	}

	function familyHref(word: string): string {
		return `/families?word=${encodeURIComponent(word)}`;
	}
</script>

<svelte:head>
	<title>{family ? `${family.word} — ` : ''}{t('familiesTitle')} — Reikun</title>
	<meta name="description" content={t('familiesIntro')} />
</svelte:head>

<Header />

<div class="kgroup-wrap">
	<h1 class="kgroup-title">
		{#if family}<span lang="es">{family.word}</span>{:else}{t('familiesTitle')}{/if}
		{#if family}<span class="kgroup-total">{formatNumber(family.members.length)}</span>{/if}
	</h1>
	<p class="kgroup-sub">
		{t('familiesIntro')} <a href="https://es.wiktionary.org/" target="_blank" rel="noopener noreferrer">Spanish Wiktionary</a>.
	</p>

	{#if error}
		<p class="error-banner" role="alert">{error}</p>
	{:else if !data}
		<div class="kgroup-loading" role="status" aria-label={t('searching')}><span class="spinner"></span></div>
	{:else if family}
		<div class="kg-grid">
			{#each family.members as member (member.word)}
				<a class="kg-card" href={wordHref(member.word)}>
					<span class="kv-value" lang="es">{member.word}</span>
					<span class="kg-meta">{member.gloss || '—'}</span>
				</a>
			{/each}
		</div>
		<div class="kgroup-bottom-actions"><a class="btn-3d" href="/families">← {t('familiesBack')}</a></div>
	{:else if data.families.length}
		<div class="kg-grid">
			{#each data.families as item (item.word)}
				<a class="kg-card" href={familyHref(item.word)}>
					<span class="kv-value" lang="es">{item.word}</span>
					<span class="kg-meta">{t('familiesMembers', { count: formatNumber(item.members.length) })}</span>
				</a>
			{/each}
		</div>
	{:else}
		<p>No word families available yet.</p>
	{/if}
</div>
