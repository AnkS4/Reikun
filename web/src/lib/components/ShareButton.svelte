<script lang="ts">
	import { page } from '$app/state';
	import Icon from './Icon.svelte';

	let { query }: { query: string } = $props();

	let copied = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	// Shared link = this search only — the JLPT level is a personal preference
	// and the result-count paging is not part of what's being shared.
	const url = $derived.by(() => {
		const u = new URL(page.url.origin + page.url.pathname);
		u.searchParams.set('q', query);
		return u.toString();
	});

	function flash() {
		copied = true;
		clearTimeout(timer);
		timer = setTimeout(() => (copied = false), 2000);
	}

	async function share() {
		const data = { title: `${query} — Reikun`, text: `“${query}” in Reikun, the Japanese dictionary`, url };
		// Native share sheet where it exists (phones, Safari, Edge); otherwise copy.
		let canNativeShare = false;
		try {
			canNativeShare = Boolean(navigator.share) && (!navigator.canShare || navigator.canShare(data));
		} catch {
			canNativeShare = false;
		}
		if (canNativeShare) {
			try {
				await navigator.share(data);
				return;
			} catch (e) {
				if (e instanceof DOMException && e.name === 'AbortError') return; // user closed the sheet
			}
		}
		try {
			await navigator.clipboard.writeText(url);
			flash();
		} catch {
			/* clipboard blocked — nothing sensible left to do */
		}
	}
</script>

<button
	type="button"
	class="btn tertiary share-btn"
	title="Share this search"
	aria-label={copied ? 'Link copied' : 'Share this search'}
	onclick={share}
>
	<Icon name={copied ? 'check' : 'share'} size={14} />
	<span>{copied ? 'Link copied' : 'Share'}</span>
</button>
<span class="sr-only" role="status">{copied ? 'Link copied to clipboard' : ''}</span>
