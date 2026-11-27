// The /es page reads ?q= from the URL — search params are unavailable during
// prerender, so the page renders client-side from the 200.html fallback (same
// treatment as /kana). Nothing links here yet either, so it's also an unseen
// route for the prerender crawler (vite.config.ts ignores those).
export const prerender = false;
