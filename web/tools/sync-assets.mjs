// Sync brand assets from the repo-root assets/ directory into web/static/.
// This script should be run as part of the build process (see package.json).
//
// Portability note: the web Docker build context is `web/` only, so the
// repo-root `assets/` directory is not present inside the image. Since the
// synced files are already committed to web/static/, the script skips the
// copy in that case instead of failing the build (the bash version could
// not be used there: Alpine has no bash and ../scripts is not in context).
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

if (!existsSync(assetsDir)) {
	console.log(`assets/ not found (Docker build context?) — skipping asset sync (${staticDir} is committed).`);
	process.exit(0);
}

console.log(`Syncing assets from ${assetsDir} to ${staticDir}...`);

// Create directories if they don't exist
for (const sub of ['favicons', 'icons', 'images']) {
	mkdirSync(join(staticDir, sub), { recursive: true });
}

// Copy favicon, icon and image files (og-image)
for (const sub of ['favicons', 'icons', 'images']) {
	const src = join(assetsDir, sub);
	const dest = join(staticDir, sub);
	for (const name of readdirSync(src)) {
		if (statSync(join(src, name)).isFile()) cpSync(join(src, name), join(dest, name));
	}
}

console.log('Assets synced successfully.');
