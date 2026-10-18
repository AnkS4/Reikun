<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/env';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiRandomKanji, apiSearch, LEVELS, type Level, type SearchResponse } from '#lib/api.ts';
	import { isKanji } from '#lib/kanji.ts';
	import Header from '#lib/components/Header.svelte';
	import Footer from '#lib/components/Footer.svelte';
	import Popover from '#lib/components/Popover.svelte';
	import Segmented from '#lib/components/Segmented.svelte';
	import SegChips from '#lib/components/SegChips.svelte';
	import KanjiCard from '#lib/components/KanjiCard.svelte';
	import ResultCard from '#lib/components/ResultCard.svelte';
	import Feedback from '#lib/components/Feedback.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import ShareButton from '#lib/components/ShareButton.svelte';
	import { loadRecent, pushRecent, clearRecent } from '#lib/recent.ts';
	import { typewriter } from '#lib/typewriter.svelte.ts';

	// Floating button state
	let showBackToTop = $state(false);

	const EXAMPLES = ['train', '国', '海外', 'How do you say cheese in Japanese', 'あの店のサービスは素晴らしいです。'];
	const TAGLINE =
		'Search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji, and get grammar explanations.';
	const HINTS = [
		'Type or tap an example below'
	];
	// Retrieval is ~25 ms — a page of ten costs the same as five; "Show more" refetches.
	const DEFAULT_RESULTS = 10;
	const PAGE_RESULTS = 10;
	const MAX_RESULTS = 50;
	// Mirrored from app/retrieval.py for the too-long warning text.
	const MAX_QUERY_CHARS = 150;
	const MAX_JA_QUERY_CHARS = 100;

	let recent = $state<string[]>([]);
	let activeCard = $state(-1);
	let qInput = $state('');
	let searchInput = $state<HTMLInputElement>();
	// Auto-focus drops the caret on desktop; on touch it would open the
	// on-screen keyboard over the hero before the user asks for it.
	onMount(() => {
		recent = loadRecent();
		if (!matchMedia('(pointer: coarse)').matches) searchInput?.focus({ preventScroll: true });
		// Floating buttons: track scroll
		const handleScroll = () => {
			showBackToTop = window.scrollY > 300;
		};
		window.addEventListener('scroll', handleScroll, { passive: true });
		return () => window.removeEventListener('scroll', handleScroll);
	});

	function scrollToTop() {
		window.scrollTo({ top: 0, behavior: 'smooth' });
	}
	let resp = $state.raw<SearchResponse | null>(null);
	let searching = $state(false);
	let randomBusy = $state(false);
	let error = $state('');
	let committed = $state('');
	let wantResults = $state(DEFAULT_RESULTS);

	function moveCard(delta: number) {
		const n = resp?.results.length ?? 0;
		if (!n) return;
		activeCard = Math.max(0, Math.min(n - 1, activeCard < 0 ? (delta > 0 ? 0 : n - 1) : activeCard + delta));
		document
			.querySelectorAll('.result-card')
			[activeCard]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
	}

	function handleWindowKeydown(e: KeyboardEvent) {
		const el = document.activeElement;
		const typing = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement;
		if (!e.metaKey && !e.ctrlKey && !e.altKey && resp?.results.length) {
			const down = e.key === 'ArrowDown' || (!typing && e.key === 'j');
			const up = e.key === 'ArrowUp' || (!typing && e.key === 'k');
			if ((down || up) && (!typing || el === searchInput) && !el?.closest('[role="dialog"]')) {
				e.preventDefault();
				moveCard(down ? 1 : -1);
				return;
			}
			if (e.key === 'Escape' && activeCard >= 0 && !typing) activeCard = -1;
		}
		if (
			e.key === '/' &&
			document.activeElement !== searchInput &&
			!(document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement)
		) {
			e.preventDefault();
			searchInput?.focus();
		} else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
			e.preventDefault();
			searchInput?.focus();
			searchInput?.select();
		}
	}

	const level = $derived.by((): Level => {
		// searchParams is unavailable during prerender — default to N5 there;
		// hydration re-evaluates with the real URL.
		const l = browser ? page.url.searchParams.get('level') ?? '' : '';
		return (LEVELS as readonly string[]).includes(l) ? (l as Level) : 'N5';
	});
	const kanjiChar = $derived(isKanji(committed) ? committed : null);
	const meta = $derived(resp?.meta);
	// latency_ms spans rewrite → route → embed → retrieve → segment; the label
	// lists every measured phase so the parts visibly sum to the total (parse
	// is only measured on the ja route, rewrite only shown when it cost >0ms).
	const phases = $derived(
		meta?.embed_ms == null
			? ''
			: [
					meta.rewrite_ms ? `rewrite ${meta.rewrite_ms} ms` : '',
					`embed ${meta.embed_ms} ms`,
					`retrieve ${meta.retrieve_ms} ms`,
					meta.segment_ms != null ? `parse ${meta.segment_ms} ms` : '',
				]
					.filter(Boolean)
					.join(' · '),
	);
	const hasResults = $derived(resp !== null);
	const infoId = $props.id();
	// One always-mounted live region: screen readers hear search progress and the
	// outcome without having to find the visual stats line.
	const announce = $derived(
		searching
			? 'Searching…'
			: error
				? error
				: resp
					? `${resp.results.length} ${resp.results.length === 1 ? 'entry' : 'entries'} for ${committed}`
					: ''
	);
	// The getter lets the typewriter stop entirely once results take over the
	// placeholder — no timer churning behind a finished search.
	const hint = typewriter(() => (hasResults ? [] : HINTS));

	// URL → search: ?q= drives everything (deep links, back/forward, pills).
	// ?kanji= is a legacy deep link → becomes a single-kanji search. urlKey
	// dedupes effect refires on params we don't care about (level).
	let handledUrl = '';
	$effect(() => {
		const sp = page.url.searchParams;
		const legacy = sp.get('kanji');
		if (legacy) {
			const u = new URL(page.url.href);
			u.searchParams.delete('kanji');
			if (isKanji(legacy)) u.searchParams.set('q', legacy);
			goto(u, { replace: true });
			return;
		}
		const q = (sp.get('q') ?? '').trim();
		if (q !== committed) {
			wantResults = DEFAULT_RESULTS; // reset before urlKey below
			activeCard = -1;
			resp = null; // skeletons take over until the new results land
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
		recent = pushRecent(q);
		runSearch(q);
	});

	// Stale-response guard: a superseded search can't overwrite newer results.
	// Timeouts, automatic retries and the "server is waking up" banner live in
	// the API layer (api.ts → <WakeBanner>), so this only tracks the latest request.
	let reqSeq = 0;
	async function runSearch(q: string) {
		const seq = ++reqSeq;
		searching = true;
		error = '';
		try {
			const r = await apiSearch(q, wantResults);
			if (seq === reqSeq) {
				resp = r;
				activeCard = -1;
			}
		} catch (e) {
			if (seq === reqSeq) {
				resp = null;
				error = e instanceof Error ? e.message : 'Search failed';
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
		// Desktop keeps the caret — pills, kanji picks, shuffle all land here.
		// Touch drops it so the on-screen keyboard collapses off the results.
		if (matchMedia('(pointer: coarse)').matches) searchInput?.blur();
		else searchInput?.focus({ preventScroll: true });
		// Same query again (re-submit, same kanji picked twice) → search directly;
		// a changed query goes through ?q= so history records it. A kanji repick
		// doesn't change kanjiChar → scroll imperatively, the effect won't refire.
		if (v === committed) {
			if (isKanji(v)) scrollToKanji();
			if (v) runSearch(v);
		} else setQuery(v);
	}

	function submit(e: SubmitEvent) {
		e.preventDefault();
		commit(qInput.trim());
	}

	function setLevel(l: Level) {
		const u = new URL(page.url.href);
		u.searchParams.set('level', l);
		goto(u, { replace: true, reset: false });
	}

	async function randomKanji() {
		if (randomBusy) return; // already fetching — extra taps would queue duplicate requests
		randomBusy = true;
		error = '';
		try {
			commit(await apiRandomKanji(level));
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not get a random kanji.';
		} finally {
			randomBusy = false;
		}
	}

	function showMore() {
		// wantResults is part of urlKey — the effect refires with the larger n.
		wantResults = Math.min(wantResults + PAGE_RESULTS, MAX_RESULTS);
	}

	// Kanji picks happen deep in the results list — scroll the card into view or
	// the click looks dead. Fires when a new char renders the card (repicks of
	// the same char are handled in commit(), where the imperative scroll lives).
	let kanjiAnchor = $state<HTMLDivElement>();
	function scrollToKanji() {
		const el = kanjiAnchor;
		if (!el) return;
		const reveal = () => {
			// Only scroll when the card is actually hidden — behind the
			// sticky bar or below the fold. A card already in view never
			// gets nudged, so no up-then-down correction.
			const bar = document.querySelector('.search-row')?.getBoundingClientRect().bottom ?? 0;
			const top = el.getBoundingClientRect().top;
			if (top >= bar && top < window.innerHeight) return;
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		};
		reveal();
		// Late shifts push the card under the sticky header — keyboard
		// collapsing on mobile, JP font swap reflowing the layout.
		setTimeout(reveal, 450);
	}
	$effect(() => {
		if (kanjiChar && kanjiAnchor) scrollToKanji();
	});

	function jumpToSegment(s: import('#lib/api.ts').Segment, segIdx: number) {
		if (!resp?.results.length) return;
		let cardIdx = resp.results.findIndex(
			(r) =>
				(s.kanji_form && r.kanji_form === s.kanji_form) ||
				(s.text && (r.text === s.text || r.kanji_form === s.text)) ||
				(s.reading && r.reading === s.reading)
		);
		if (cardIdx < 0 && segIdx < resp.results.length && resp.segments?.length === resp.results.length) {
			cardIdx = segIdx;
		}
		if (cardIdx >= 0) {
			activeCard = cardIdx;
			const cards = document.querySelectorAll('.result-card');
			cards[cardIdx]?.scrollIntoView({ block: 'start', behavior: 'smooth' });
		} else {
			const head = s.kanji_form || s.reading || s.text;
			if (head) commit(head);
		}
	}
</script>

<svelte:head>
	<title>{committed ? `${committed} — Reikun` : 'Reikun (例訓) — Semantic Japanese Dictionary'}</title>
</svelte:head>

<svelte:window onkeydown={handleWindowKeydown} />

<Header hero={!hasResults && !searching} tagline={TAGLINE} />

<form class="search-row" role="search" onsubmit={submit}>
	<div class="search-pair">
		<span class="search-icon-prefix">
			<Icon name="search" size={18} />
		</span>
		<input
			type="search"
			id="search"
			placeholder={hasResults ? 'Search English or Japanese…' : hint.text}
			aria-label="Search"
			bind:value={qInput}
			bind:this={searchInput}
			autocomplete="off"
			autocapitalize="none"
			spellcheck="false"
		/>
		<button type="submit" class="search-submit">
			Search
		</button>
	</div>
	<button
		type="button"
		class="btn-3d"
		title="Random {level} kanji"
		aria-label="Random {level} kanji"
		aria-busy={randomBusy}
		disabled={randomBusy}
		onclick={randomKanji}
	>
		{#if randomBusy}<span class="spinner" aria-hidden="true"></span>{:else}<Icon name="shuffle" size={17} />{/if}
	</button>
	<Popover icon="school" label={level} title="JLPT level for grammar explanations" buttonClass="btn-3d">
		<p class="popover-title">JLPT Level</p>
		<Segmented options={LEVELS} value={level} onchange={setLevel} label="JLPT level" />
	</Popover>
</form>

<div class="sr-only" role="status" aria-live="polite">{announce}</div>

{#if searching && !resp}
	<div class="skeletons" aria-hidden="true">
		{#each [0, 1, 2] as n (n)}
			<div class="skeleton-card">
				<span class="sk sk-head"></span>
				<span class="sk sk-line"></span>
				<span class="sk sk-line short"></span>
				<span class="sk sk-line"></span>
			</div>
		{/each}
	</div>
{/if}
{#if error}
	<div class="error-banner" role="alert"><Icon name="warning" size={16} /> {error}</div>
{/if}

{#if resp}
	{#if kanjiChar}
		<div bind:this={kanjiAnchor} class="kanji-anchor">
			<KanjiCard char={kanjiChar} />
		</div>
	{/if}

	<div class="stats-line">
		<span class="stats-count">{resp.results.length} {resp.results.length === 1 ? 'entry' : 'entries'}</span>
		<Feedback kind="search" refId={resp.search_id ?? null} query={committed} />
		{#if committed}<ShareButton query={committed} />{/if}
		<span class="stats-details">
			<!-- svelte-ignore a11y_no_noninteractive_tabindex — focusable so the details tooltip opens by keyboard -->
			<span
				class="stats-info"
				role="img"
				tabindex="0"
				aria-label="Query route, timing and cache details"
				aria-describedby={infoId}
			>
				<Icon name="info" size={14} />
			</span>
			<span class="stats-pop" role="tooltip" id={infoId}>
				<span class="popover-title">Technical info</span>
				<span class="stats-meta"
					><span class="stats-label">route</span>{resp.mode}{meta?.route
						? ` · ${meta.route}`
						: ''}</span
				>
				<span class="stats-meta"><span class="stats-label">total</span>{resp.latency_ms} ms</span>
				{#if meta?.cached}
					<span class="stats-meta"><span class="stats-label">cache</span>hit</span>
				{:else if phases}
					<span class="stats-meta"><span class="stats-label">stages</span>{phases}</span>
				{/if}
			</span>
		</span>
	</div>

	{#if resp.rewrite.changed}
		<p class="caption">
			Searched for <b>{resp.rewrite.query}</b>
		</p>
	{/if}

	{#if resp.segments?.length}
		<SegChips segments={resp.segments} onjump={jumpToSegment} />
	{/if}

	{#if !resp.results.length}
		{#if meta?.too_long}
			{@const shown = committed.length > 24 ? committed.slice(0, 24) + '…' : committed}
			<div class="warning">
				<Icon name="warning" size={16} />
				{#if meta.too_long === MAX_JA_QUERY_CHARS}
					“{shown}” is too long — Japanese input is parsed up to {MAX_JA_QUERY_CHARS} characters;
					enter a word or a shorter sentence.
				{:else}
					“{shown}” is too long for a dictionary lookup — enter a single word or a short phrase
					({MAX_QUERY_CHARS} characters max).
				{/if}
			</div>
		{:else if kanjiChar}
			<div class="notice">
				<Icon name="info" size={16} /> “{kanjiChar}” isn't a standalone dictionary word — see the
				common words above for it in use.
			</div>
		{:else}
			<div class="warning">
				<Icon name="warning" size={16} /> Nothing found. Try a different English or Japanese word.
			</div>
		{/if}
	{/if}

	{#each resp.results as r, i (`${r.id ?? r.text}-${i}`)}
		<ResultCard result={r} {level} onPickKanji={commit} active={i === activeCard} />
	{/each}

	{#if resp.results.length >= wantResults && wantResults < MAX_RESULTS}
		<button
			type="button"
			class="btn-3d"
			onclick={showMore}
			title="Refetches the search with up to {MAX_RESULTS} results"
		>
			<Icon name="expand-more" size={15} /> Show {PAGE_RESULTS} more
		</button>
	{/if}
{:else if !searching && !error}
	{#if recent.length === 0}
	<div class="pills" aria-label="Example searches">
		{#each EXAMPLES as ex (ex)}
			<button type="button" class="pill" onclick={() => commit(ex)}>
				<Icon name="search" size={14} />
				<span>{ex}</span>
			</button>
		{/each}
	</div>
	{/if}
	{#if recent.length}
		<div class="recent">
			<p class="popover-title">
				Recent
				<button
					type="button"
					class="recent-clear"
					onclick={() => {
						clearRecent();
						recent = [];
					}}>Clear</button
				>
			</p>
			<div class="pills" aria-label="Recent searches">
				{#each recent as q (q)}
					<button type="button" class="pill" onclick={() => commit(q)}>
						<Icon name="search" size={14} />
						<span lang="ja">{q}</span>
					</button>
				{/each}
			</div>
		</div>
	{/if}
{/if}

<!-- Floating navigation button -->
{#if showBackToTop}
	<div class="floating-buttons">
		<button
			type="button"
			class="floating-btn visible"
			onclick={scrollToTop}
			title="Scroll to top"
			aria-label="Scroll to top"
		>
			<Icon name="arrow-up" size={16} />
		</button>
	</div>
{/if}

<Footer />
