// Sync brand assets and shared i18n tables from the repo-root directories into
// web/static/ and web/src/lib/i18n/ respectively.
//
// This script should be run as part of the build process (see package.json).
//
// Portability note: the web Docker build context is `web/` only, so the
// repo-root `assets/` and `i18n/` directories are not present inside the image.
// Since the synced files are already committed under web/static/ and
// web/src/lib/i18n/, the script skips the copy in that case instead of failing
// the build (the bash version could not be used there: Alpine has no bash and
// ../scripts is not in context).
//
// Note: favicon.svg and favicon.png at the root of web/static/ are manually
// maintained and not synced from assets/ (they are separate 32px versions
// distinct from the favicons/ directory).

import { cpSync, existsSync, mkdirSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const assetsDir = join(here, '..', '..', 'assets');
const staticDir = join(here, '..', 'static');
const i18nDir = join(here, '..', '..', 'i18n');
const i18nDest = join(here, '..', 'src', 'lib', 'i18n');

// Brand assets (favicons, icons, images).
if (existsSync(assetsDir)) {
	console.log(`Syncing assets from ${assetsDir} to ${staticDir}...`);
	for (const sub of ['favicons', 'icons', 'images']) {
		mkdirSync(join(staticDir, sub), { recursive: true });
	}
	for (const sub of ['favicons', 'icons', 'images']) {
		const src = join(assetsDir, sub);
		const dest = join(staticDir, sub);
		if (!existsSync(src)) continue;
		for (const name of readdirSync(src)) {
			if (statSync(join(src, name)).isFile()) cpSync(join(src, name), join(dest, name));
		}
	}
	console.log('Assets synced successfully.');
} else {
	console.log(`assets/ not found (Docker build context?) — skipping asset sync (${staticDir} is committed).`);
}

// Shared UI strings (single source of truth at repo root).
if (existsSync(i18nDir)) {
	console.log(`Syncing i18n from ${i18nDir} to ${i18nDest}...`);
	mkdirSync(i18nDest, { recursive: true });
	for (const name of readdirSync(i18nDir)) {
		if (statSync(join(i18nDir, name)).isFile()) cpSync(join(i18nDir, name), join(i18nDest, name));
	}
	console.log('i18n synced successfully.');
} else {
	console.log(`i18n/ not found (Docker build context?) — skipping i18n sync (${i18nDest} is committed).`);
}

process.exit(0);