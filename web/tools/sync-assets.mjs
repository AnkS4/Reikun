// Sync brand assets from assets/ into web/static/.
//
// This script should be run as part of the build process (see package.json).
//
// Portability note: the web Docker build context is the repo root, so assets/
// is present in image builds too and the copy is idempotent over the committed
// web/static/. A missing assets/ (e.g. a stripped checkout) silently skips —
// web/static/ is the committed output and stays valid.
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

process.exit(0);