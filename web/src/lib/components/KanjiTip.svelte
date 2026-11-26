<script lang="ts">
	import { page } from '$app/state';
	import { building } from '$app/env';
	import { hovers, wantKanji } from '#lib/hover.svelte.ts';
	import { clampTip } from '#lib/tooltip.ts';
	import { t } from '#lib/i18n.svelte.ts';
	let { char }: { char: string } = $props();
	const uid = $props.id();
	const PIN_EVENT = 'reikun-kanji-tip-pin';

	// The back-context this tip's link threads to the kanji page: the searched
	// word on the home page (`?q=`), the kanji being viewed on a kanji page
	// (path, so the chain names the page you were just on), else `from`.
	// During prerender builds `url.searchParams` is unavailable — emit the bare
	// path there; the client re-derives with the real context on hydration.
	const ctxFrom = $derived.by(() => {
		if (building) return '';
		const u = page.url;
		const q = u.searchParams.get('q');
		if (q) return q;
		const m = u.pathname.match(/^\/kanji\/([^/?]+)/);
		if (m) return decodeURIComponent(m[1]);
		return u.searchParams.get('from') ?? '';
	});
	const kanjiHref = $derived(
		ctxFrom
			? `/kanji/${encodeURIComponent(char)}?from=${encodeURIComponent(ctxFrom)}`
			: `/kanji/${encodeURIComponent(char)}`
	);

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
	function onfocus(e: FocusEvent) {
		// Keyboard parity with hover: tabbing onto the kanji opens the tip too.
		if (anchorEl?.contains(e.target as Node)) hovered = true;
	}
	function onblur(e: FocusEvent) {
		// Focus moving into the tip's own link keeps it open.
		if (anchorEl?.contains(e.relatedTarget as Node)) return;
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
			// The other instances close themselves, so the newest pin wins.
			window.dispatchEvent(new CustomEvent(PIN_EVENT, { detail: { id: uid } }));
		}
	}

	function keyToggle(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') toggle(e);
	}

	function close() {
		pinned = false;
		hovered = false;
	}

	// One pinned tip at a time: the newest pin announces its id, and older
	// pinned instances close themselves. Listened for only while this tip is
	// showing — a hidden tip is already closed, so the broadcast has nothing
	// to tell it, and a permanent listener here would hang one window listener
	// on every rendered kanji (hundreds on large results), making every pin
	// dispatch visit each of them.
	$effect(() => {
		if (!visible) return;
		const onPin = (event: Event) => {
			if ((event as CustomEvent<{ id: string }>).detail.id !== uid) close();
		};
		window.addEventListener(PIN_EVENT, onPin);
		return () => window.removeEventListener(PIN_EVENT, onPin);
	});

	$effect(() => {
		if (!visible) return;
		const onClick = (e: MouseEvent) => {
			if (anchorEl && !anchorEl.contains(e.target as Node)) close();
		};
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') close();
		};
		window.addEventListener('click', onClick);
		window.addEventListener('keydown', onKey);
		window.addEventListener('scroll', close);
		return () => {
			window.removeEventListener('click', onClick);
			window.removeEventListener('keydown', onKey);
			window.removeEventListener('scroll', close);
		};
	});
</script>

<!-- Every kanji on the page renders one of these (hundreds on a results page), so
     the window listeners exist only while this tip is showing — not once per kanji. -->

{#snippet body()}
	<span class="kanji-tip-body" role="tooltip" id={uid}>
		<span class="big">{char}</span>
		{#if d?.meanings.length}
			<div class="tip-meanings"><b>{t('meanings')}</b> {d.meanings.join(', ')}</div>
		{/if}
		{#if d?.on_yomi.length}
			<div class="tip-readings"><span class="tip-label">{t('tipOn')}</span>{d.on_yomi.join('、')}</div>
		{/if}
		{#if d?.kun_yomi.length}
			<div class="tip-readings"><span class="tip-label">{t('tipKun')}</span>{d.kun_yomi.join('、')}</div>
		{/if}
		{#if d?.meta.length}
			<div class="tip-stroke">{d.meta.map((m) => m.label).join(' · ')}</div>
		{/if}
		<a class="tip-go" href={kanjiHref} onclick={() => close()}
			>{t('tipOpen', { char })}</a
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
		aria-label={t('tipAria', { char })}
		aria-describedby={visible ? uid : undefined}
		bind:this={anchorEl}
		{@attach clampTip}
		onpointerenter={onenter}
		onpointerleave={onleave}
		onfocus={onfocus}
		onblur={onblur}
		onclick={toggle}
		onkeydown={keyToggle}
	>
		{char}{#if visible}{@render body()}{/if}
	</span>
{:else}
	<!-- hover data still loading or failed — keep plain-link navigation -->
	<a class="kanji-tip" href={kanjiHref} onclick={() => close()} {@attach clampTip}
		>{char}</a
	>
{/if}
