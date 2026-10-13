/**
 * web/src/lib/storage.ts
 *
 * localStorage that never throws. Reading `localStorage` can raise a
 * SecurityError in Safari with "Block all cookies", some in-app browsers
 * (Instagram/Facebook/TikTok webviews), and sandboxed iframes. An unguarded
 * read at module load (like the theme store's `stored()`) takes the whole
 * app down for those visitors.
 */
export const safeStorage = {
	get(key: string): string | null {
		try {
			return localStorage.getItem(key);
		} catch {
			return null;
		}
	},
	set(key: string, value: string): void {
		try {
			localStorage.setItem(key, value);
		} catch {
			/* storage unavailable or full — carry on with in-memory state */
		}
	},
	remove(key: string): void {
		try {
			localStorage.removeItem(key);
		} catch {
			/* ignore */
		}
	}
};
