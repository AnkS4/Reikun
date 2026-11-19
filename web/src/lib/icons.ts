/**
 * Inline SVG icon bodies (24×24, 1.5px stroke, Tabler Icons — MIT). Static
 * data rendered via {@html} in Icon.svelte; safe because the strings are
 * compile-time constants.
 *
 * This dict is the SPA's single icon source: every icon renders through
 * `Icon.svelte` from here — same 24×24 grid, `stroke-width="1.5"`,
 * `currentColor`, `aria-hidden` (meaning lives in title/aria-label).
 * Do not add icon SVGs anywhere else, and don't mix in emoji or
 * unicode-symbol "icons"; the deliberate exceptions are typographic arrows
 * in link text (←, →) and the あ furigana button (a language character,
 * not an icon — no icon set ships a kana face; ours is Tabler's
 * `language-hiragana`, same as every other glyph here). Spinners and
 * status marks are CSS-drawn. (The stroke-order diagram is StrokeSvg.svelte
 * — KanjiVG data, not an icon.)
 * Lite keeps its own uniform language instead — text labels, a CSS dot and
 * typographic arrows — because hardened browsers with svg.disabled
 * (Tor/LibreWolf "Safest") blank inline SVG; see the note above the glyph
 * constants in app/lite/__init__.py.
 */
export const icons = {
	'search': '<path stroke-linecap="round" stroke-linejoin="round" d="M3 10a7 7 0 1 0 14 0a7 7 0 1 0-14 0m18 11l-6-6"/>',
	'languages': '<path d="M9 6.371C9 10.789 6.761 13 4 13m0-6.629h7"/><path d="M5 9c0 2.144 2.252 3.908 6 4m1 7l4-9l4 9m-.9-2h-6.2M6.694 3l.793.582"/>',
	'shuffle': '<path d="m18 4l3 3l-3 3m0 10l3-3l-3-3"/><path d="M3 7h3a5 5 0 0 1 5 5a5 5 0 0 0 5 5h5m0-10h-5a4.98 4.98 0 0 0-3 1m-4 8a5 5 0 0 1-3 1H3"/>',
	'school': '<path d="M22 9L12 5L2 9l10 4zv6"/><path d="M6 10.6V16a6 3 0 0 0 12 0v-5.4"/>',
	'palette': '<path d="M12 21a9 9 0 0 1 0-18c4.97 0 9 3.582 9 8c0 1.06-.474 2.078-1.318 2.828S17.693 15 16.5 15H14a2 2 0 0 0-1 3.75A1.3 1.3 0 0 1 12 21"/><path d="M7.5 10.5a1 1 0 1 0 2 0a1 1 0 1 0-2 0m4-3a1 1 0 1 0 2 0a1 1 0 1 0-2 0m4 3a1 1 0 1 0 2 0a1 1 0 1 0-2 0"/>',
	'replay': '<path stroke-linecap="round" stroke-linejoin="round" d="M19.95 11a8 8 0 1 0-.5 4m.5 5v-5h-5"/>',
	'database': '<path d="M4 6a8 3 0 1 0 16 0A8 3 0 1 0 4 6"/><path d="M4 6v6a8 3 0 0 0 16 0V6"/><path d="M4 12v6a8 3 0 0 0 16 0v-6"/>',
	'thumbs-up': '<path stroke-linecap="round" stroke-linejoin="round" d="M7 11v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1za4 4 0 0 0 4-4V6a2 2 0 0 1 4 0v5h3a2 2 0 0 1 2 2l-1 5a2 3 0 0 1-2 2h-7a3 3 0 0 1-3-3"/>',
	'thumbs-down': '<path stroke-linecap="round" stroke-linejoin="round" d="M7 13V5a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1za4 4 0 0 1 4 4v1a2 2 0 0 0 4 0v-5h3a2 2 0 0 0 2-2l-1-5a2 3 0 0 0-2-2h-7a3 3 0 0 0-3 3"/>',
	'expand-more': '<path stroke-linecap="round" stroke-linejoin="round" d="m6 9l6 6l6-6"/>',
	'info': '<path d="M3 12a9 9 0 1 0 18 0a9 9 0 0 0-18 0m9-3h.01"/><path d="M11 12h1v4h1"/>',
	'award': '<path d="M6 9a6 6 0 1 0 12 0A6 6 0 1 0 6 9"/><path d="m12 15l3.4 5.89l1.598-3.233l3.598.232l-3.4-5.889M6.802 12l-3.4 5.89L7 17.657l1.598 3.232l3.4-5.889"/>',
	'import': '<path stroke-linecap="round" stroke-linejoin="round" d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M7 11l5 5l5-5m-5-7v12"/>',
	'bot': '<path stroke-linecap="round" stroke-linejoin="round" d="M6 6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zm6-4v2m-3 8v9m6-9v9M5 16l4-2m6 0l4 2M9 18h6M10 8v.01M14 8v.01"/>',
	'split': '<path d="M21 17h-8l-3.5-5H3m18-5h-8l-3.495 5"/><path d="m18 10l3-3l-3-3m0 16l3-3l-3-3"/>',
	'copy': '<path d="M7 9.667A2.667 2.667 0 0 1 9.667 7h8.666A2.667 2.667 0 0 1 21 9.667v8.666A2.667 2.667 0 0 1 18.333 21H9.667A2.667 2.667 0 0 1 7 18.333z"/><path d="M4.012 16.737A2 2 0 0 1 3 15V5c0-1.1.9-2 2-2h10c.75 0 1.158.385 1.5 1"/>',
	'check': '<path stroke-linecap="round" stroke-linejoin="round" d="m5 12l5 5L20 7"/>',
	'share': '<path stroke-linecap="round" stroke-linejoin="round" d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M7 9l5-5l5 5m-5-5v12"/>',
	'warning': '<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m-1.637-9.409L2.257 17.125a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636-2.87L13.637 3.59a1.914 1.914 0 0 0-3.274 0M12 16h.01"/>',
	'close': '<path stroke-linecap="round" stroke-linejoin="round" d="M18 6L6 18M6 6l12 12"/>',
	'arrow-up': '<path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m6-8l-6-6m-6 6l6-6"/>',
	'arrow-right': '<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6 6l6-6m-6-6l6 6"/>',
	'pen-line': '<path stroke-linecap="round" stroke-linejoin="round" d="M4 20h4L18.5 9.5a2.828 2.828 0 1 0-4-4L4 16zm9.5-13.5l4 4"/>',
	'book-open': '<path stroke-linecap="round" stroke-linejoin="round" d="M3 19a9 9 0 0 1 9 0a9 9 0 0 1 9 0M3 6a9 9 0 0 1 9 0a9 9 0 0 1 9 0M3 6v13m9-13v13m9-13v13"/>',
	'book-open-text': '<path d="M19 4v16H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M19 16H7a2 2 0 0 0-2 2M9 8h6"/>',
	'feather': '<path d="m4 20l10-10m0-5v5h5m-9-1v5h5m-9-1v5h5m-5-5l4-4l4-4"/><path d="M19 10c.638-.636 1-1.515 1-2.486A3.515 3.515 0 0 0 16.483 4c-.97 0-1.847.367-2.483 1m-3 13l4-4l4-4"/>',
	'kana': '<path d="M4 5h7M7 4c0 4.846 0 7 .5 8"/><path d="M10 8.5c0 2.286-2 4.5-3.5 4.5S4 11.865 4 11q0-3 3-3c3 0 5 .57 5 2.857q0 2.286-2 3.143m2 6l4-9l4 9m-.9-2h-6.2"/>',
};

export type IconName = keyof typeof icons;
