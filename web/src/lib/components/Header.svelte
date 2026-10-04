<script lang="ts">
	import { onMount } from 'svelte';
	import { apiReady } from '#lib/api.ts';
	import { theme, type ThemeChoice } from '#lib/theme.svelte.ts';
	import KanjiText from './KanjiText.svelte';
	import Popover from './Popover.svelte';
	import Segmented from './Segmented.svelte';
	import Icon from './Icon.svelte';

	let { hero = false, tagline = '' }: { hero?: boolean; tagline?: string } = $props();

	let status = $state<{ ok: boolean; msg: string } | null>(null);
	onMount(() => {
		apiReady()
			.then((r) => (status = { ok: true, msg: `${r.entries.toLocaleString()} entries indexed` }))
			.catch((e) => (status = { ok: false, msg: e instanceof Error ? e.message : 'API unreachable' }));
	});

	const THEME_OPTIONS: { v: ThemeChoice; label: string }[] = [
		{ v: 'system', label: 'System' },
		{ v: 'light', label: 'Light' },
		{ v: 'dark', label: 'Dark' }
	];
</script>

<div class="header-bar">
	<div class="header-title">
		{#if hero}
			<div class="hero">
				<div class="title-heading hero-heading" role="heading" aria-level="1">
					<a class="title-home" href="/" title="Back to search">Reikun</a>
					(<KanjiText text="例訓" />)
				</div>
				{#if tagline}<p class="tagline">{tagline}</p>{/if}
			</div>
		{:else}
			<div class="title-heading compact-title" role="heading" aria-level="1">
				<a class="title-home" href="/" title="Back to search">Reikun</a>
				(<KanjiText text="例訓" />)
			</div>
		{/if}
	</div>
	<div class="header-controls">
		<span
			class="status-dot"
			class:ok={status?.ok}
			class:err={status && !status.ok}
			title={status ? status.msg : 'Connecting to the API…'}
		>
			<Icon name="database" size={16} />
		</span>
		<Popover icon="palette" title="Theme">
			<p class="popover-title">Theme</p>
			<div class="segmented" role="group" aria-label="Theme">
				{#each THEME_OPTIONS as t}
					<button class:sel={theme.choice === t.v} onclick={() => theme.set(t.v)}>{t.label}</button>
				{/each}
			</div>
		</Popover>
	</div>
</div>
