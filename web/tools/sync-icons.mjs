#!/usr/bin/env node
/* Regenerates web/src/lib/icons.ts from the installed lucide-static package.
 *
 * The SPA glyphs inline the upstream Lucide bodies verbatim (modulo SVG
 * comment/wrapper stripping and currentColor passthrough), so an upstream
 * update is:
 *
 *   npm install lucide-static@latest --save-dev && npm run sync:icons
 *
 * then review the diff and rebuild lite's subset font
 * (uv run python scripts/build_lite_icons.py) — F-codes are stable.
 *
 * The name mapping (our key → upstream icon name) matches the lite font
 * builder's F-code table. Bodies carry no stroke attributes of their own —
 * Icon.svelte supplies stroke-width/currentColor.
 */
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import pathMod from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '..');
const outFile = pathMod.join(webRoot, 'src/lib/icons.ts');
const iconsDir = pathMod.join(webRoot, 'node_modules/lucide-static/icons');

const MAP = {
	search: 'search',
	dices: 'dices',
	languages: 'languages',
	'chart-line': 'chart-line',
	school: 'school',
	palette: 'palette',
	replay: 'rotate-ccw',
	history: 'rotate-ccw-clock',
	database: 'database',
	'thumbs-up': 'thumbs-up',
	'thumbs-down': 'thumbs-down',
	'expand-more': 'chevron-down',
	info: 'info',
	award: 'award',
	import: 'import',
	bot: 'bot',
	split: 'split',
	copy: 'copy',
	check: 'check',
	blend: 'blend',
	share: 'share',
	warning: 'triangle-alert',
	close: 'x',
	'arrow-up': 'arrow-up',
	'arrow-right': 'arrow-right',
	'pen-line': 'pen-line',
	'book-open-text': 'book-open-text',
	zap: 'zap',
};

const HEADER = `/**
 * Inline SVG icon bodies (24×24, 2px stroke, Lucide Icons — ISC). Static
 * data rendered via {@html} in Icon.svelte; safe because the strings are
 * compile-time constants. Regenerate with \`npm run sync:icons\` (details in
 * tools/sync-icons.mjs) — do not hand-edit the bodies below.
 *
 * This dict is the SPA's single icon source: every icon renders through
 * \`Icon.svelte\` from here — same 24×24 grid, \`stroke-width="2"\`,
 * \`currentColor\`, \`aria-hidden\` (meaning lives in title/aria-label).
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
`;
const FOOTER = `};

export type IconName = keyof typeof icons;
`;

const STRIP = /(?:\s(?:fill="none"|stroke="currentColor"|stroke-width="2"|stroke-linecap="round"|stroke-linejoin="round"))/g;
const elementsOf = (body) =>
	// top-level self-closing primitives only — Lucide bodies are flat lists
	body.match(/<(?:path|circle|rect|ellipse|line|polyline|polygon)[^>]*\/>/g) ?? [];

const entries = [];
for (const [ourName, upName] of Object.entries(MAP)) {
	const raw = readFileSync(pathMod.join(iconsDir, `${upName}.svg`), 'utf8');
	const body = raw
		.replace(/<!--[\s\S]*?-->/g, '') // upstream license header comment
		.match(/<svg[^>]*>([\s\S]*?)<\/svg>/)[1];
	const els = elementsOf(body);
	if (els.length === 0) throw new Error(`${upName}: no primitives found`);
	const cleaned = els.map((el) => {
		if (/fill="currentColor"/.test(el)) {
			// filled sub-part (e.g. palette dots): keep fill, silence inherited stroke
			return el.replace(STRIP, '').replace('fill="currentColor"', 'fill="currentColor" stroke="none"');
		}
		return el.replace(STRIP, '');
	});
	entries.push(`\t'${ourName}': '${cleaned.join(' ')}',\n`);
}

writeFileSync(outFile, HEADER + entries.join('') + FOOTER);
console.log(`wrote ${pathMod.relative(webRoot, outFile)} — ${entries.length} glyphs from lucide-static`);
