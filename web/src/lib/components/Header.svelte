<script module lang="ts">
	import type { ThemeChoice } from '#lib/theme.svelte.ts';

	const THEME_OPTIONS: { v: ThemeChoice; label: string }[] = [
		{ v: 'system', label: 'System' },
		{ v: 'light', label: 'Light' },
		{ v: 'dark', label: 'Dark' },
		{ v: 'oled', label: 'OLED' }
	];
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import { apiReady } from '#lib/api.ts';
	import { theme } from '#lib/theme.svelte.ts';
	import KanjiText from './KanjiText.svelte';
	import Popover from './Popover.svelte';
	import Icon from './Icon.svelte';

	let { hero = false, tagline = '' }: { hero?: boolean; tagline?: string } = $props();

	let status = $state<{ ok: boolean; entries: number | null; msg: string } | null>(null);
	onMount(() => {
		apiReady()
			.then((r) => (status = { ok: true, entries: r.entries, msg: 'Ready' }))
			.catch((e) =>
				(status = { ok: false, entries: null, msg: e instanceof Error ? e.message : 'API unreachable' })
			);
	});
</script>

<div class="header-controls">
	<span
		class="status-dot"
		class:ok={status?.ok}
		class:err={status && !status.ok}
		aria-label={status ? (status.ok ? `Dictionary ready — ${status.entries?.toLocaleString()} entries` : `Dictionary offline — ${status.msg}`) : 'Connecting to the dictionary…'}
	>
		<Icon name="database" size={15} />
		<span class="status-pop" role="tooltip">
			<span class="popover-title">Dictionary status</span>
			{#if status === null}
				<span class="status-line"><span class="status-mark"></span>Connecting…</span>
				<span class="status-sub">Waking up the dictionary</span>
			{:else if status.ok}
				<span class="status-line"><span class="status-mark ok"></span>Connected</span>
				<span class="status-sub">{status.entries?.toLocaleString()} words and phrases ready to search</span>
			{:else}
				<span class="status-line"><span class="status-mark err"></span>Offline</span>
				<span class="status-sub">Couldn't reach the dictionary — {status.msg}</span>
			{/if}
		</span>
	</span>
	<Popover icon="palette" title="Theme">
		<p class="popover-title">Appearance</p>
		<div class="segmented" role="group" aria-label="Theme">
			{#each THEME_OPTIONS as t (t.v)}
				<button type="button" class:sel={theme.choice === t.v} onclick={() => theme.set(t.v)}>{t.label}</button>
			{/each}
		</div>
	</Popover>
</div>

<div class="header-bar">
	<div class="header-title" class:hero>
		{#if hero}
			<div class="hero-badge-tag">
				<Icon name="languages" size={13} />
				<span>Japanese Dictionary</span>
			</div>
		{/if}
		<h1 class="title-heading" class:hero-heading={hero} class:compact-title={!hero}>
			<a class="title-home" href="/" title="Back to search">Reikun</a>
			<span class="brand-kanji">(<KanjiText text="例訓" />)</span>
		</h1>
		{#if hero && tagline}<p class="tagline">{tagline}</p>{/if}
	</div>
</div>
