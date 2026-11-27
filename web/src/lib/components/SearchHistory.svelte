<script lang="ts">
	import { page } from '$app/state';
	import { t } from '#lib/i18n.svelte.ts';
	import { clearRecent, loadRecent } from '#lib/recent.ts';

	let { close }: { close: () => void } = $props();
	// The popover mounts its contents on each open, so this also sees searches
	// from another tab or from the Japanese Lite UI.
	let recent = $state.raw(loadRecent());

	function searchHref(query: string): string {
		const params = new URLSearchParams({ q: query });
		const level = page.url.searchParams.get('level');
		if (level) params.set('level', level);
		return `${page.url.pathname === '/es' ? '/es' : '/'}?${params}`;
	}

	function clearHistory() {
		if (!recent.length) return;
		clearRecent();
		recent = [];
	}
</script>

<div class="history-heading">
	<p class="popover-title">{t('recentSearches')}</p>
	<button
		type="button"
		class="history-clear"
		aria-disabled={!recent.length}
		onclick={clearHistory}
	>{t('clear')}</button>
</div>
{#if recent.length}
	<ul>
		{#each recent as query (query)}
			<li><a href={searchHref(query)} onclick={close} data-popover-focus>{query}</a></li>
		{/each}
	</ul>
{:else}
	<p class="history-empty" role="status" tabindex="-1" data-popover-focus>{t('noRecentSearches')}</p>
{/if}

<style>
	.history-heading {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--space-3);
	}

	.history-clear {
		padding: var(--space-1);
		border: 0;
		border-radius: var(--radius-xs);
		background: none;
		color: var(--text-muted);
		cursor: pointer;
		font: inherit;
		font-size: var(--fs-sm);
	}

	.history-clear[aria-disabled='true'] {
		opacity: 0.55;
		cursor: default;
	}

	.history-clear:hover:not([aria-disabled='true']), a:hover {
		background: var(--hover-bg);
		color: var(--text);
	}

	ul {
		margin: 0;
		list-style: none;
		max-height: min(21rem, 65vh);
		overflow-y: auto;
		/* Leave room for the keyboard focus outline within the scroll area. */
		padding: var(--space-1);
	}

	a {
		display: block;
		padding: var(--space-2);
		border-radius: var(--radius-sm);
		color: var(--text);
		text-decoration: none;
		overflow-wrap: anywhere;
	}

	.history-empty {
		margin: var(--space-2) 0 0;
		color: var(--text-muted);
		font-size: var(--fs-sm);
	}
</style>
