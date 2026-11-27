<script lang="ts">
	import { page } from '$app/state';
	import Header from '#lib/components/Header.svelte';
	import { BRAND_SHORT } from '#lib/brand.ts';
	import { t } from '#lib/i18n.svelte.ts';
	import { clearRecent, loadRecent } from '#lib/recent.ts';

	let recent = $state.raw(loadRecent());

	function searchHref(query: string): string {
		const params = new URLSearchParams({ q: query });
		const level = page.url.searchParams.get('level');
		if (level) params.set('level', level);
		return `/?${params}`;
	}

	function clearHistory() {
		if (!recent.length) return;
		clearRecent();
		recent = [];
	}
</script>

<svelte:head>
	<title>{t('recentSearches')} — {BRAND_SHORT}</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<Header />

<section class="history-page" aria-labelledby="history-title">
	<div class="history-heading">
		<h2 id="history-title">{t('recentSearches')}</h2>
		<button
			type="button"
			class="btn tertiary"
			aria-disabled={!recent.length}
			onclick={clearHistory}
		>{t('clear')}</button>
	</div>
	{#if recent.length}
		<ul>
			{#each recent as query (query)}
				<li><a href={searchHref(query)}>{query}</a></li>
			{/each}
		</ul>
	{:else}
		<p class="history-empty" role="status">{t('noRecentSearches')}</p>
	{/if}
	<p><a class="history-back" href="/">{t('backToSearch')}</a></p>
</section>

<style>
	.history-page {
		margin-block: var(--space-5);
	}

	.history-heading {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--space-3);
	}

	button[aria-disabled='true'] {
		opacity: 0.55;
		cursor: default;
	}

	ul {
		margin: 0;
		list-style: none;
		padding: 0;
		border-top: 1px solid var(--border-soft);
	}

	li a {
		display: block;
		padding: var(--space-3) var(--space-2);
		border-bottom: 1px solid var(--border-soft);
		color: var(--text);
		text-decoration: none;
		overflow-wrap: anywhere;
	}

	li a:hover {
		background: var(--hover-bg);
	}

	.history-back {
		color: var(--primary);
	}

	.history-empty {
		margin: var(--space-2) 0 0;
		color: var(--text-muted);
		font-size: var(--fs-sm);
	}
</style>
