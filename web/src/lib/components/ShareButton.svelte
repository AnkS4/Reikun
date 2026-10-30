<script lang="ts">
	import { page } from '$app/state';
	import { t } from '#lib/i18n.svelte.ts';
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
		// Always copy the URL to clipboard on desktop
		try {
			await navigator.clipboard.writeText(url);
			flash();
		} catch {
			// Clipboard API blocked (e.g., by uBlock), try deprecated execCommand
			try {
				const textArea = document.createElement('textarea');
				textArea.value = url;
				textArea.style.position = 'fixed';
				textArea.style.left = '-9999px';
				textArea.style.top = '0';
				document.body.appendChild(textArea);
				textArea.focus();
				textArea.select();
				const successful = document.execCommand('copy');
				document.body.removeChild(textArea);
				if (successful) {
					flash();
				}
			} catch {
				/* Both methods failed — nothing sensible left to do */
			}
		}
	}
</script>

<button
	type="button"
	class="btn tertiary copy-link-btn"
	title={t('shareTitle')}
	aria-label={copied ? t('linkCopied') : t('shareTitle')}
	onclick={share}
>
	<Icon name={copied ? 'check' : 'share'} size={14} />
	<span>{copied ? t('linkCopied') : t('share')}</span>
</button>
<span class="sr-only" role="status">{copied ? t('linkCopiedSr') : ''}</span>
