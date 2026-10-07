<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from '#lib/icons.ts';
	import type { Snippet } from 'svelte';
	let {
		icon,
		label = '',
		title = '',
		children
	}: { icon?: IconName; label?: string; title?: string; children: Snippet } = $props();
	let open = $state(false);
	let wrap = $state<HTMLDivElement>();
</script>

<svelte:window
	onkeydown={(e) => {
		if (open && e.key === 'Escape') open = false;
	}}
	onclick={(e) => {
		if (open && wrap && !wrap.contains(e.target as Node)) open = false;
	}}
/>

<div class="popover-wrap" bind:this={wrap}>
	<button
		type="button"
		class="btn tertiary"
		{title}
		aria-label={title || label || undefined}
		onclick={() => (open = !open)}
		aria-expanded={open}
	>
		{#if icon}<Icon name={icon} size={15} />{/if}
		{#if label}<span class="level-indicator">{label}</span>{/if}
	</button>
	{#if open}
		<div class="popover-panel" role="dialog">
			{@render children()}
		</div>
	{/if}
</div>
