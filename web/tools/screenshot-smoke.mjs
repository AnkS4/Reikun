#!/usr/bin/env node
/* Visual smoke check — screenshots both variants at 375/1280 px and fails
   on console errors or horizontal page overflow.
 *
 * Usage:
 *   node tools/screenshot-smoke.mjs [--spa-base URL] [--lite-base URL] [--out DIR]
 *
 * The SPA must be served statically (e.g. `npm run build` then any static
 * server pointed at `build/`; the script tries `/about` and falls back to
 * `/about.html`). The lite variant is server-rendered by FastAPI, so it is
 * screenshotted only when --lite-base is reachable (default
 * http://localhost:8000); otherwise it is skipped with a note.
 *
 * This is deliberately a smoke test, not a visual-diff harness: captures
 * land in --out (default docs/screenshots/smoke/) for human review.
 *
 * Setup (once per machine):  npm i -D playwright && npx playwright install chromium
 * Playwright is deliberately NOT in package.json — keep `npm ci` lean for
 * everyone who never runs the visual pass. Without it this script exits 1
 * with the install hint rather than crashing.
 */
import { mkdir } from 'node:fs/promises';
import pathMod from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '..', '..');

const args = Object.fromEntries(
	process.argv.slice(2).flatMap((a, i, arr) => {
		if (a.startsWith('--')) {
			const v = arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : 'true';
			return [[a.slice(2), v]];
		}
		return [];
	})
);

const spaBase = (args['spa-base'] ?? process.env.SPA_BASE_URL ?? 'http://127.0.0.1:8765').replace(/\/$/, '');
const liteBase = (args['lite-base'] ?? process.env.LITE_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
const outDir = pathMod.resolve(args.out ?? pathMod.join(repoRoot, 'docs/screenshots/smoke'));

// Pages follow the Design.md *Definition of done*: both variants, all themes.
const spaPages = [
	['/', 'home'],
	['/about', 'about'],
	['/privacy', 'privacy']
];
const spaThemes = ['light', 'dark', 'oled'];
const liteThemes = ['light', 'dark'];
const widths = [375, 1280];

const fail = (msg) => {
	console.error(`FAIL ${msg}`);
	process.exitCode = 1;
};

const badHosts = [
	/^\/(api|lite)(\/|$)/, // /api → FastAPI, /lite → worker proxy; both absent from a pure-static serve
	/^\/(about|privacy|loanwords|conjugations|kanji-group)$/ // clean-URL paths; this host serves them via .html fallback
];
async function spaPage(browser, page, pageName, path, theme, width) {
	const ctx = await browser.newContext({ viewport: { width, height: 900 } });
	// Pin the theme before the pre-paint script reads it — mirrors the app's own storage.
	await ctx.addInitScript((t) => {
		try {
			window.localStorage.setItem('reikun-theme', t);
			document.cookie = `lite_theme=${t === 'light' ? 'light' : 'dark'}; path=/`;
		} catch {
			/* private mode */
		}
	}, theme);
	const pg = await ctx.newPage();
	const errors = [];
	const badPaths = [];
	pg.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
	pg.on('pageerror', (e) => errors.push(String(e)));
	pg.on('response', (r) => {
		if (r.status() < 400) return;
		const pn = new URL(r.url()).pathname;
		if (badHosts.some((re) => re.test(pn))) {
			console.log(`note SPA static-host expected-404: ${pn}`);
		} else {
			badPaths.push(`${r.status()} ${pn}`);
			console.log(`FAIL unexpected HTTP error: ${r.status()} ${pn}`);
		}
	});
	const url = `${spaBase}${path}`;
	const res = await pg.goto(url, { waitUntil: 'networkidle', timeout: 30_000 }).catch((e) => null);
	if (!res || res.status() >= 400) {
		// fall back to .html form for directory-static hosts
		const res2 = await pg.goto(`${url}.html`, { waitUntil: 'networkidle', timeout: 30_000 }).catch(() => null);
		if (!res2 || res2.status() >= 400) {
			fail(`SPA ${path} ${theme}@${width}: HTTP ${res2?.status() ?? 'unreachable'}`);
			await ctx.close();
			return;
		}
	}
	const overflow = await pg.evaluate(
		() => document.documentElement.scrollWidth > window.innerWidth + 1
	);
	if (overflow) fail(`SPA ${path} ${theme}@${width}: horizontal page overflow`);
	for (const e of errors) {
		if (badPaths.length === 0 && e.startsWith('Failed to load resource')) continue;
		fail(`SPA ${path} ${theme}@${width}: console error: ${e.slice(0, 200)}`);
	}
	await pg.screenshot({ path: pathMod.join(outDir, `spa-${pageName}-${theme}-${width}.png`), fullPage: false });
	await ctx.close();
	console.log(`ok   SPA ${pageName} ${theme}@${width}`);
}

async function litePage(browser, pageName, path, theme, width) {
	const ctx = await browser.newContext({
		viewport: { width, height: 900 },
		extraHTTPHeaders: {} // no cookies → default (OS-driven) mode
	});
	if (theme === 'dark') {
		await ctx.addInitScript(() => {
			document.cookie = 'lite_theme=dark; path=/';
		});
	}
	const pg = await ctx.newPage();
	const errors = [];
	pg.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
	pg.on('pageerror', (e) => errors.push(String(e)));
	const res = await pg.goto(`${liteBase}${path}`, { waitUntil: 'networkidle', timeout: 30_000 }).catch(() => null);
	if (!res) {
		console.log(`skip lite ${pageName} ${theme}@${width}: lite not reachable at ${liteBase}`);
		await ctx.close();
		return;
	}
	if (res.status() >= 400) {
		fail(`lite ${path} ${theme}@${width}: HTTP ${res.status()}`);
		await ctx.close();
		return;
	}
	const overflow = await pg.evaluate(
		() => document.documentElement.scrollWidth > window.innerWidth + 1
	);
	if (overflow) fail(`lite ${path} ${theme}@${width}: horizontal page overflow`);
	for (const e of errors) fail(`lite ${path} ${theme}@${width}: console error: ${e.slice(0, 200)}`);
	await pg.screenshot({ path: pathMod.join(outDir, `lite-${pageName}-${theme}-${width}.png`) });
	await ctx.close();
	console.log(`ok   lite ${pageName} ${theme}@${width}`);
}

await mkdir(outDir, { recursive: true });
let chromium;
try {
	chromium = (await import('playwright')).chromium;
} catch {
	console.error('playwright is not installed. Run this once per machine:');
	console.error('  npm i -D playwright && npx playwright install chromium');
	process.exit(1);
}
const browser = await chromium.launch();
try {
	for (const [pathName, label] of spaPages)
		for (const theme of spaThemes)
			for (const width of widths) await spaPage(browser, null, label, pathName, theme, width);
	for (const [pathName, label] of [
		['/lite/', 'home'],
		['/lite/about', 'about']
	])
		for (const theme of liteThemes)
			for (const width of widths) await litePage(browser, label, pathName, theme, width);
} finally {
	await browser.close();
}
if (process.exitCode) {
	console.error('\nSmoke check FAILED — see messages above.');
	process.exit(1);
} else {
	console.log(`\nSmoke check passed. Screenshots in ${outDir}`);
}
