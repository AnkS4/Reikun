/**
 * Inline SVG icon bodies (24×24, 2px stroke, Lucide Icons — ISC). Static
 * data rendered via {@html} in Icon.svelte; safe because the strings are
 * compile-time constants. Regenerate with `npm run sync:icons` (details in
 * tools/sync-icons.mjs) — do not hand-edit the bodies below.
 *
 * This dict is the SPA's single icon source: every icon renders through
 * `Icon.svelte` from here — same 24×24 grid, `stroke-width="2"`,
 * `currentColor`, `aria-hidden` (meaning lives in title/aria-label).
 * Do not add icon SVGs anywhere else, and don't mix in emoji or
 * unicode-symbol "icons"; the deliberate exceptions are typographic arrows
 * in link text (←, →) and the あ furigana/kana-tile glyphs (language
 * characters, not icons — Lucide ships no Japanese-kana face). Spinners and
 * status marks are CSS-drawn. (The stroke-order diagram is StrokeSvg.svelte
 * — KanjiVG data, not an icon.)
 * Lite keeps its own uniform language instead — text labels, a CSS dot and
 * typographic arrows — because hardened browsers with svg.disabled
 * (Tor/LibreWolf "Safest") blank inline SVG; see the note above the glyph
 * constants in app/lite/__init__.py.
 */
export const icons = {
	'search': '<path d="m21 21-4.34-4.34" /> <circle cx="11" cy="11" r="8" />',
	'dices': '<rect width="12" height="12" x="2" y="10" rx="2" ry="2" /> <path d="m17.92 14 3.5-3.5a2.24 2.24 0 0 0 0-3l-5-4.92a2.24 2.24 0 0 0-3 0L10 6" /> <path d="M6 18h.01" /> <path d="M10 14h.01" /> <path d="M15 6h.01" /> <path d="M18 9h.01" />',
	'languages': '<path d="m5 8 6 6" /> <path d="m4 14 6-6 2-3" /> <path d="M2 5h12" /> <path d="M7 2h1" /> <path d="m22 22-5-10-5 10" /> <path d="M14 18h6" />',
	'chart-line': '<path d="M3 3v16a2 2 0 0 0 2 2h16" /> <path d="m19 9-5 5-4-4-3 3" />',
	'school': '<path d="M14 21v-3a2 2 0 0 0-4 0v3" /> <path d="M18 4.933V21" /> <path d="m4 6 7.106-3.79a2 2 0 0 1 1.788 0L20 6" /> <path d="m6 11-3.52 2.147a1 1 0 0 0-.48.854V19a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5a1 1 0 0 0-.48-.853L18 11" /> <path d="M6 4.933V21" /> <circle cx="12" cy="9" r="2" />',
	'palette': '<path d="M12 22a1 1 0 0 1 0-20 10 9 0 0 1 10 9 5 5 0 0 1-5 5h-2.25a1.75 1.75 0 0 0-1.4 2.8l.3.4a1.75 1.75 0 0 1-1.4 2.8z" /> <circle cx="13.5" cy="6.5" r=".5" fill="currentColor" stroke="none" /> <circle cx="17.5" cy="10.5" r=".5" fill="currentColor" stroke="none" /> <circle cx="6.5" cy="12.5" r=".5" fill="currentColor" stroke="none" /> <circle cx="8.5" cy="7.5" r=".5" fill="currentColor" stroke="none" />',
	'replay': '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /> <path d="M3 3v5h5" />',
	'database': '<ellipse cx="12" cy="5" rx="9" ry="3" /> <path d="M3 5V19A9 3 0 0 0 21 19V5" /> <path d="M3 12A9 3 0 0 0 21 12" />',
	'thumbs-up': '<path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" /> <path d="M7 10v12" />',
	'thumbs-down': '<path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" /> <path d="M17 14V2" />',
	'expand-more': '<path d="m6 9 6 6 6-6" />',
	'info': '<circle cx="12" cy="12" r="10" /> <path d="M12 16v-4" /> <path d="M12 8h.01" />',
	'award': '<path d="m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 2.686a.5.5 0 0 1-.81-.469l1.514-8.526" /> <circle cx="12" cy="8" r="6" />',
	'import': '<path d="M12 3v12" /> <path d="m8 11 4 4 4-4" /> <path d="M8 5H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-4" />',
	'bot': '<path d="M12 8V4H8" /> <rect width="16" height="12" x="4" y="8" rx="2" /> <path d="M2 14h2" /> <path d="M20 14h2" /> <path d="M15 13v2" /> <path d="M9 13v2" />',
	'split': '<path d="M16 3h5v5" /> <path d="M8 3H3v5" /> <path d="M12 22v-8.3a4 4 0 0 0-1.172-2.872L3 3" /> <path d="m15 9 6-6" />',
	'copy': '<rect width="14" height="14" x="8" y="8" rx="2" ry="2" /> <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />',
	'check': '<path d="M20 6 9 17l-5-5" />',
	'blend': '<circle cx="15" cy="9" r="7" /> <circle cx="9" cy="15" r="7" />',
	'share': '<path d="M12 2v13" /> <path d="m16 6-4-4-4 4" /> <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />',
	'warning': '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /> <path d="M12 9v4" /> <path d="M12 17h.01" />',
	'close': '<path d="M18 6 6 18" /> <path d="m6 6 12 12" />',
	'arrow-up': '<path d="m5 12 7-7 7 7" /> <path d="M12 19V5" />',
	'arrow-right': '<path d="M5 12h14" /> <path d="m12 5 7 7-7 7" />',
	'pen-line': '<path d="M13 21h8" /> <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />',
	'book-open-text': '<path d="M12 5v16" /> <path d="M16 13h2" /> <path d="M16 9h2" /> <path d="M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z" /> <path d="M6 13h2" /> <path d="M6 9h2" />',
	'zap': '<path d="M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z" />',
};

export type IconName = keyof typeof icons;
