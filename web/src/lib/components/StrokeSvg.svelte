<script lang="ts">
	import type { StrokeData } from '#lib/api.ts';
	import Icon from './Icon.svelte';
	import { t } from '#lib/i18n.svelte.ts';
	let { stroke }: { stroke: StrokeData } = $props();
	let replay = $state(0);
	const STEP = 0.75; // delay between consecutive strokes — matches draw duration, strictly sequential
	const SPEED = 50; // pixels per second for consistent drawing speed

	// Calculate stroke lengths and durations for consistent drawing speed
	const strokeInfo = $derived.by(() => {
		const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.setAttribute('viewBox', stroke.view_box);
		const paths = stroke.strokes.map((d) => {
			const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
			path.setAttribute('d', d);
			svg.appendChild(path);
			const length = path.getTotalLength();
			svg.removeChild(path);
			return {
				length,
				duration: length / SPEED
			};
		});
		return paths;
	});

	// Pre-compute animation-delay strings based on cumulative durations
	const strokeDelays = $derived.by(() => {
		let cumulative = 0;
		return strokeInfo.map((info, i) => {
			const delay = cumulative.toFixed(2);
			cumulative += info.duration;
			return `${delay}s`;
		});
	});

	const strokeDurations = $derived(strokeInfo.map((info) => `${info.duration.toFixed(2)}s`));

	// Numbers appear with their corresponding stroke
	const numberDelays = $derived(strokeDelays);
</script>

<div class="stroke-svg" class:pa={replay % 2 === 0} class:pb={replay % 2 === 1}>
	<button
		type="button"
		class="stroke-replay"
		title={t('replayStroke')}
		aria-label={t('replayStroke')}
		onclick={() => replay++}
	>
		<Icon name="replay" size={14} />
	</button>
	<svg viewBox={stroke.view_box} xmlns="http://www.w3.org/2000/svg" role="img" aria-label={t('strokeDiagram')}>
		{#each stroke.strokes as d, i (i)}
			<path
				{d}
				pathLength="100"
				style="animation-delay:{strokeDelays[i]}; animation-duration:{strokeDurations[i]}"
			></path>
		{/each}
		{#each stroke.numbers as n, i (i)}
			<text x={n.x} y={n.y} style="animation-delay:{numberDelays[i]}">{n.value}</text>
		{/each}
	</svg>
</div>
