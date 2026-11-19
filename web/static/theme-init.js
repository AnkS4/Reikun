			// Apply persisted theme before first paint to avoid a flash.
			(function () {
				var t = 'system';
				// The lite_theme cookie is the shared channel with the lite UI and is
				// authoritative: whichever variant you switched last wins (see
				// stored() in theme.svelte.ts). lite's single dark maps onto the
				// oled canvas unless this end already prefers dark/oled.
				var c = document.cookie.match(/(?:^|;\s*)lite_theme=(light|dark)(?:;|$)/)?.[1];
				if (c === 'light') t = 'light';
				else if (c === 'dark') {
					var local;
					try {
						local = localStorage.getItem('reikun-theme');
					} catch (e) {}
					t = local === 'dark' || local === 'oled' ? local : 'oled';
				} else {
					// No cookie — follow this variant's own choice. localStorage can
					// throw (Safari "Block all cookies", in-app webviews, sandboxed
					// iframes) — fall back to the OS preference, never abort.
					try {
						t = localStorage.getItem('reikun-theme');
					} catch (e) {}
					if (t === 'amoled') t = 'oled'; // legacy value
					if (t !== 'light' && t !== 'dark' && t !== 'oled') t = 'system';
				}
				var resolved = t;
				if (t === 'system') {
					// NOTE: 'oled' is intentionally the default dark resolution for system preference (not 'dark').
					resolved = matchMedia('(prefers-color-scheme: dark)').matches ? 'oled' : 'light';
				}
				document.documentElement.dataset.theme = resolved;
				// Keep in sync with --bg in app.css and CHROME_COLOR in theme.svelte.ts.
				var bg = { light: '#fcfaf6', dark: '#0f1620', oled: '#000000' }[resolved] || '#fcfaf6';
				var meta = document.getElementById('theme-color');
				if (meta) meta.setAttribute('content', bg);
			})();
