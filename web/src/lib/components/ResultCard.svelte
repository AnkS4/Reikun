<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Level, SearchResult } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import ExampleRow from './ExampleRow.svelte';
	import Icon from './Icon.svelte';
	import { t, type MessageKey } from '#lib/i18n.svelte.ts';

	type Sense = SearchResult['senses'][number];

	/** Coarse POS tag → i18n key (tags are built by scripts/build_chunks.py). */
	const POS_LABEL: Record<string, MessageKey> = {
		verb: 'posVerb',
		'adj-i': 'posAdjI',
		'adj-na': 'posAdjNa',
		noun: 'posNoun',
		adv: 'posAdv',
		phrase: 'posPhrase',
		intj: 'posIntj',
		other: 'posOther'
	};
	/** Misc tags that render as badges; register/name tags stay capture-only. */
	const MISC_LABEL: Record<string, MessageKey> = {
		'on-mim': 'miscOnom',
		kana: 'miscKana',
		abbr: 'miscAbbr',
		idiom: 'miscIdiom'
	};
	/** ke_inf per-form labels → i18n keys (codes from scripts/build_chunks.py). */
	const KE_INF_LABEL: Record<string, MessageKey> = {
		sK: 'variantSearchOnly',
		rK: 'variantRare',
		oK: 'variantOldForm',
		ateji: 'variantAteji',
		io: 'variantIrregularOkurigana',
		iK: 'variantIrregularKanji',
		ik: 'variantIrregularKana'
	};

	let {
		result,
		level,
		onPickKanji,
		onSearchWord,
		active = false,
		searched = null,
		style = ''
	}: {
		result: SearchResult;
		level: Level;
		onPickKanji: (c: string) => void;
		onSearchWord?: (q: string, ref?: { seq?: string; sno?: string | null }) => void;
		active?: boolean;
		searched?: string | null;
		style?: string;
	} = $props();

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	function posTags(s: Sense): string[] {
		return (s.pos ?? []).slice(0, 3);
	}
	function miscTags(s: Sense): string[] {
		return (s.misc ?? []).filter((tag) => tag in MISC_LABEL).slice(0, 3);
	}
	function xrefAntonyms(s: Sense) {
		return (s.xrefs ?? []).filter((x) => x.type === 'ant');
	}
	function xrefSeeAlso(s: Sense) {
		return (s.xrefs ?? []).filter((x) => x.type !== 'ant').slice(0, 6);
	}
	function hasXrefs(s: Sense): boolean {
		return xrefAntonyms(s).length > 0 || xrefSeeAlso(s).length > 0;
	}

	/** Build URL for the conjugations page. */
	const conjHref = $derived.by(() => {
		const word = result.kanji_form || result.reading;
		if (!word) return '';
		const params = new URLSearchParams({ word });
		if (result.reading && result.reading !== word) params.set('reading', result.reading);
		return `/conjugations?${params}`;
	});

	/** Navigate to the conjugations page, passing pre-loaded data via state. */
	function openConj(e: MouseEvent) {
		e.preventDefault();
		if (!conjHref) return;
		goto(conjHref, { state: { conjRows: result.inflected_forms } });
	}

	// Anki / notes format: 高い【たかい】— high, tall, expensive
	const wordLine = $derived.by(() => {
		const head = result.kanji_form && result.kanji_form !== result.reading
			? `${result.kanji_form}【${result.reading}】`
			: result.reading || result.kanji_form || '';
		return `${head}— ${result.meanings.slice(0, 3).join(', ')}`;
	});

	async function copyWord() {
		try {
			await navigator.clipboard.writeText(wordLine);
			copied = true;
			clearTimeout(timer);
			timer = setTimeout(() => (copied = false), 1500);
		} catch {
			/* clipboard blocked */
		}
	}

	const senses = $derived(result.senses ?? []);
	const flatExamples = $derived(result.example_sentences ?? []);
	// Unrestricted readings apply to every written form — the primary reading
	// already sits in the headword, so only alternates earn the shared line.
	const sharedReads = $derived(
		(result.variants?.readings ?? []).filter((r) => r && r !== result.reading)
	);
	const hasExamples = $derived(
		senses.length ? senses.some((s) => (s.examples ?? []).length > 0) : flatExamples.length > 0
	);
</script>

