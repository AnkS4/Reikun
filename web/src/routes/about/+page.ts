// SSR on for this route only (root layout disables it): prerender then emits
// real, crawlable HTML for /about/ instead of the empty SPA shell.
export const ssr = true;
