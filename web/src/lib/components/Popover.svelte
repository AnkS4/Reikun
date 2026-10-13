<script lang="ts">
	import Icon from './Icon.svelte';
	import type { IconName } from '#lib/icons.ts';
	import type { Snippet } from 'svelte';
	let {
		icon,
		label = '',
		title = '',
		buttonClass = '',
		children
	}: { icon?: IconName; label?: string; title?: string; buttonClass?: string; children: Snippet } = $props();
	let open = $state(false);
	let wrap = $state<HTMLDivElement>();
	let trigger = $state<HTMLButtonElement>();
	let panel = $state<HTMLDivElement>();
	const panelId = $props.id();

	function close(returnFocus = false) {
		open = false;
		if (returnFocus) trigger?.focus();
	}

	// Keyboard users land inside the panel (the selected option if there is one).
	$effect(() => {
		if (!open) return;
		panel?.querySelector<HTMLElement>('.sel, button, [href], input')?.focus();
	});
</script>

<svelte:window
	onkeydown={(e) => {
		if (open && e.key === 'Escape') close(true);
	}}
	onclick={(e) => {
		if (open && wrap && !wrap.contains(e.target as Node)) close();
	}}
/>

<!-- focusout: tabbing past the panel closes it instead of leaving it open behind the page -->
<div
	class="popover-wrap"
	bind:this={wrap}
	onfocusout={(e) => {
		if (open && !wrap?.contains(e.relatedTarget as Node | null)) close();
	}}
>
	<button
		type="button"
		class="btn {buttonClass || 'tertiary'}"
		{title}
		aria-label={label ? `${title}: ${label}` : title || undefined}
		onclick={() => (open = !open)}
		aria-expanded={open}
		aria-haspopup="dialog"
		aria-controls={open ? panelId : undefined}
		bind:this={trigger}
	>
		{#if icon}<Icon name={icon} size={15} />{/if}
		{#if label}<span class="level-indicator">{label}</span>{/if}
	</button>
	{#if open}
		<div class="popover-panel" role="dialog" aria-label={title || undefined} id={panelId} bind:this={panel}>
			{@render children()}
		</div>
	{/if}
</div>