<div class="result-card" {style} class:kbd-active={active}>
	<div class="result-head">
		<span class="headword" lang="ja"><Ruby parts={result.ruby} onpick={onPickKanji} /></span>
		{#if result.is_common}<span class="badge">{t('common')}</span>{/if}
		<button
			type="button"
			class="btn tertiary copy-word"
			title={copied ? t('copied') : t('copyAsTitle')}
			aria-label={copied ? t('copied') : t('copyWordAria')}
			onclick={copyWord}
		>
			<Icon name={copied ? 'check' : 'copy'} size={15} />
		</button>
	</div>
	{#if result.lsource?.length}
		<!-- Etymology ("From Portuguese — espada"): JMdict-authored English like
		     the glosses; the source form carries its BCP-47 lang tag. -->
		<p class="etymology">
			{#each result.lsource as src, i (src.lang + '-' + i)}{i > 0 ? '; ' : ''}{#if src.lang}<a class="etym-link" href="/loanwords?lang={encodeURIComponent(src.lang)}">{src.label}</a>{:else}{src.label}{/if}{#if src.text} — <span class="etym-src" lang={src.tag ?? undefined}>{src.text}</span>{/if}{/each}
		</p>
	{/if}
	{#if searched && result.inflection}
		<p class="inflection-bar">
			<span lang="ja">{searched}</span>
			— {t('inflectionForm', { form: result.inflection.toLowerCase() })}
		</p>
	{/if}
	{#if result.inflected_forms?.length}
		<div class="conj-section">
			<a
				class="conj-toggle"
				href={conjHref}
				onclick={openConj}
				title={t('conjugationsTitle')}
			>
				<Icon name="replace" size={12} />
				<span class="conj-label">{t('conjugations')}</span>
				<span class="conj-count">{result.inflected_forms.length}</span>
				<Icon name="arrow-right" size={12} />
			</a>
		</div>
	{/if}
	{#if senses.length}
		<!-- Per-sense blocks: each meaning keeps its own glosses, badges,
		     usage notes, cross-references and examples (JMdict scopes all of
		     these to the sense — see scripts/build_chunks.py). -->
		{#each senses as sense, si (si)}
			<div class="sense-block" id={result.id != null ? `sense-${result.id}-${si + 1}` : undefined}>
				{#if sense.glosses?.length || posTags(sense).length || miscTags(sense).length || (sense.dial ?? []).length}
					<div class="sense-line">
						{#if sense.glosses?.length}
							<p class="sense-glosses">{sense.glosses.join('; ')}</p>
						{/if}
						{#if posTags(sense).length || miscTags(sense).length || (sense.dial ?? []).length}
							<p class="sense-badges">
								{#each posTags(sense) as tag (tag)}<span class="badge pos">{t(POS_LABEL[tag] ?? 'posOther')}</span>{/each}
								{#each miscTags(sense) as tag (tag)}<span class="badge misc">{t(MISC_LABEL[tag] ?? 'miscOnom')}</span>{/each}
								{#each sense.dial ?? [] as d (d.code)}<span class="badge dial" title={t('dialect')}>{d.name}</span>{/each}
							</p>
						{/if}
					</div>
				{/if}
				{#if sense.stagk?.length || sense.stagr?.length}
					<!-- Sense-level form restrictions (JMdict stagk/stagr): this
					     meaning only applies to the listed written forms /
					     readings. -->
					<p class="sense-variants">
						{#if sense.stagk?.length}<span>{t('senseWrittenOnly', { forms: sense.stagk.join(' · ') })}</span>{/if}
						{#if sense.stagr?.length}<span>{t('senseReadOnly', { readings: sense.stagr.join(' · ') })}</span>{/if}
					</p>
				{/if}
				{#if sense.s_inf?.length}
					<p class="sense-note" lang="en">{sense.s_inf.join(' ')}</p>
				{/if}
				{#if onSearchWord && hasXrefs(sense)}
					<!-- Dictionary cross-references (JMdict xref): antonyms and
					     see-also pointers — searchable headwords carrying the
					     target entry seq + sense number for the deep link. -->
					<div class="xref-row">
						{#if xrefAntonyms(sense).length}
							<span class="xref-label">{t('antonyms')}</span>
							{#each xrefAntonyms(sense) as x (x.seq + x.sno + x.text)}
								<button
									type="button"
									class="related-pill xref-ant"
									title={t('searchWord', { word: x.text })}
									onclick={() => onSearchWord!(x.text, { seq: x.seq, sno: x.sno })}
								><span lang="ja">{x.text}{#if x.sno}<sup class="xref-sno">{x.sno}</sup>{/if}</span></button>
							{/each}
						{/if}
						{#if xrefSeeAlso(sense).length}
							<span class="xref-label">{t('seeAlso')}</span>
							{#each xrefSeeAlso(sense) as x (x.seq + x.sno + x.text)}
								<button
									type="button"
									class="related-pill"
									title={t('searchWord', { word: x.text })}
									onclick={() => onSearchWord!(x.text, { seq: x.seq, sno: x.sno })}
								><span lang="ja">{x.text}{#if x.sno}<sup class="xref-sno">{x.sno}</sup>{/if}</span></button>
							{/each}
						{/if}
					</div>
				{/if}
				{#if sense.examples?.length}
					<div class="example-section">
						{#each sense.examples as ex, i (ex.japanese + i)}
							<ExampleRow {ex} {level} onpick={onPickKanji} />
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	{:else}
		<p class="meanings-line">{result.meanings.slice(0, 6).join('; ')}</p>
		{#if flatExamples.length}
			<div class="example-section">
				{#each flatExamples.slice(0, 3) as ex, i (ex.japanese + i)}
					<ExampleRow {ex} {level} onpick={onPickKanji} />
				{/each}
			</div>
		{/if}
	{/if}
	{#if result.variants?.forms?.length}
		<!-- Variant forms: JMdict's reading→kanji bindings (re_restr /
		     re_nokanji) plus per-form ke_inf labels — which spelling goes
		     with which reading, and which spellings are search-only/rare.
		     Chips flow horizontally and click through to a search. -->
		<div class="variants">
			<p class="variants-title">{t('variantsTitle')}</p>
			<div class="variant-chips">
				{#each result.variants.forms as f (f.form)}
					{#snippet chip()}
						<span class="v-form" lang="ja">{f.form}</span>
						{#each f.labels ?? [] as l (l)}{#if KE_INF_LABEL[l]}<span class="v-tag">{t(KE_INF_LABEL[l])}</span>{/if}{/each}
						{#if f.readings?.length}<span class="v-read">— {f.readings.join(' · ')}</span>{/if}
					{/snippet}
					{#if onSearchWord}
						<button
							type="button"
							class="variant-chip"
							title={t('searchWord', { word: f.form })}
							onclick={() => onSearchWord!(f.form)}
						>{@render chip()}</button>
					{:else}
						<span class="variant-chip">{@render chip()}</span>
					{/if}
				{/each}
				{#if sharedReads.length}
					<span class="variant-note">{t('variantReadAs')}</span>
					{#each sharedReads as r (r)}
						{#if onSearchWord}
							<button
								type="button"
								class="variant-chip v-read-chip"
								lang="ja"
								title={t('searchWord', { word: r })}
								onclick={() => onSearchWord!(r)}
							>{r}</button>
						{:else}
							<span class="variant-chip v-read-chip" lang="ja">{r}</span>
						{/if}
					{/each}
				{/if}
				{#if result.variants.kana_only?.length}
					<span class="variant-note">{t('variantKanaOnly')}</span>
					{#each result.variants.kana_only as r (r)}
						{#if onSearchWord}
							<button
								type="button"
								class="variant-chip v-read-chip"
								lang="ja"
								title={t('searchWord', { word: r })}
								onclick={() => onSearchWord!(r)}
							>{r}</button>
						{:else}
							<span class="variant-chip v-read-chip" lang="ja">{r}</span>
					{/if}
					{/each}
				{/if}
			</div>
		</div>
	{/if}
	{#if onSearchWord && result.related?.length}
		<div class="related-row" aria-label={t('relatedWords')}>
			{#each result.related as w, i ((w.kanji_form || w.reading) + (w.reading ?? '') + i)}
				<button
					type="button"
					class="related-pill"
					title={t('searchWord', { word: w.kanji_form || w.reading })}
					onclick={() => onSearchWord(w.kanji_form || w.reading)}
				>
					<span lang="ja"><Ruby parts={w.ruby} tips={false} /></span>
					<span class="related-gloss">{w.gloss}</span>
				</button>
			{/each}
		</div>
	{/if}
	{#if !hasExamples}
		<p class="no-example">{t('noExamples')}</p>
	{/if}
</div>
