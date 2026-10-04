<script lang="ts">
	import type { Segment } from '#lib/api.ts';
	import Ruby from './Ruby.svelte';
	import { isKanji } from '#lib/kanji.ts';
	let { segments }: { segments: Segment[] } = $props();
	const approx = $derived(segments.some((s) => s.approx));

	function tip(s: Segment): string {
		const t = s.options.length
			? s.options.join(' / ')
			: [
					s.kanji_form && s.kanji_form !== s.text ? s.kanji_form : '',
					s.reading && s.reading !== s.text ? s.reading : '',
					s.meanings.slice(0, 3).join('; ')
				]
					.filter(Boolean)
					.join(' · ');
		return s.approx ? (t ? `approximate — ${t}` : 'approximate') : t;
	}
</script>

<p class="caption">
	Parsed — {approx ? 'approximate split (fallback segmenter);' : 'reading above, meaning below;'}
	hover for detail
</p>
<div class="seg-row">
	{#each segments as s}
		<span class="seg" class:approx={s.approx} title={tip(s)}>
			<span class="seg-word"><Ruby parts={s.ruby} tips={false} /></span>
			<span class="seg-mean">{s.gloss}</span>
		</span>
	{/each}
</div>
