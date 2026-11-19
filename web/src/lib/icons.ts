/**
 * Inline SVG icon bodies (24×24, 1.5px stroke, Tabler Icons — MIT). Static
 * data rendered via {@html} in Icon.svelte; safe because the strings are
 * compile-time constants. Regenerate with `npm run sync:icons` (details in
 * tools/sync-icons.mjs) — do not hand-edit the bodies below.
 *
 * This dict is the SPA's single icon source: every icon renders through
 * `Icon.svelte` from here — same 24×24 grid, `stroke-width="1.5"`,
 * `currentColor`, `aria-hidden` (meaning lives in title/aria-label).
 * Do not add icon SVGs anywhere else, and don't mix in emoji or
 * unicode-symbol "icons"; the deliberate exceptions are typographic arrows
 * in link text (←, →) and the あ furigana button (a language character,
 * not an icon — Tabler ships no kana-specific face; ours is
 * `alphabet-japanese`, same as every other glyph here). Spinners and
 * status marks are CSS-drawn. (The stroke-order diagram is StrokeSvg.svelte
 * — KanjiVG data, not an icon.)
 * Lite keeps its own uniform language instead — text labels, a CSS dot and
 * typographic arrows — because hardened browsers with svg.disabled
 * (Tor/LibreWolf "Safest") blank inline SVG; see the note above the glyph
 * constants in app/lite/__init__.py.
 */
