// Copy the web-facing brand assets from their canonical artwork. A stripped
// checkout (including the web Docker image) uses the committed static mirror.
import { copyFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const assets = fileURLToPath(new URL('../../assets/', import.meta.url));
const output = fileURLToPath(new URL('../static/', import.meta.url));

if (existsSync(assets)) {
	for (const folder of ['emblems', 'favicons', 'icons', 'images']) {
		for (const file of readdirSync(join(assets, folder), { withFileTypes: true })) {
			if (!file.isFile() || (folder === 'emblems' && !file.name.endsWith('.svg'))) continue;
			const dest = folder === 'emblems' ? 'icons' : file.name === 'favicon.svg' ? '' : folder;
			const path = join(output, dest, file.name);
			mkdirSync(dirname(path), { recursive: true });
			copyFileSync(join(assets, folder, file.name), path);
		}
	}
}
