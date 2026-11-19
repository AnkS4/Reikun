// The kana page reads ?variant=hiragana|katakana from the URL — search
// params are unavailable during prerender, so the page is rendered on the
// client after load (and prerender-safe via the 200.html fallback).
export const prerender = false;
