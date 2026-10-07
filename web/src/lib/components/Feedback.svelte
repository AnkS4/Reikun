<script lang="ts">
	import { apiFeedback } from '#lib/api.ts';
	import Icon from './Icon.svelte';
	let {
		kind,
		refId,
		query = null
	}: { kind: 'search' | 'explanation'; refId: number | null; query?: string | null } = $props();
	let rating = $state<0 | 1 | -1>(0);

	// The component is reused across searches — clear the highlight when the
	// thing being rated changes, so a new result never shows a stale vote.
	$effect(() => {
		void refId;
		void query;
		rating = 0;
	});

	async function pick(v: 1 | -1) {
		if (rating === v) return;
		rating = v;
		try {
			await apiFeedback(kind, refId, v, query);
		} catch {
			/* best-effort telemetry */
		}
	}
</script>

<span class="feedback-row" role="group" aria-label="Rate this {kind}">
	<button
		type="button"
		class:sel={rating === 1}
		title="Helpful"
		aria-label="Helpful"
		onclick={() => pick(1)}
	>
		<Icon name="thumbs-up" size={14} />
	</button>
	<button
		type="button"
		class:sel={rating === -1}
		class:down={rating === -1}
		title="Not helpful"
		aria-label="Not helpful"
		onclick={() => pick(-1)}
	>
		<Icon name="thumbs-down" size={14} />
	</button>
</span>
