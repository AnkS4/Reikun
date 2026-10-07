<script lang="ts">
	import { hovers, wantKanji } from '#lib/hover.svelte.ts';
	import { clampTip } from '#lib/tooltip.ts';
	let { char, onpick }: { char: string; onpick?: (char: string) => void } = $props();

	$effect(() => wantKanji([char]));
	const d = $derived(hovers.get(char));

	let hovered = $state(false);
	let pinned = $state(false);
	const visible = $derived(hovered || pinned);
	let anchorEl = $state<HTMLElement>();

	function onenter() {
		hovered = true;
	}
	function onleave() {
		hovered = false;
	}
	function toggle(e: Event) {
		// Clicks inside the open tip (selecting text, hitting "Search →")
		// mustn't toggle — the char itself is the toggle surface.
		if ((e.target as HTMLElement).closest('.kanji-tip-body')) return;
		e.preventDefault();
		e.stopPropagation();
		if (pinned) {
			pinned = false;
			hovered = false;
		} else {
			pinned = true;
		}
	}

	function keyToggle(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') toggle(e);
	}

	function pick(e: MouseEvent) {
		if (onpick) {
			e.preventDefault();
			e.stopPropagation();
			pinned = false;
			hovered = false;
			onpick(char);
		} else {
			pinned = false;
			hovered = false;
		}
	}

	function close() {
		pinned = false;
		hovered = false;
	}
</script>

<svelte:window
	onclick={(e) => {
		if (pinned && anchorEl && !anchorEl.contains(e.target as Node)) close();
	}}
	onkeydown={(e) => {
		if (pinned && e.key === 'Escape') close();
	}}
	onscroll={close}
/>

{#snippet body()}
	<span class="kanji-tip-body" role="tooltip">
		<span class="big">{char}</span>
		{#if d?.meanings.length}
			<div class="tip-meanings"><b>Meanings</b> {d.meanings.join(', ')}</div>
		{/if}
		{#if d?.on_yomi.length}
			<div class="tip-readings"><span class="tip-label">On</span>{d.on_yomi.join('、')}</div>
		{/if}
		{#if d?.kun_yomi.length}
			<div class="tip-readings"><span class="tip-label">Kun</span>{d.kun_yomi.join('、')}</div>
		{/if}
		{#if d?.meta.length}
			<div class="tip-stroke">{d.meta.map((m) => m.label).join(' · ')}</div>
		{/if}
		<a class="tip-go" href="/?q={encodeURIComponent(char)}" onclick={pick}
			>Search {char} →</a
		>
	</span>
{/snippet}

{#if d}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex a11y_no_noninteractive_element_interactions -->
	<span
		class="kanji-tip"
		class:pinned
		role="button"
		tabindex="0"
		aria-expanded={pinned}
		aria-label="Kanji {char} details"
		bind:this={anchorEl}
		use:clampTip
		onpointerenter={onenter}
		onpointerleave={onleave}
		onclick={toggle}
		onkeydown={keyToggle}
	>
		{char}{#if visible}{@render body()}{/if}
	</span>
{:else if onpick}
	<!-- hover data still loading/failed — keep plain-link navigation -->
	<a class="kanji-tip" href="/?q={encodeURIComponent(char)}" onclick={pick} use:clampTip
		>{char}</a
	>
{:else}
	{char}
{/if}
