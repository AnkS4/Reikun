<script lang="ts">
	import { page } from '$app/state';
	import { apiKanjiGroup, type GroupKey, type KanjiGroupResponse } from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import Footer from '#lib/components/Footer.svelte';
	import Icon from '#lib/components/Icon.svelte';

	// One page of the grid; eight columns of six rows on desktop, and the
	// API cap keeps a foulest-offset request from doing more work than this.
	const PAGE_SIZE = 48;

	const GROUPS: Record<GroupKey, string> = {
		strokes: 'strokes',
		grade: 'grade',
		jlpt: 'JLPT level'
	};

	// Validated request descriptor — anything unrecognized renders the
	// bad-request notice instead of a fetch.
	let req = $derived.by((): { by: GroupKey; value: number; skip: number } | null => {
		const params = page.url.searchParams;
		const raw = params.get('by');
		const value = Number(params.get('value'));
		const by: GroupKey | null =
			raw === 'strokes' || raw === 'grade' || raw === 'jlpt' ? raw : null;
		if (!by) return null;
		return { by, value, skip: Math.max(0, Math.round(Number(params.get('page') ?? 0))) * PAGE_SIZE };
	});

	let data = $state.raw<KanjiGroupResponse | null>(null);
	let busy = $state(false);
	let error = $state('');

	$effect(() => {
		const r = req;
		data = null;
		error = '';
		if (!r) return;
		busy = true;
		apiKanjiGroup(r.by, r.value, PAGE_SIZE, r.skip)
			.then((d) => (data = d))
			.catch((e) => (error = e instanceof Error ? e.message : 'Failed to load the kanji group'))
			.finally(() => (busy = false));
	});

	const pageNo = $derived(req ? Math.floor(req.skip / PAGE_SIZE) + 1 : 0);
	const pages = $derived(data ? Math.ceil(data.total / PAGE_SIZE) : 0);

	// Pagination navigates via ?page= so every page is a real entry in the
	// session history (an explicit URL the back button undoes).
	function pageHref(p: number): string {
		return `/kanji-group?by=${req?.by}&value=${req?.value}&page=${p}`;
	}

	function metaLine(k: KanjiGroupResponse['kanjis'][number]): string {
		return [
			k.stroke_count ? `${k.stroke_count} strokes` : '',
			k.jlpt_level ? { 4: 'N5', 3: 'N4', 2: 'N2-N3', 1: 'N1' }[k.jlpt_level] : '',
			k.freq ? `Freq #${k.freq}` : ''
		]
			.filter(Boolean)
			.join(' · ');
	}
</script>

<svelte:head>
	<title>{data ? `${data.label} kanji — Reikun` : 'Reikun'}</title>
</svelte:head>

<Header />
<div class="kgroup-wrap">
	<nav class="about-nav"><a href="/">← Reikun</a></nav>
	{#if !req}
		<p class="notice"><Icon name="info" size={16} /> Unknown group — pick one from any kanji card's
			badges (strokes, grade or JLPT).</p>
	{:else}
		<h1 class="kgroup-title">
			{data?.label ?? GROUPS[req.by]} kanji
			{#if data}<span class="kgroup-total">{data.total}</span>{/if}
		</h1>
		<p class="kgroup-sub">
			Every kanji with the same {GROUPS[req.by]}, frequency-ranked most-common first. Click one to
			open its full card with readings, stroke order and words.
		</p>

		{#if busy}
			<div class="kgroup-loading"><span class="spinner"></span></div>
		{:else if error}
			<p class="error-banner"><Icon name="warning" size={16} /> {error}</p>
		{:else if data}
			<div class="kg-grid">
				{#each data.kanjis as k (k.literal)}
					<a class="kg-card" href="/?q={encodeURIComponent(k.literal)}" title={`Open ${k.literal}`}>
						<span class="kg-glyph" lang="ja">{k.literal}</span>
						<span class="kg-gloss">{k.meanings[0] ?? '—'}</span>
						<span class="kg-meta">{metaLine(k)}</span>
					</a>
				{/each}
			</div>
			{#if pages > 1}
				<nav class="kg-pager" aria-label="Group pages">
					{#if pageNo > 1}<a class="btn-3d" href={pageHref(pageNo - 2)}>← Previous</a>{/if}
					<span class="kg-pager-label">Page {pageNo} of {pages}</span>
					{#if pageNo < pages}<a class="btn-3d" href={pageHref(pageNo)}>Next →</a>{/if}
				</nav>
			{/if}
		{/if}
	{/if}
</div>
<Footer />
