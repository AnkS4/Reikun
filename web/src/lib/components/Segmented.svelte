<script lang="ts" generics="T extends string">
	let {
		options,
		value,
		onchange,
		label
	}: { options: readonly T[]; value: T; onchange: (v: T) => void; label?: string } = $props();
</script>

<div class="segmented" role="group" aria-label={label}>
	{#each options as o}
		<button type="button" class:sel={o === value} onclick={() => onchange(o)}>{o}</button>
	{/each}
</div>
