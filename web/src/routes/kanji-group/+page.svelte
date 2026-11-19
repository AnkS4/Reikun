<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import {
		apiKanjiGroup,
		apiKanjiGroups,
		type GroupKey,
		type KanjiGroupResponse,
		type KanjiGroupsResponse
	} from '#lib/api.ts';
	import Header from '#lib/components/Header.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { formatNumber, t } from '#lib/i18n.svelte.ts';

	// One page of the grid; eight columns of six rows on desktop, and the
	// API cap keeps a foulest-offset request from doing more work than this.
	const PAGE_SIZE = 48;

	const fromWord = $derived(page.url.searchParams.get('from') ?? '');

	// Validated request descriptor — anything unrecognized renders the
	// picker (no/invalid `by` → category chips, `by` without a usable
	// `value` → value chips) instead of a fetch.
	const byParam = $derived.by((): GroupKey | null => {
		const raw = page.url.searchParams.get('by');
		return raw === 'strokes' || raw === 'grade' || raw === 'jlpt' ? raw : null;
	});
	const valueParam = $derived.by(() => {
		const value = Number(page.url.searchParams.get('value') ?? NaN);
		return Number.isInteger(value) && value >= 1 && value <= 50 ? value : null;
	});
	const pageParam = $derived.by(() => {
		const pageNo = Number(page.url.searchParams.get('page') ?? 0);
		return Number.isInteger(pageNo) && pageNo >= 0 ? pageNo : null;
	});
	let req = $derived.by((): { by: GroupKey; value: number; skip: number } | null => {
		if (!byParam || valueParam === null || pageParam === null) return null;
		return { by: byParam, value: valueParam, skip: pageParam * PAGE_SIZE };
	});

	let data = $state.raw<KanjiGroupResponse | null>(null);
	let facets = $state.raw<KanjiGroupsResponse | null>(null);
	let facetsError = $state('');
	let busy = $state(false);
	let error = $state('');

	// The value picker needs the facet list (values + counts) — fetch it
	// only while a `by` is chosen but no grid request is possible.
	$effect(() => {
		const needs = byParam !== null && req === null;
		facets = null;
		facetsError = '';
		if (!needs) return;
		let dropped = false;
		apiKanjiGroups()
			.then((d) => {
				if (!dropped) facets = d;
			})
			.catch((e) => {
				if (!dropped) facetsError = e instanceof Error ? e.message : t('groupLoadFailed');
			});
		return () => {
			dropped = true;
		};
	});

	$effect(() => {
		const r = req;
		data = null;
		error = '';
		if (!r) {
			busy = false;
			return;
		}
		// Stale-response guard: a fast click from page N to N+1 must not let
		// the slower page-N response overwrite the newer one (the out-of-order
		// grid used to render under the newer page's pagination state).
		let dropped = false;
		busy = true;
		apiKanjiGroup(r.by, r.value, PAGE_SIZE, r.skip)
			.then((d) => {
				if (dropped) return;
				data = d;
			})
			.catch((e) => {
				if (dropped) return;
				error = e instanceof Error ? e.message : t('groupLoadFailed');
			})
			.finally(() => {
				if (!dropped) busy = false;
			});
		return () => {
			dropped = true;
		};
	});

	const pageNo = $derived(req ? Math.floor(req.skip / PAGE_SIZE) + 1 : 0);
	const pages = $derived(data ? Math.ceil(data.total / PAGE_SIZE) : 0);

	// Pagination navigates via ?page= so every page is a real entry in the
	// session history (an explicit URL the back button undoes).
	function pageHref(p: number): string {
		const fromParam = fromWord ? `&from=${encodeURIComponent(fromWord)}` : '';
		return `/kanji-group?by=${req?.by}&value=${req?.value}&page=${p}${fromParam}`;
	}

	function goBack() {
		if (typeof window !== 'undefined' && window.history.length > 1) {
			window.history.back();
		} else if (fromWord) {
			goto(`/?q=${encodeURIComponent(fromWord)}`);
		} else {
			goto('/');
		}
	}

	// Cards carry this group page as the next back-context: `from` is the
	// group's display label, `gq` a copy of this page's params so the kanji
	// page's back fallback returns here verbatim (pagination included).
	const gq = $derived.by(() => {
		if (!req) return '';
		const p = new URLSearchParams({ by: req.by, value: String(req.value) });
		if (pageNo > 1) p.set('page', String(pageNo - 1));
		if (fromWord) p.set('from', fromWord);
		return encodeURIComponent(p.toString());
	});

	function groupLabel(by: GroupKey): string {
		return t(by === 'jlpt' ? 'jlpt' : by);
	}

	// Picker chip label for one facet value — stroke counts and grades are
	// localized counts, JLPT maps the internal 4→1 scale to N-levels.
	function valueLabel(by: GroupKey, v: number): string {
		if (by === 'strokes') return t('strokesCount', { n: formatNumber(v) });
		if (by === 'grade') return t('gradeCount', { n: formatNumber(v) });
		return { 4: 'N5', 3: 'N4', 2: 'N2-N3', 1: 'N1' }[v] ?? `N${v}`;
	}

	// Title-case browse label per grouping — the same strings the homepage
	// tiles use, so picker headings match ("Strokes", "JLPT Level").
	const BROWSE_KEY = {
		strokes: 'browseStrokes',
		grade: 'browseGrade',
		jlpt: 'jlptLevel'
	} as const;
	function browseLabel(by: GroupKey): string {
		return t(BROWSE_KEY[by]);
	}
	function cap(s: string): string {
		return s ? s[0].toUpperCase() + s.slice(1) : s;
	}

	function metaLine(k: KanjiGroupResponse['kanjis'][number]): string {
		return [
			k.stroke_count ? t('strokesCount', { n: formatNumber(k.stroke_count) }) : '',
			k.jlpt_level ? { 4: 'N5', 3: 'N4', 2: 'N2-N3', 1: 'N1' }[k.jlpt_level] : '',
			k.freq ? t('freq', { n: formatNumber(k.freq) }) : ''
		]
			.filter(Boolean)
			.join(' · ');
	}
