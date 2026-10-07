<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import {
		apiRandomKanji,
		apiSearch,
		isTransient,
		LEVELS,
		sleep,
		type Level,
		type SearchResponse
	} from '#lib/api.ts';
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
	import { typewriter } from '#lib/typewriter.svelte.ts';

	const TAGLINE =
		'Search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji, and get grammar explanations.';
	const EXAMPLES = ['train', '国', '海外', 'How do you say cheese in Japanese', 'あの店のサービスは素晴らしいです。'];
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

	let qInput = $state('');
	let searchInput = $state<HTMLInputElement>();
	// Auto-focus drops the caret on desktop; on touch it would open the
	// on-screen keyboard over the hero before the user asks for it.
	onMount(() => {
		if (!matchMedia('(pointer: coarse)').matches) searchInput?.focus({ preventScroll: true });
	});
	let resp = $state.raw<SearchResponse | null>(null);
	let searching = $state(false);
	let waking = $state(false);
	let error = $state('');
	let committed = $state('');
	let wantResults = $state(DEFAULT_RESULTS);

	function handleWindowKeydown(e: KeyboardEvent) {
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
		const l = page.url.searchParams.get('level') ?? '';
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
		if (q !== committed) wantResults = DEFAULT_RESULTS; // reset before urlKey below
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
		runSearch(q);
	});

	// Stale-response guard: a superseded search can't overwrite newer results.
	let reqSeq = 0;
	async function runSearch(q: string) {
		const seq = ++reqSeq;
		searching = true;
		waking = false;
		error = '';
		// Slow API on a scale-to-zero host (or a sleeping Qdrant free cluster)
		// → tell the user it's waking, not hung, and retry once automatically.
		const wakeTimer = setTimeout(() => {
			if (seq === reqSeq) waking = true;
		}, 3000);
		try {
			let r: SearchResponse;
			try {
				r = await apiSearch(q, wantResults);
			} catch (e) {
				if (seq !== reqSeq || !isTransient(e)) throw e;
				waking = true;
				await sleep(2000);
				if (seq !== reqSeq) return;
				r = await apiSearch(q, wantResults);
			}
			if (seq === reqSeq) resp = r;
		} catch (e) {
			if (seq === reqSeq) {
				resp = null;
				error =
					e instanceof TypeError
						? 'The API is unreachable — it may be waking up after a cold start. Try again in a few seconds.'
						: e instanceof Error
							? e.message
							: 'Search failed';
			}
		} finally {
			if (seq === reqSeq) {
				clearTimeout(wakeTimer);
				searching = false;
				waking = false;
			}
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
		try {
			commit(await apiRandomKanji(level));
		} catch {
			error = 'Could not reach the API for a random kanji.';
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
</script>

<svelte:head>
	<title>{committed ? `${committed} — Reikun` : 'Reikun (例訓) — Semantic Japanese Dictionary'}</title>
</svelte:head>

<svelte:window onkeydown={handleWindowKeydown} />

<Header hero={!hasResults} tagline={TAGLINE} />

<form class="search-row" onsubmit={submit}>
	<div class="search-pair">
		<span class="search-icon-prefix">
			<Icon name="search" size={18} />
		</span>
		<input
			type="search"
			placeholder={hasResults ? 'Search English or Japanese…' : hint.text}
			aria-label="Search"
			bind:value={qInput}
			bind:this={searchInput}
			autocomplete="off"
			autocapitalize="none"
			spellcheck="false"
		/>
		<button type="submit" class="search-go" title="Search" aria-label="Search">
			Search
		</button>
	</div>
	<button
		type="button"
		class="btn tertiary"
		title="Random {level} kanji"
		aria-label="Random {level} kanji"
		onclick={randomKanji}
	>
		<Icon name="shuffle" size={17} />
	</button>
	<Popover icon="school" label={level} title="JLPT level for grammar explanations">
		<p class="popover-title">JLPT Level</p>
		<Segmented options={LEVELS} value={level} onchange={setLevel} label="JLPT level" />
	</Popover>
</form>

{#if searching}
	<p class="searching-line"><span class="spinner"></span> Searching dictionary…</p>
{/if}
{#if waking && searching}
	<p class="wake">The API is taking a moment — it may be waking up from cold standby…</p>
{/if}
{#if error}
	<div class="error-banner"><Icon name="warning" size={16} /> {error}</div>
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
		<span class="stats-details">
			<span class="stats-info" aria-label="Query route, timing and cache details">
				<Icon name="info" size={14} />
			</span>
			<span class="stats-pop" role="tooltip">
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
		<SegChips segments={resp.segments} />
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
		<ResultCard result={r} {level} onPickKanji={commit} />
	{/each}

	{#if resp.results.length >= wantResults && wantResults < MAX_RESULTS}
		<button
			type="button"
			class="btn secondary"
			onclick={showMore}
			title="Refetches the search with up to {MAX_RESULTS} results"
		>
			<Icon name="expand-more" size={15} /> Show {PAGE_RESULTS} more
		</button>
	{/if}
{:else if !searching && !error}
	<div class="pills" aria-label="Example searches">
		{#each EXAMPLES as ex (ex)}
			<button type="button" class="pill" onclick={() => commit(ex)}>
				<Icon name="search" size={14} />
				<span>{ex}</span>
			</button>
		{/each}
	</div>
{/if}

<Footer />
