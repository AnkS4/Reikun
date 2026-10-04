<script lang="ts">
	import Icon from './Icon.svelte';
	import type { Snippet } from 'svelte';
	let {
		icon = '',
		label = '',
		title = '',
		children
	}: { icon?: string; label?: string; title?: string; children: Snippet } = $props();
	let open = $state(false);
</script>

<div class="popover-wrap">
	<button type="button" class="btn tertiary" {title} onclick={() => (open = !open)} aria-expanded={open}>
		{#if icon}<Icon name={icon} />{/if}{label}
	</button>
	{#if open}
		<button type="button" class="popover-backdrop" aria-label="Close" onclick={() => (open = false)} tabindex="-1"
		></button>
		<div class="popover-panel" role="dialog">
			{@render children()}
		</div>
	{/if}
</div>
