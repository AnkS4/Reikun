<script lang="ts">
	import type { StrokeData } from '#lib/api.ts';
	import Icon from './Icon.svelte';
	let { stroke }: { stroke: StrokeData } = $props();
	let replay = $state(0);
	const STEP = 0.75; // delay between consecutive strokes — matches draw duration, strictly sequential

	// Pre-compute animation-delay strings once per stroke/number set change,
	// rather than recalculating on every render cycle. Numbers lead by one beat
	// — each label fades in during the previous stroke so it's fully visible
	// before its own stroke begins.
	const strokeDelays = $derived(stroke.strokes.map((_, i) => `${(i * STEP).toFixed(2)}s`));
	const numberDelays = $derived(stroke.numbers.map((_, i) => `${(Math.max(0, i - 1) * STEP).toFixed(2)}s`));
</script>

<div class="stroke-svg" class:pa={replay % 2 === 0} class:pb={replay % 2 === 1}>
	<button
		type="button"
		class="stroke-replay"
		title="Replay the stroke-order animation"
		aria-label="Replay the stroke-order animation"
		onclick={() => replay++}
	>
		<Icon name="replay" size={14} />
	</button>
	<svg viewBox={stroke.view_box} xmlns="http://www.w3.org/2000/svg">
		{#each stroke.strokes as d, i (i)}
			<path {d} pathLength="100" style="animation-delay:{strokeDelays[i]}"></path>
		{/each}
		{#each stroke.numbers as n, i (i)}
			<text x={n.x} y={n.y} style="animation-delay:{numberDelays[i]}">{n.value}</text>
		{/each}
	</svg>
</div>
