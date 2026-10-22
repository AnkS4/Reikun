// Query-param browse page (?by=&value=&page=) — nothing meaningful to
// prerender without params. adapter-static's 200.html fallback (and the
// Worker's single-page-application handling) serves this route as a
// client-rendered SPA page instead.
export const prerender = false;
