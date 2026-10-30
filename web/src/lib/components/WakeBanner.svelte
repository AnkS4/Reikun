<script lang="ts">
	import { backend } from '#lib/backend.svelte.ts';
	import { apiWake } from '#lib/api.ts';
	import { t } from '#lib/i18n.svelte.ts';
	import Icon from './Icon.svelte';

	const waking = $derived(backend.state === 'waking');
	const down = $derived(backend.state === 'down');

	function retry() {
		apiWake().catch(() => {});
	}
</script>

<!-- The live region is always mounted: screen readers only announce changes
     inside a region that already exists when the content changes. -->
<div class="wake-host" role="status" aria-live="polite">
	{#if waking}
		<div class="wake-banner">
			<span class="spinner" aria-hidden="true"></span>
			<p>
				<span class="wake-title">{t('wakeTitle')}</span>
				<span class="wake-sub">{t('wakeSub')}</span>
			</p>
		</div>
	{:else if down}
		<div class="wake-banner down">
			<Icon name="warning" size={16} />
			<p>
				<span class="wake-title">{t('wakeDownTitle')}</span>
				<span class="wake-sub">{t('wakeDownSub')}</span>
			</p>
			<button type="button" class="btn secondary" onclick={retry}>{t('retry')}</button>
		</div>
	{/if}
</div>
