<script lang="ts">
	import type { Segment } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import { clampTip } from '#lib/tooltip.ts';
	let { segments }: { segments: Segment[] } = $props();
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
	let pinned = $state(-1);
	const active = $derived(pinned >= 0 ? pinned : hovered);

	function onenter(i: number) {
		hovered = i;
	}
	function onleave(i: number) {
		if (hovered === i) hovered = -1;
	}
	function toggle(i: number, e: Event) {
		if ((e.target as HTMLElement).closest('.seg-tip')) {
			e.stopPropagation();
			return;
		}
		e.stopPropagation();
		if (pinned === i) {
			pinned = -1;
			hovered = -1;
		} else {
			pinned = i;
		}
	}
	function keyToggle(i: number, e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') toggle(i, e);
	}
	function close() {
		pinned = -1;
		hovered = -1;
	}
</script>

<svelte:window
	onclick={close}
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
		<span class="stats-meta">Tap or hover chips for readings & definitions</span>
	</div>
	<div class="seg-row">
		{#each segments as s, i (s.text + i)}
			{@const t = tip(s)}
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions — role=button + Enter/Space handled in keyToggle -->
			<span
				class="seg"
				class:approx={s.approx}
				class:open={active === i}
				role="button"
				tabindex="0"
				use:clampTip
				onpointerenter={() => onenter(i)}
				onpointerleave={() => onleave(i)}
				onclick={(e) => toggle(i, e)}
				onkeydown={(e) => keyToggle(i, e)}
			>
				<span class="seg-word"><Ruby parts={s.ruby} tips={false} /></span>
				<span class="seg-mean">{s.gloss}</span>
				{#if active === i && t}<span class="seg-tip" role="tooltip">{t}</span>{/if}
			</span>
		{/each}
	</div>
</div>
