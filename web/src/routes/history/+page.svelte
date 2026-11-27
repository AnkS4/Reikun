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
		<!-- Same pill buttons as beneath the search box on the home page. -->
		<div class="pills" aria-label={t('recentSearches')}>
			{#each recent as query (query)}
				<a class="pill" href={searchHref(query)}>{query}</a>
			{/each}
		</div>
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

	.pills {
		justify-content: flex-start;
	}

	.pill {
		overflow-wrap: anywhere;
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
