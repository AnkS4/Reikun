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
				// The Spanish edition's origin swaps the brand artwork for the
				// gold-sun set (same mark, Spanish accent) — icon + touch icon +
				// manifest + the data-pack flag the CSS theme rules key on (the
				// dark emblem swap in app.css picks the es artwork through it).
				// The favicon SVG already adapts to dark chrome via its own styles.
				if (location.hostname === 'es.reikun.app') {
					document.documentElement.dataset.pack = 'es';
					var icon = document.querySelector('link[rel="icon"][type="image/svg+xml"]');
					if (icon) icon.setAttribute('href', icon.getAttribute('href').replace(/favicon\.svg$/, 'favicons/favicon-es.svg'));
					document.querySelectorAll('link[rel="icon"][type="image/png"]').forEach(function (png) {
						png.setAttribute('href', png.getAttribute('href').replace(/favicon-(\d+)\.png$/, 'favicon-es-$1.png'));
					});
					var touch = document.querySelector('link[rel="apple-touch-icon"]');
					if (touch) touch.setAttribute('href', touch.getAttribute('href').replace(/apple-touch-icon\.png/, 'apple-touch-icon-es.png'));
					var manifest = document.querySelector('link[rel="manifest"]');
					if (manifest) manifest.setAttribute('href', manifest.getAttribute('href').replace(/site\.webmanifest/, 'site-es.webmanifest'));
				}
			})();
