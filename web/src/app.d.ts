// Ambient types for globals Vite injects at build time (vite.config.ts
// `define`), so TypeScript and svelte-check see them without imports.

/** App version, inlined from web/package.json (kept equal to pyproject.toml). */
declare const __APP_VERSION__: string;
