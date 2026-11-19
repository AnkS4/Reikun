#!/usr/bin/env node
/* Mirrors the fonts the SPA requests into web/static/fonts/, built from the
   upstream release archives that produce the fonts themselves. No external
   font service is involved — every byte comes from github.com at fetch time,
   then lives on disk.

   Re-run semantics: existing files are skipped (hash = sha256 of the source
   TTF, so a rebuild after an upstream bump only re-subsets what changed).
   `--check` reports what would be needed without writing anything.
   `--refresh` deletes fonts/files/ and fonts.css first, then writes a clean
   mirror from scratch.

   Usage: node tools/fetch-fonts.mjs [--check] [--refresh]

   To bump an upstream release, edit the SOURCES entry below (one zip per
   family); everything else is derived.
*/
import { createHash } from 'node:crypto';
import { mkdir, writeFile, readFile, rm, access, readdir, stat } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import pathMod from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = pathMod.resolve(pathMod.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = pathMod.join(webRoot, 'static', 'fonts');
const filesDir = pathMod.join(outDir, 'files');
const cssOut = pathMod.join(outDir, 'fonts.css');
const args = new Set(process.argv.slice(2));
const checkOnly = args.has('--check');
const refresh = args.has('--refresh');

// The ranges every family serves. The Japanese ranges live only on the
// JP-superset family — IBM Plex Sans (Latin) and the Devanagari package
// carry no CJK glyphs at all.
const JAPANESE_RANGE = 'U+3000-303F,U+3040-309F,U+30A0-30FF,U+31F0-31FF,U+3400-4DBF,U+4E00-9FFF,U+F900-FAFF,U+FF00-FFEF';

const SUBSETS = [
	['devanagari', 'U+0900-097F,U+1CD0-1CF4,U+1CF7-1CF9,U+200C-200D,U+20A8,U+20B9,U+20F0,U+25CC,U+A830-A839,U+A8E0-A8FF,U+11B00-11B0A'],
	['latin-ext', 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF'],
	['latin', 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD']
];

// Upstream sources, pinned. Exact URLs from the upstream release pages on
// GitHub. Each family contributes only weights the SPA asks for.
const SOURCES = [
	{
		family: 'IBM Plex Sans',
		url: 'https://github.com/IBM/plex/releases/download/%40ibm/plex-sans%401.1.0/ibm-plex-sans.zip',
		weights: [
			[400, 'Regular'],
			[500, 'Medium'],
			[600, 'SemiBold']
		]
	},
	{
		family: 'IBM Plex Sans JP',
		url: 'https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-jp%403.0.0/ibm-plex-sans-jp.zip',
		weights: [
			[400, 'Regular'],
			[500, 'Medium'],
			[600, 'SemiBold']
		],
		subsets: [...SUBSETS, ['japanese', JAPANESE_RANGE]]
	},
	{
		family: 'IBM Plex Mono',
		url: 'https://github.com/IBM/plex/releases/download/%40ibm/plex-mono%402.5.0/ibm-plex-mono.zip',
		weights: [
			[400, 'Regular'],
			[500, 'Medium']
		]
	},
	{
		family: 'IBM Plex Sans Devanagari',
		url: 'https://github.com/IBM/plex/releases/download/%40ibm/plex-sans-devanagari%401.1.0/ibm-plex-sans-devanagari.zip',
		weights: [
			[400, 'Regular'],
			[500, 'Medium'],
			[600, 'SemiBold']
		]
	},
];

async function exists(p) {
	try { await access(p); return true; } catch { return false; }
}

async function fetchToFile(url, dest) {
	const tmp = dest + '.part';
	const res = await fetch(url);
	if (!res.ok) throw new Error(`download ${url}: HTTP ${res.status}`);
	await mkdir(pathMod.dirname(dest), { recursive: true });
	const { writeFile: wf } = await import('node:fs/promises');
	const buf = Buffer.from(await res.arrayBuffer());
	await wf(tmp, buf);
	const { rename } = await import('node:fs/promises');
	await rename(tmp, dest);
	return dest;
}

function unzipDir(zipPath, dest) {
	const r = spawnSync('python3', ['-c', `import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])`, zipPath, dest], { encoding: 'utf8' });
	if (r.status !== 0) throw new Error(`unzip ${zipPath}: ${r.stderr}`);
}

// Recursive find for TTF files under a root, case-insensitive.
async function findTtfs(root) {
	const out = [];
	async function walk(dir) {
		for (const entry of await readdir(dir, { withFileTypes: true })) {
			const full = pathMod.join(dir, entry.name);
			if (entry.isDirectory()) await walk(full);
			else if (/\.ttf$/i.test(entry.name)) out.push(full);
		}
	}
	await walk(root);
	return out;
}

function pickWeightFile(ttfs, weightName) {
	const re = new RegExp(`-${weightName}\\.ttf$`, 'i');
	return ttfs.find((p) => re.test(pathMod.basename(p)));
}

const slug = (s) =>
	s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

async function subsetOne(python, ttf, unicodes, out) {
	const r = spawnSync(python, [
		pathMod.join(pathMod.dirname(fileURLToPath(import.meta.url)), '_subset.py'),
		ttf, unicodes, out
	], { encoding: 'utf8' });
	if (r.status === 2 || (r.status === 0 && Buffer.byteLength(await readFile(out).catch(() => Buffer.alloc(0))) === 0)) {
		// No glyphs in this range — drop the empty output.
		await rm(out, { force: true }).catch(() => {});
		return 'skipped';
	}
	if (r.status !== 0) throw new Error(`subset ${ttf}: ${r.stderr || r.stdout}`);
	// Guard against silently renamed non-WOFF2 output: the served CSS declares
	// format('woff2'), and browsers reject anything else without a word.
	const head = (await readFile(out)).subarray(0, 4).toString('latin1');
	if (head !== 'wOF2') {
		const size = (await stat(out)).size;
		await rm(out, { force: true }).catch(() => {});
		throw new Error(`${out} is not WOFF2 (${size} B, magic ${JSON.stringify(head)}) — subset writer is broken`);
	}
	return 'wrote';
}

async function main() {
	await mkdir(outDir, { recursive: true });

	// Optional full rebuild.
	if (refresh && !checkOnly) {
		await rm(filesDir, { recursive: true, force: true });
		await rm(cssOut, { force: true });
	}
	await mkdir(filesDir, { recursive: true });

	const tmpDir = pathMod.join(outDir, '.tmp-fetch-fonts');
	await rm(tmpDir, { recursive: true, force: true });
	await mkdir(tmpDir, { recursive: true });

	const python = spawnSync('python3', ['-c', 'import fontTools; print(fontTools.__version__)'], { encoding: 'utf8' });
	const pythonBin = python.stdout.trim() ? 'python3' : null;
	if (!pythonBin) {
		console.error('python3 with fontTools not found; install fontTools (pip install fonttools)');
		process.exit(1);
	}

	const entries = [];
	let wrote = 0, skipped = 0, missing = 0;

	for (const src of SOURCES) {
		const zipPath = pathMod.join(tmpDir, slug(src.family) + '.zip');
		const extractPath = pathMod.join(tmpDir, slug(src.family));
		console.log(`== ${src.family}`);
		await fetchToFile(src.url, zipPath);
		await rm(extractPath, { recursive: true, force: true });
		await unzipDir(zipPath, extractPath);

		const ttfs = await findTtfs(extractPath);
		const familySubsets = src.subsets ?? SUBSETS;
		for (const [weight, weightFile] of src.weights) {
			const ttf = pickWeightFile(ttfs, weightFile);
			if (!ttf) {
				console.error(`   MISSING ${weightFile} — no file matching -${weightFile}.ttf`);
				missing++;
				continue;
			}
			const srcHash = createHash('sha256').update(await readFile(ttf)).digest('hex').slice(0, 8);
			for (const [subsetName, unicodes] of familySubsets) {
				const name = `${slug(src.family)}-w${weight}-${subsetName}-${srcHash}.woff2`;
				const dest = pathMod.join(filesDir, name);
				const rel = `files/${name}`;
				let emit = false;
				if (await exists(dest)) {
					skipped++;
					emit = true;
				} else if (checkOnly) {
					console.log(`   would write ${rel}`);
					wrote++;
					emit = true;
				} else {
					const r = await subsetOne(pythonBin, ttf, unicodes, dest);
					if (r === 'wrote') {
						wrote++;
						emit = true;
					}
				}

				if (emit && !checkOnly) {
					entries.push(
						`/* ${subsetName} */\n@font-face {\n` +
							`  font-family: '${src.family}';\n` +
							`  font-style: normal;\n` +
							`  font-weight: ${weight};\n` +
							`  font-stretch: 100%;\n` +
							`  font-display: swap;\n` +
							`  src: url(${rel}) format('woff2');\n` +
							`  unicode-range: ${unicodes};\n` +
							`}\n`
					);
				}
			}
		}
	}

	if (!checkOnly) {
		const header =
			'/* Self-hosted mirror of upstream release archives — generated by\n' +
			'   tools/fetch-fonts.mjs. Do not edit by hand; re-run the tool. */\n\n';
		await writeFile(cssOut, header + entries.join('\n'));
		console.log(`\nwrote ${cssOut} (${entries.length} faces), ${wrote} written, ${skipped} skipped${missing ? `, ${missing} MISSING` : ''}`);
	} else {
		console.log(`\ncheck-only: ${wrote} to write, ${skipped} already present${missing ? `, ${missing} MISSING` : ''}`);
	}
	// Best-effort cleanup: the zips are ~330 MB of transient downloads.
	await rm(tmpDir, { recursive: true, force: true }).catch(() => {});
	if (missing) process.exitCode = 1;
}

main().catch((e) => {
	console.error(e.stack ?? e);
	process.exit(1);
});
