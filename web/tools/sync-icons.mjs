#!/usr/bin/env node
/* Regenerates web/src/lib/icons.ts from the installed @tabler/icons package.
 *
 * The 27 SPA glyphs inline the upstream Tabler bodies verbatim (modulo SVG
 * comment/wrapper stripping and currentColor passthrough), so an upstream
 * update is:
 *
 *   npm install @tabler/icons@latest --save-dev && npm run sync:icons
 *
 * then review the diff and rebuild lite's subset font
 * (uv run python scripts/build_lite_icons.py) if lite references changed
 * shapes — F-codes are stable, so usually nothing to do there.
 *
 * The name mapping (our key → upstream icon name) matches the lite font
 * builder's F-code table; kana is tabler:alphabet-japanese since 2026-11.
 * Bodies carry no stroke attributes of their own — Icon.svelte supplies
 * stroke-width/currentColor.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import pathMod from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '..');
const outFile = pathMod.join(webRoot, 'src/lib/icons.ts');
const iconsDir = pathMod.join(webRoot, 'node_modules/@tabler/icons/icons/outline');

// our key → upstream icon name (Tabler Icons, MIT)
const MAP = {
	search: 'search',
	languages: 'language',
	shuffle: 'arrows-shuffle',
	school: 'school',
	palette: 'palette',
	replay: 'rotate',
	database: 'database',
	'thumbs-up': 'thumb-up',
	'thumbs-down': 'thumb-down',
	'expand-more': 'chevron-down',
	info: 'info-circle',
	award: 'award',
	import: 'download',
	bot: 'robot',
	split: 'arrows-split',
	copy: 'copy',
	check: 'check',
	share: 'upload',
	warning: 'alert-triangle',
	close: 'x',
	'arrow-up': 'arrow-up',
	'arrow-right': 'arrow-right',
	'pen-line': 'pencil',
	'book-open': 'book',
	'book-open-text': 'book-2',
	feather: 'feather',
	kana: 'alphabet-japanese',
};

const HEADER = `/**
 * Inline SVG icon bodies (24×24, 1.5px stroke, Tabler Icons — MIT). Static
 * data rendered via {@html} in Icon.svelte; safe because the strings are
 * compile-time constants. Regenerate with \`npm run sync:icons\` (details in
 * tools/sync-icons.mjs) — do not hand-edit the bodies below.
 *
 * This dict is the SPA's single icon source: every icon renders through
 * \`Icon.svelte\` from here — same 24×24 grid, \`stroke-width="1.5"\`,
 * \`currentColor\`, \`aria-hidden\` (meaning lives in title/aria-label).
 * Do not add icon SVGs anywhere else, and don't mix in emoji or
 * unicode-symbol "icons"; the deliberate exceptions are typographic arrows
 * in link text (←, →) and the あ furigana button (a language character,
 * not an icon — Tabler ships no kana-specific face; ours is
 * \`alphabet-japanese\`, same as every other glyph here). Spinners and
 * status marks are CSS-drawn. (The stroke-order diagram is StrokeSvg.svelte
 * — KanjiVG data, not an icon.)
 * Lite keeps its own uniform language instead — text labels, a CSS dot and
 * typographic arrows — because hardened browsers with svg.disabled
 * (Tor/LibreWolf "Safest") blank inline SVG; see the note above the glyph
 * constants in app/lite/__init__.py.
 */
export const icons = {
`;
const FOOTER = `};

export type IconName = keyof typeof icons;
`;

const entries = [];
for (const [ourName, upName] of Object.entries(MAP)) {
	const svg = readFileSync(pathMod.join(iconsDir, `${upName}.svg`), 'utf8');
	const body = svg.match(/<svg[^>]*>([\s\S]*?)<\/svg>/)[1]
		// strip the upstream comment block with tags/unicode (keeps output byte-small)
		.replace(/<!--[\s\S]*?-->/g, '')
		// drop the upstream hit-target rectangle (24×24 bounding box) — Icon.svelte
		// supplies the stroke, so a stripped-stroke rect renders as a square frame
		.replace(/<path\s+[^>]*d="M0 0h24v24H0z"[^>]*\/>\s*/g, '')
		// keep only the visible paths, verbatim (d attributes are ours untouched)
		.replace(/<path\s+([^>]*)\/>/g, (_m, attrs) => {
			const d = attrs.match(/\bd="([^"]*)"/);
			if (!d) throw new Error(`${upName}: path without d`);
			return `<path d="${d[1]}"/>`;
		})
		.replace(/\s+/g, ' ')
		.trim();
	entries.push(`\t'${ourName}': '${body}',\n`);
}

writeFileSync(outFile, HEADER + entries.join('') + FOOTER);
console.log(`wrote ${pathMod.relative(webRoot, outFile)} — ${entries.length} glyphs from @tabler/icons`);
