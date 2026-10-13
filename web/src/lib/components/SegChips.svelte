<script lang="ts">
	import type { Segment } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import { clampTip } from '#lib/tooltip.ts';
	let {
		segments,
		onjump
	}: {
		segments: Segment[];
		onjump?: (segment: Segment, index: number) => void;
	} = $props();
	const approx = $derived(segments.some((s) => s.approx));

	function tip(s: Segment): string {
		const t = s.options.length
			? s.options.join(' / ')
			: [
					s.kanji_form && s.kanji_form !== s.text ? s.kanji_form : '',
					s.reading && s.reading !== s.text ? s.reading : '',
					s.meanings.slice(0, 3).join('; ')
				]
				.filter(Boolean)
				.join(' · ');
		return s.approx ? (t ? `approximate — ${t}` : 'approximate') : t;
	}

	let hovered = $state(-1);

	function onenter(i: number) {
		hovered = i;
	}
	function onleave(i: number) {
		if (hovered === i) hovered = -1;
	}
	function handleClick(s: Segment, i: number) {
		hovered = -1;
		onjump?.(s, i);
	}
	function handleKey(s: Segment, i: number, e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleClick(s, i);
		}
	}
	function close() {
		hovered = -1;
	}
</script>

<svelte:window
	onscroll={close}
	onkeydown={(e) => {
		if (e.key === 'Escape') close();
	}}
/>

<div class="seg-card">
	<div class="seg-header">
		<p class="seg-title">
			<span>Sentence Breakdown</span>
			{#if approx}
				<span class="meta-badge" title="Fallback segmenter used">Approximate</span>
			{/if}
		</p>
		<span class="stats-meta">Hover for definitions · Click to view entry</span>
	</div>
	<div class="seg-row">
		{#each segments as s, i (s.text + i)}
			{@const t = tip(s)}
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions — role=button + Enter/Space handled in handleKey -->
			<span
				class="seg"
				class:approx={s.approx}
				class:open={hovered === i}
				role="button"
				tabindex="0"
				title="Jump to {s.kanji_form || s.reading || s.text}"
				use:clampTip
				onpointerenter={() => onenter(i)}
				onpointerleave={() => onleave(i)}
				onclick={() => handleClick(s, i)}
				onkeydown={(e) => handleKey(s, i, e)}
			>
				<span class="seg-word" lang="ja"><Ruby parts={s.ruby} tips={false} /></span>
				<span class="seg-mean">{s.gloss}</span>
				{#if hovered === i && t}<span class="seg-tip" role="tooltip">{t}</span>{/if}
			</span>
		{/each}
	</div>
</div>