export const icons = {
	'search': '<path d="M0 0h24v24H0z"/> <path d="M3 10a7 7 0 1 0 14 0a7 7 0 1 0 -14 0"/> <path d="M21 21l-6 -6"/>',
	'languages': '<path d="M0 0h24v24H0z"/> <path d="M9 6.371c0 4.418 -2.239 6.629 -5 6.629"/> <path d="M4 6.371h7"/> <path d="M5 9c0 2.144 2.252 3.908 6 4"/> <path d="M12 20l4 -9l4 9"/> <path d="M19.1 18h-6.2"/> <path d="M6.694 3l.793 .582"/>',
	'shuffle': '<path d="M0 0h24v24H0z"/> <path d="M18 4l3 3l-3 3"/> <path d="M18 20l3 -3l-3 -3"/> <path d="M3 7h3a5 5 0 0 1 5 5a5 5 0 0 0 5 5h5"/> <path d="M21 7h-5a4.978 4.978 0 0 0 -3 1m-4 8a4.984 4.984 0 0 1 -3 1h-3"/>',
	'school': '<path d="M0 0h24v24H0z"/> <path d="M22 9l-10 -4l-10 4l10 4l10 -4v6"/> <path d="M6 10.6v5.4a6 3 0 0 0 12 0v-5.4"/>',
	'palette': '<path d="M0 0h24v24H0z"/> <path d="M12 21a9 9 0 0 1 0 -18c4.97 0 9 3.582 9 8c0 1.06 -.474 2.078 -1.318 2.828c-.844 .75 -1.989 1.172 -3.182 1.172h-2.5a2 2 0 0 0 -1 3.75a1.3 1.3 0 0 1 -1 2.25"/> <path d="M7.5 10.5a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/> <path d="M11.5 7.5a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/> <path d="M15.5 10.5a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>',
	'replay': '<path d="M0 0h24v24H0z"/> <path d="M19.95 11a8 8 0 1 0 -.5 4m.5 5v-5h-5"/>',
	'database': '<path d="M0 0h24v24H0z"/> <path d="M4 6a8 3 0 1 0 16 0a8 3 0 1 0 -16 0"/> <path d="M4 6v6a8 3 0 0 0 16 0v-6"/> <path d="M4 12v6a8 3 0 0 0 16 0v-6"/>',
	'thumbs-up': '<path d="M0 0h24v24H0z"/> <path d="M7 11v8a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1v-7a1 1 0 0 1 1 -1h3a4 4 0 0 0 4 -4v-1a2 2 0 0 1 4 0v5h3a2 2 0 0 1 2 2l-1 5a2 3 0 0 1 -2 2h-7a3 3 0 0 1 -3 -3"/>',
	'thumbs-down': '<path d="M0 0h24v24H0z"/> <path d="M7 13v-8a1 1 0 0 0 -1 -1h-2a1 1 0 0 0 -1 1v7a1 1 0 0 0 1 1h3a4 4 0 0 1 4 4v1a2 2 0 0 0 4 0v-5h3a2 2 0 0 0 2 -2l-1 -5a2 3 0 0 0 -2 -2h-7a3 3 0 0 0 -3 3"/>',
	'expand-more': '<path d="M0 0h24v24H0z"/> <path d="M6 9l6 6l6 -6"/>',
	'info': '<path d="M0 0h24v24H0z"/> <path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0 -18 0"/> <path d="M12 9h.01"/> <path d="M11 12h1v4h1"/>',
	'award': '<path d="M0 0h24v24H0z"/> <path d="M6 9a6 6 0 1 0 12 0a6 6 0 1 0 -12 0"/> <path d="M12 15l3.4 5.89l1.598 -3.233l3.598 .232l-3.4 -5.889"/> <path d="M6.802 12l-3.4 5.89l3.598 -.233l1.598 3.232l3.4 -5.889"/>',
	'import': '<path d="M0 0h24v24H0z"/> <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/> <path d="M7 11l5 5l5 -5"/> <path d="M12 4l0 12"/>',
	'bot': '<path d="M0 0h24v24H0z"/> <path d="M6 6a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v4a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2l0 -4"/> <path d="M12 2v2"/> <path d="M9 12v9"/> <path d="M15 12v9"/> <path d="M5 16l4 -2"/> <path d="M15 14l4 2"/> <path d="M9 18h6"/> <path d="M10 8v.01"/> <path d="M14 8v.01"/>',
	'split': '<path d="M0 0h24v24H0z"/> <path d="M21 17h-8l-3.5 -5h-6.5"/> <path d="M21 7h-8l-3.495 5"/> <path d="M18 10l3 -3l-3 -3"/> <path d="M18 20l3 -3l-3 -3"/>',
	'copy': '<path d="M0 0h24v24H0z"/> <path d="M7 9.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667l0 -8.666"/> <path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1"/>',
	'check': '<path d="M0 0h24v24H0z"/> <path d="M5 12l5 5l10 -10"/>',
	'share': '<path d="M0 0h24v24H0z"/> <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"/> <path d="M7 9l5 -5l5 5"/> <path d="M12 4l0 12"/>',
	'warning': '<path d="M0 0h24v24H0z"/> <path d="M12 9v4"/> <path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0"/> <path d="M12 16h.01"/>',
	'close': '<path d="M0 0h24v24H0z"/> <path d="M18 6l-12 12"/> <path d="M6 6l12 12"/>',
	'arrow-up': '<path d="M0 0h24v24H0z"/> <path d="M12 5l0 14"/> <path d="M18 11l-6 -6"/> <path d="M6 11l6 -6"/>',
	'arrow-right': '<path d="M0 0h24v24H0z"/> <path d="M5 12l14 0"/> <path d="M13 18l6 -6"/> <path d="M13 6l6 6"/>',
	'pen-line': '<path d="M0 0h24v24H0z"/> <path d="M4 20h4l10.5 -10.5a2.828 2.828 0 1 0 -4 -4l-10.5 10.5v4"/> <path d="M13.5 6.5l4 4"/>',
	'book-open': '<path d="M0 0h24v24H0z"/> <path d="M3 19a9 9 0 0 1 9 0a9 9 0 0 1 9 0"/> <path d="M3 6a9 9 0 0 1 9 0a9 9 0 0 1 9 0"/> <path d="M3 6l0 13"/> <path d="M12 6l0 13"/> <path d="M21 6l0 13"/>',
	'book-open-text': '<path d="M0 0h24v24H0z"/> <path d="M19 4v16h-12a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h12"/> <path d="M19 16h-12a2 2 0 0 0 -2 2"/> <path d="M9 8h6"/>',
	'feather': '<path d="M0 0h24v24H0z"/> <path d="M4 20l10 -10m0 -5v5h5m-9 -1v5h5m-9 -1v5h5m-5 -5l4 -4l4 -4"/> <path d="M19 10c.638 -.636 1 -1.515 1 -2.486a3.515 3.515 0 0 0 -3.517 -3.514c-.97 0 -1.847 .367 -2.483 1m-3 13l4 -4l4 -4"/>',
	'kana': '<path d="M0 0h24v24H0z"/> <path d="M6 6h10"/> <path d="M10 4c0 6.784 .8 11.1 1.5 12.5"/> <path d="M14.25 10.75c0 3.429 -2.75 6.75 -4.812 6.75s-3.438 -1.25 -3.438 -3c0 -2.5 1.375 -4.5 4.125 -4.5s6.875 .855 6.875 4.286q 0 3.428 -2.75 4.714"/>',
};

export type IconName = keyof typeof icons;
