// Static SPA: the API does all data work, so no SSR. prerender emits a
// shell + 200.html fallback for Pages.
export const ssr = false;
export const prerender = true;
