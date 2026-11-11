<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Header from '#lib/components/Header.svelte';
	import KanjiCard from '#lib/components/KanjiCard.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Popover from '#lib/components/Popover.svelte';
	import { t } from '#lib/i18n.svelte.ts';
	import { isKanji } from '#lib/kanji.ts';
	import { apiRandomKanji, LEVELS, type Level } from '#lib/api.ts';
	import { pushRecent } from '#lib/recent.ts';
	import { furigana } from '#lib/furigana.svelte.ts';

	const char = $derived(page.params.char ?? '');
	// Back context threaded by the linking page: `from` is the previous page's
	// label (a search word, another kanji, or a kanji-group label), and `gq` is
	// a pre-encoded copy of the group page's params when that page was a group.
	const from = $derived(page.url.searchParams.get('from') ?? '');
	const gq = $derived(page.url.searchParams.get('gq') ?? '');

	let qInput = $state('');
	let searchInput = $state<HTMLInputElement>();
	let randomBusy = $state(false);
	const level = $state<Level>('N5');

	function setLevel(l: Level) {
		// no-op on kanji page — level only matters for the random pick
	}

	async function submitSearch(e: Event) {
		e.preventDefault();
		const q = qInput.trim();
		if (q) goto(`/?q=${encodeURIComponent(q)}`);
	}

	async function randomKanji() {
		if (randomBusy) return;
		randomBusy = true;
		try {
			const c = await apiRandomKanji(level);
			// Same as the homepage shuffle: a random pick lands in recents.
			pushRecent(c);
			goto(`/kanji/${encodeURIComponent(c)}?from=${encodeURIComponent(char)}`);
		} catch {
			// ignore
		} finally {
			randomBusy = false;
		}
	}

	function goBack() {
		if (typeof window !== 'undefined' && window.history.length > 1) {
			window.history.back();
			return;
		}
		// Deep-linked without history: reconstruct the page the context names.
		if (gq) {
			goto(`/kanji-group?${gq}`);
		} else if (from) {
			goto(
				isKanji(from)
					? `/kanji/${encodeURIComponent(from)}`
					: `/?q=${encodeURIComponent(from)}`
			);
		} else {
			goto('/');
		}
	}
</script>

<svelte:head>
	<title>{char ? `${char} — Reikun` : 'Reikun'}</title>
</svelte:head>

<Header />
<form class="search-row" role="search" onsubmit={submitSearch}>
	<div class="search-pair">
		<input
			type="search"
			placeholder={t('searchPlaceholder')}
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
			<Icon name="close" size={15} />
		</button>
		<button type="submit" class="search-submit" aria-label={t('search')} title={t('search')}>
			<Icon name="search" size={15} />
		</button>
	</div>
	<button
		type="button"
		class="btn-3d no-press"
		title={t('randomKanji', { level })}
		aria-label={t('randomKanji', { level })}
		aria-busy={randomBusy}
		disabled={randomBusy}
		onclick={randomKanji}
	>
		{#if randomBusy}<span class="spinner" aria-hidden="true"></span>{:else}<Icon name="shuffle" size={15} />{/if}
	</button>
	<!-- Furigana toggle: visible one-click control (the Appearance popover in
	     the Header is the secondary location). Reads are on by default; the あ
	     glyph dims + strikes over when they're hidden. -->
	<button
		type="button"
		class="btn-3d furi-toggle"
		class:off={!furigana.on}
		title={furigana.on ? t('furiganaShown') : t('furiganaHidden')}
		aria-label={t('furiganaToggle')}
		aria-pressed={furigana.on}
		onclick={() => furigana.toggle()}
	>
		<span class="furi-glyph" aria-hidden="true">あ</span>
	</button>
	<Popover label={level} title={t('jlptTitle')} buttonClass="btn-3d jlpt-trigger">
		<p class="popover-title">{t('jlptLevel')}</p>
		<div class="segmented" role="group" aria-label={t('jlptLevel')}>
			{#each LEVELS as l (l)}
				<button
					type="button"
					class:sel={level === l}
					aria-pressed={level === l}
					onclick={() => setLevel(l)}>{l}</button
				>
			{/each}
		</div>
	</Popover>
</form>
<div class="kanji-detail-wrap">
	{#if !char || !isKanji(char)}
		<p class="notice"><Icon name="info" size={16} /> {char ? t('notAKanji', { char }) : t('noKanjiGiven')}</p>
	{:else}
		<KanjiCard char={char} />

		<div class="kanji-page-back">
			<button type="button" class="btn-3d" onclick={goBack} title={from ? t('backTo', { word: from }) : t('goBack')}>
				← {#if from}{t('backTo', { word: from })}{:else}{t('backToSearch')}{/if}
			</button>
		</div>
	{/if}
</div>
