<script lang="ts">
	import type { StrokeData } from '#lib/api.ts';
	import Icon from './Icon.svelte';
	let { stroke }: { stroke: StrokeData } = $props();
	let replay = $state(0);
	const STEP = 0.5; // delay between consecutive strokes (ui/common.py)
</script>

<div class="stroke-svg" class:pa={replay % 2 === 0} class:pb={replay % 2 === 1}>
	<button
		class="stroke-replay"
		title="Replay the stroke-order animation"
		aria-label="Replay the stroke-order animation"
		onclick={() => replay++}
	>
		<Icon name="replay" size={14} />
	</button>
	<svg viewBox={stroke.view_box} xmlns="http://www.w3.org/2000/svg">
		{#each stroke.strokes as d, i}
			<path {d} pathLength="100" style="animation-delay:{(i * STEP).toFixed(2)}s"></path>
		{/each}
		{#each stroke.numbers as n, i}
			<text x={n.x} y={n.y} style="animation-delay:{(i * STEP).toFixed(2)}s">{n.value}</text>
		{/each}
	</svg>
</div>
