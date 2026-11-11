/**
 * Tiny interface-chrome i18n: English and Japanese.
 *
 * The app is a mixed-language product by design — UI chrome is localized,
 * while JMdict glosses, example sentences and LLM explanations stay English
 * data/content. Only static chrome labels live in the shared i18n/*.json
 * files at the repo root (also used by the Lite UI); keys Lite uses alone
 * are prefixed `lite_`.
 *
 * Initial locale is English so prerendered HTML and the first client render
 * agree; `init()` applies the persisted choice on mount (a preference flash,
 * never a hydration mismatch).
 */
import { browser } from '$app/env';
import { safeStorage } from './storage.ts';
import en from './i18n/en.json';
import ja from './i18n/ja.json';

export const LOCALES = ['en', 'ja'] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_NAMES: Record<Locale, string> = {
	en: 'English',
	ja: '日本語'
};
/** BCP 47 tags used for locale-aware number formatting. */
export const LOCALE_TAGS: Record<Locale, string> = {
	en: 'en',
	ja: 'ja-JP'
};

const KEY = 'reikun-locale';
/**
 * Shared with the lite UI (app/lite.py's `lite_lang` cookie): cookies are not
 * port-scoped, so one language choice follows you across both variants. The
 * cookie is authoritative in both directions, like the furigana preference.
 */
const SHARED_COOKIE = 'lite_lang';
const COOKIE_AGE = 2_592_000; // 30 days — same as lite's _COOKIE_MAX_AGE

function readSharedCookie(): Locale | null {
	if (!browser) return null;
	const m = document.cookie.match(/(?:^|;\s*)lite_lang=(en|ja)(?:;|$)/);
	return m ? (m[1] as Locale) : null;
}

function syncSharedCookie(next: Locale): void {
	if (!browser) return;
	document.cookie = `${SHARED_COOKIE}=${next}; path=/; max-age=${COOKIE_AGE}; samesite=lax`;
}

export type MessageKey = keyof typeof en;

const DICTS: Record<Locale, Record<MessageKey, string>> = { en, ja };

let locale = $state<Locale>('en');
let initialized = false;

function apply(l: Locale): void {
	if (browser) document.documentElement.lang = l;
}

/** Translate a chrome string; interpolation is `{name}`. */
export function t(key: MessageKey, vars?: Record<string, string | number>): string {
	let out = DICTS[locale][key] ?? en[key];
	if (vars) {
		for (const [name, value] of Object.entries(vars)) {
			// A replacer function keeps `$&`/`$'` in user text literal — a
			// string replacement would expand them as replacement patterns.
			out = out.replaceAll(`{${name}}`, () => String(value));
		}
	}
	return out;
}

export const i18n = {
	get locale(): Locale {
		return locale;
	},
	set(next: Locale): void {
		locale = next;
		safeStorage.set(KEY, next);
		syncSharedCookie(next);
		apply(next);
	},
	/** Apply the persisted choice after hydration (SSR starts at English).
	 *  The shared cookie wins: the lite UI writes it server-side, and a pick
	 *  made there must follow into the SPA on the next load. */
	init(): void {
		if (initialized || !browser) return;
		initialized = true;
		const stored = safeStorage.get(KEY);
		const next: Locale =
			readSharedCookie() ?? (LOCALES.includes(stored as Locale) ? (stored as Locale) : 'en');
		locale = next;
		safeStorage.set(KEY, next);
		syncSharedCookie(next);
		apply(next);
	}
};

if (browser) {
	// Cookies have no change event: re-check the shared language on focus so a
	// pick made in the lite UI lands here without a reload.
	addEventListener('visibilitychange', () => {
		if (document.visibilityState !== 'visible') return;
		const c = readSharedCookie();
		if (c !== null && c !== locale) {
			locale = c;
			safeStorage.set(KEY, c);
			apply(c);
		}
	});
	// localStorage changes (another SPA tab) propagate to this tab too.
	addEventListener('storage', (e) => {
		if (e.key !== KEY) return;
		const v = safeStorage.get(KEY);
		if (LOCALES.includes(v as Locale)) {
			locale = v as Locale;
			syncSharedCookie(locale);
			apply(locale);
		}
	});
}