</script>

<svelte:head>
	<title>
		{req ? `${valueLabel(req.by, req.value)} ${t('kanjiSuffix')} — Reikun` : 'Reikun'}
	</title>
</svelte:head>

<Header />
<div class="kgroup-wrap">
	{#if !req}
		{#if byParam}
			<!-- Value picker: `?by=X` without a usable value lists every
			     available value as a card with its kanji count, in the same
			     grid the results use. -->
			<h1 class="kgroup-title">{browseLabel(byParam)} {cap(t('kanjiSuffix'))}</h1>
			<p class="kgroup-sub">{t('pickValueSub', { group: groupLabel(byParam) })}</p>
			{#if facets}
				<div class="kg-grid">
					{#each facets[byParam] ?? [] as v (v.value)}
						<a class="kg-card kv-card" href="/kanji-group?by={byParam}&value={v.value}">
							<span class="kv-value">{valueLabel(byParam, v.value)}</span>
							<span class="kg-meta">{formatNumber(v.count)} {t('kanjiSuffix')}</span>
						</a>
					{/each}
				</div>
			{:else if facetsError}
				<p class="error-banner"><Icon name="warning" size={18} /> {facetsError}</p>
			{:else}
				<div class="kgroup-loading"><span class="spinner"></span></div>
			{/if}
		{:else}
			<!-- Category picker: bare /kanji-group (or a bad `by`) offers the
			     three kanji groupings as the same tiles the homepage uses. -->
			<h1 class="kgroup-title">{t('browseKanji')}</h1>
			<p class="kgroup-sub">{t('pickGroupSub')}</p>
			<div class="browse-grid pick-grid">
				<a class="browse-tile" href="/kanji-group?by=strokes">
					<span class="browse-icon"><Icon name="pen-line" size={22} /></span>
					<span class="browse-name">{t('browseStrokes')}</span>
					<span class="browse-desc">{t('browseStrokesDesc')}</span>
				</a>
				<a class="browse-tile" href="/kanji-group?by=grade">
					<span class="browse-icon"><Icon name="school" size={22} /></span>
					<span class="browse-name">{t('browseGrade')}</span>
					<span class="browse-desc">{t('browseGradeDesc')}</span>
				</a>
				<a class="browse-tile" href="/kanji-group?by=jlpt">
					<span class="browse-icon"><Icon name="award" size={22} /></span>
					<span class="browse-name">{t('jlptLevel')}</span>
					<span class="browse-desc">{t('browseJlptDesc')}</span>
				</a>
			</div>
		{/if}
	{:else}
		<h1 class="kgroup-title">
			{valueLabel(req.by, req.value)} {t('kanjiSuffix')}
			{#if data}<span class="kgroup-total">{formatNumber(data.total)}</span>{/if}
		</h1>
		<p class="kgroup-sub">
			{t('groupSubtitle', { group: groupLabel(req.by) })}
		</p>

		{#if busy}
			<div class="kgroup-loading"><span class="spinner"></span></div>
		{:else if error}
			<p class="error-banner"><Icon name="warning" size={18} /> {error}</p>
		{:else if data}
			<div class="kg-grid">
				{#each data.kanjis as k (k.literal)}
					<a
					class="kg-card"
					href="/kanji/{encodeURIComponent(k.literal)}?from={encodeURIComponent(valueLabel(req.by, req.value))}&gq={gq}"
					title={t('openKanji', { char: k.literal })}
				>
						<span class="kg-glyph" lang="ja">{k.literal}</span>
						<span class="kg-gloss">{k.meanings[0] ?? '—'}</span>
						<span class="kg-meta">{metaLine(k)}</span>
					</a>
				{/each}
			</div>
			{#if pages > 1}
				<nav class="kg-pager" aria-label={t('groupPages')}>
					{#if pageNo > 1}<a class="btn-3d" href={pageHref(pageNo - 2)}>{t('previous')}</a>{/if}
					<span class="kg-pager-label">{t('pageOf', { page: formatNumber(pageNo), pages: formatNumber(pages) })}</span>
					{#if pageNo < pages}<a class="btn-3d" href={pageHref(pageNo)}>{t('next')}</a>{/if}
				</nav>
			{/if}

			<div class="kgroup-bottom-actions">
				<button type="button" class="btn-3d" onclick={goBack}>
					← {#if fromWord}{t('backTo', { word: fromWord })}{:else}{t('backPrevious')}{/if}
				</button>
			</div>
		{/if}
	{/if}
</div>
