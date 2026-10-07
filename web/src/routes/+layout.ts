// Everything prerenders at build: ssr emits real HTML per route (title,
// canonical, landing content) so non-JS crawlers see content, not a shell.
export const ssr = true;
export const prerender = true;
