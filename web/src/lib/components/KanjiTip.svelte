<script lang="ts">
	import { hovers, wantKanji } from '#lib/hover.svelte.ts';
	let { char, onpick }: { char: string; onpick?: (char: string) => void } = $props();

	$effect(() => wantKanji([char]));
	const d = $derived(hovers.get(char));

	function pick(e: MouseEvent) {
		e.preventDefault();
		onpick?.(char);
	}
</script>

{#snippet body()}
	<span class="kanji-tip-body">
		<span class="big">{char}</span>
		{#if d?.meanings.length}
			<div class="tip-meanings"><b>Meanings</b> {d.meanings.join(', ')}</div>
		{/if}
		{#if d?.on_yomi.length}
			<div class="tip-readings"><span class="tip-label">On</span>{d.on_yomi.join('、')}</div>
		{/if}
		{#if d?.kun_yomi.length}
			<div class="tip-readings"><span class="tip-label">Kun</span>{d.kun_yomi.join('、')}</div>
		{/if}
		{#if d?.meta.length}
			<div class="tip-stroke">{d.meta.map((m) => m.label).join(' · ')}</div>
		{/if}
	</span>
{/snippet}

{#if onpick}
	<a class="kanji-tip" href="/?q={encodeURIComponent(char)}" onclick={pick}
		>{char}{#if d}{@render body()}{/if}</a
	>
{:else if d}
	<!-- svelte-ignore a11y_no_noninteractive_tabindex — focusable so keyboard/touch users can open the tip -->
	<span class="kanji-tip" tabindex="0">{char}{@render body()}</span>
{:else}
	{char}
{/if}
