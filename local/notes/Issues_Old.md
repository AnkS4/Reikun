# Issues — archive (Streamlit era)

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

Archived out of `Issues.md` to declutter it: these regressions were in the
**Streamlit** app, which was deleted in the Phase-4 migration (`app/ui/`,
`streamlit_app.py`, `.streamlit/` all gone; `web/` is the only frontend), so
none of the symptoms can recur. Kept for the upstream-bug trail and the
workaround lessons. One fix survives as live code — #U8's
`retrieval.is_headword()` still backs `/kanji/random`. Issue IDs (`U<n>`)
match the references left behind in `Issues.md` and `Architecture.md`.

# UI regressions — Streamlit overhaul

Regressions investigated after the interface overhaul (CSS extraction to
`app/ui/style.css`, top navigation via `st.navigation(position="top")`,
`top_bar()` in `app/ui/common.py`).

Six distinct problems were found initially; all had confirmed root causes —
one is an upstream Streamlit frontend bug worked around in-app, and one an
upstream limitation kept as the default. Later finds are appended below
(#U7 from the sticky-search-row work; #U8–#U12 from the kanji-card overhaul
and later passes).

---

## U1. Tooltip text bleeding into the page title

**Symptom.** The app title's rendered/serialized DOM and Streamlit-generated
heading id contained kanji tooltip content — "Meanings …", "On …", "Kun …",
stroke counts — i.e. `<h1 id="reikun-例-訓-meanings-…">`-style pollution.

**Root cause — confirmed.** `render_title()` built the title as

```python
text = f"Reikun ({format_kanji_text('例訓')})"
...
f'<a class="title-home" href="{href}" target="_self">{text}</a>'
```

`format_kanji_text()` wraps each kanji in `<span class="kanji-tip"
tabindex="0">…<span class="kanji-tip-body">tooltip…</span></span>`. `tabindex`
makes each span a **focusable, interactive element**, and interactive content
cannot validly nest inside another interactive element (`<a>`). Browsers
handle the violation inconsistently — effectively splitting the compound
nesting into separate link-like fragments, each carrying a line of the hidden
tooltip bodies. That also poisoned the heading id Streamlit slugs from the
heading text.

**Fix.** The title is a "go home" link, not a dictionary lookup — it does not
need per-kanji tooltips. Render plain escaped text:

```python
text = f"Reikun ({html.escape('例訓')})"
```

`format_kanji_text()`'s docstring now documents the rule: **never nest its
output inside `<a>`/`<button>` or any interactive element.** Verified:
`<h1 id="reikun">` with a single clean anchor.

---

## U2. Dashboard content persisting after navigating to Search

**Symptom.** Clicking **Search** in the top nav after viewing **Dashboard**
left dashboard charts, subheaders, the expander and footer mounted below the
Search page. Search → Dashboard did **not** bleed back.

**Investigation.** Reproduced reliably in headless Chromium
(`leftover: 7` `[data-testid="stVegaLiteChart"]` elements after nav). A long
bisect:

- Minimal two-page apps with the same wrap/structure: **clean** — the app, not
  the pattern.
- Search page reduced to a 3-line stub: **still bleeds** — trigger is
  dashboard-side / shared-code side.
- Dashboard bisect: any chart bleeds; `st.metric` or even `st.write` *before*
  the chart bleeds; chart at index 1 alone is clean. Initially this suggested
  a positional "stale tail" model.
- DOM dump showed the leftovers were **whole element subtrees** inside
  `stMain` — not just a floating Vega tooltip. `#vg-tooltip-element` was
  absent, ruling out the vega-tooltip theory. No `stSidebar` existed, ruling
  out the unrelated duplicate-nav bug (#13224, fixed in the 1.52.x series and
  requiring `st.sidebar` usage anyway).
- Not a race: waiting for the dashboard run to fully finish
  (`stStatusWidget` detached) before navigating still left exactly the tail —
  3 charts (row 3) + expander + footer.
- Wrapping each page in a single `st.empty().container()` did **not** help:
  the stale elements moved *inside* the reused container.

**Root cause — confirmed mechanism, upstream bug.** Reading the compiled
frontend bundle (`streamlit/static/static/js/index.*.js`):

- `addBlock` reuses an existing block at the same path when its `deltaBlock`
  type matches (`flex_container` for `st.container`/`st.columns`), **carrying
  over the old block's children**.
- The new page's children then merge positionally; the old page's **tail
  beyond the new page's child count is never swept** — `clearStaleNodes` only
  prunes inside blocks that get re-visited, and the per-page
  `filterMainScriptElements` cleanup only runs for legacy `pages/` apps where
  `scriptName` changes. `st.navigation` pages share the entrypoint script, so
  it never fires.
- Result: stale nodes are permanently wedged — even a second rerun does not
  remove them (verified).

This belongs to the known element-reuse regression class introduced around
#13849 (see #14249, #14404; fixes #14251/#14406 already shipped in 1.64 but
do not cover this variant). **Worth reporting upstream** with the DOM evidence
above.

**Solutions tried that did not work.**

| Approach | Result |
|---|---|
| `st.container()` page wrapper | Bleed recurs one level down inside the reused block |
| `st.empty().container()` (transient root) | Same — transient wrapper doesn't stop carryover |
| Different block types at root | Only `flex_container` is available for plain containers; other block types (`form`, `expander`, `chat_message`) all change behaviour/UI |
| Padding the shorter page's child count | Would silence this pair but is fragile — any content change silently re-breaks it |
| `st.rerun()` after nav | Stale nodes are already re-stamped/wedged; a second run leaves them |

**Fix that worked — force full page loads for page navigation.** The app's
only cross-page links are the top nav and the title-home link; intercepting
them in the **capture phase** (before React's root listener) and calling
`location.assign(href)` skips the client-side swap entirely:

```javascript
// _NAV_HARD_RELOAD_JS in common.py, emitted once by inject_css()
document.addEventListener('click', function (e) {
  var a = e.target && e.target.closest && e.target.closest(
    'a[data-testid="stTopNavLink"], a.title-home');
  if (a && a.href) {
    e.preventDefault();
    e.stopImmediatePropagation();
    window.location.assign(a.href);
  }
}, true);
window.addEventListener('popstate', function () { window.location.reload(); });
```

Verified: `expect_navigation` confirms real page loads; **0 leftover charts**
Dashboard→Search, **0 leftover inputs** on the return trip. `popstate` covers
browser back/forward (query-param widgets use `pushState`/`replaceState`, not
`popstate`, so intra-page history is unaffected). Trade-off: nav costs a full
reload (~1 s) and drops session state — acceptable for this app; arguably the
desired "home" semantics anyway.

**Why not just keep the smooth client-side swap?** Because in 1.64 the swap
*is* the bug: the frontend reuses the same-position root block and never
sweeps the previous page's tail, so every Dashboard→Search nav leaves
charts, the expander and the footer mounted under the new page. The missed
cleanup lives in the frontend reconciler — there is no app-side way to make
the swap reliable, so a full page load is currently the only deterministic
fix. That is also why the listener intercepts the title-home ("Reikun")
link: a smooth nav there would traverse the same stale-tail path — and the
reload doubles as the intended reset, dropping `last_search` so the hero
view returns (`theme`/`level` ride along as query params). If upstream ever
fixes the sweep, deleting `_NAV_HARD_RELOAD_JS` restores client-side nav —
nothing else depends on it.

**Possible better solutions.**

- **Upstream fix** — report to streamlit/streamlit; the correct fix is in the
  frontend sweep (visit/sweep carried-over block tails on same-script page
  runs, or run `filterMainScriptElements` on `st.navigation` page switches).
- If Streamlit later fixes it, the patch is a no-op — the listener just adds
  a reload; remove it and restore client-side nav if desired.
- Alternative not taken: keep client-side nav but make the two pages' root
  block *types* differ so carryover never engages — rejected because every
  alternate block type has UI/behaviour side effects.

---

## U3. Stylesheet silently never loading

**Symptom (found while investigating #U2).** `.hero` computed
`text-align: left`, zero `kanji-tip` rules in `document.styleSheets`, no
`.stHtml` element in the DOM — **`inject_css()` was a no-op**, so the entire
extracted stylesheet never applied.

**Root cause — two stacked upstream quirks.**

1. `st.html(Path)` wraps the `.css` file in `<style>` and, because the body is
   *style-only* (`_html_only_style_tags`), routes it to Streamlit's **event
   container** — which in 1.64 renders `html` elements as an empty
   `stElementContainer`. The stylesheet was dropped.
2. After re-emitting as `<style>+<script>` (non-style-only → main container),
   the style element was **still stripped by DOMPurify** — the CSS comments
   contained literal `<` sequences (`a <button> is…`, `` `st-key-<key>` ``).
   Verified directly against the app's bundled DOMPurify: `sanitize()` keeps
   a plain `<style>` but drops the whole element when its text parses as
   stray markup.

**Fix.** `inject_css()` now emits one `st.html` whose body is
`<style>{style.css}</style><script>{nav patch}</script>` with
`unsafe_allow_javascript=True` — the script tag defeats the style-only check
so the element lands in the main container, where the style applies and the
script executes. The offending `<` characters were removed from `style.css`
comments, with a warning comment added (a literal less-than sign anywhere in
the file kills the whole stylesheet).

Verified: `.hero` centered (`marginTop` = 12vh), `kanji-tip` rules present in
`document.styleSheets`, one `.stHtml` element rendered.

**Better solution.** If upstream makes event-container `html` elements render
(or adds a proper scoped/global CSS API), revert to `st.html(_CSS_PATH)` or
`st.markdown("<style>…")`. Until then the style+script bundle is the minimal
working form.

---

## U4. `config.toml` font spec crashed the server

**Symptom.** `streamlit run` died with
`StreamlitInvalidThemeOptionError: The source URL specified in the font
property of config.toml contains multiple fonts`.

**Root cause.** `theme.font` accepts a **single** `"Name:stylesheet-url"`
spec — the parser splits on the first colon and rejects a source URL
containing more than one `family=`. The config listed two sourced fonts
(Inter + Noto Sans JP) in one comma-separated string.

**Fix.** The family *name* part may itself be a CSS fallback list, so:

```toml
font = "Inter, 'Noto Sans JP', sans-serif:https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
```

and Noto Sans JP is `@import`ed at the top of `style.css` with
`display=optional` (paint the fallback immediately, never swap — a late CJK
swap visibly shifts glyph boxes, a past source of misalignment). Server
starts clean; full font stack applies.

---

## U5. Stroke-order SVG stripped by `st.html` — replay "button" rendered as empty text

**Symptom.** In the kanji card, the stroke-order animation was invisible and
the "replay button" was just the caption text ("Stroke order · replay") —
no diagram, no clickable control.

**Root cause — confirmed by reading the bundled frontend.** The diagram was
emitted via `st.html(<button>…<svg>…</svg>)`. Streamlit's `Html` component
(`streamlit/static/static/js/Html.*.js`) sanitises the body with DOMPurify
configured as `USE_PROFILES: {html: true}` — the `svg` profile is **not**
enabled, so `<svg>` and its entire subtree are stripped from the output, both
with and without `unsafe_allow_javascript` (the flag only adds `script`/
`style` tags and script attrs to the allowlist; it does not widen the
profile). What survived was an empty `<button>` — which `style.css`
deliberately renders borderless/backgroundless — hence invisible. Only the
`st.markdown` caption below it was left on screen.

**Fix — two parts.**

1. **Render the SVG via `st.markdown(unsafe_allow_html=True)` instead of
   `st.html`.** Markdown is not DOMPurify-sanitised in this version: raw HTML
   goes through `react-markdown` + `rehype-raw`, which parses `<svg>` into
   real DOM elements (verified: no `purify` import in the
   `StreamlitMarkdown.*.js` chunk).
2. **Replay without inline JS.** `onclick` doesn't survive the
   rehype→React prop mapping, so the JS toggle was replaced by a native
   `st.button("Replay")` in `_stroke_diagram()`, an `st.fragment`. The
   button's `on_click` bumps a session counter whose parity flips the
   wrapper class between `.pa`/`.pb`; each maps to an identical keyframes
   pair in `style.css` (`kvg-draw-a/b`, `kvg-fade-a/b`). Browsers won't
   replay an animation whose name didn't change, so the name swap restarts
   the draw on every click. The fragment scopes the button's rerun to just
   this block — a full rerun would close the kanji dialog, since
   `kanji_dialog` consumes its session state on open.

Verified with `AppTest` and in headless Chromium (playwright-core + the
cached `ms-playwright` binary) against a live server: `.stroke-svg` mounts
`stroke-svg pa` with the full `<svg>` (9 paths / 9 `<text>` for 食,
`pathLength` preserved), `stroke-dashoffset` animates to `0`, a native
`Replay` button is visible, and each click alternates the class `pa` ↔ `pb`
and the computed `animation-name` `kvg-draw-a` ↔ `kvg-draw-b`.

**Gotcha that prolonged this bug — stale server.** Browser refreshes kept
showing an *intermediate* build: a visible default-styled checkbox (the
temporary no-JS replay control, unstyled because the emitted markup and the
stylesheet had drifted out of sync) plus a few grey dots — KanjiVG's
hard-coded `fill:#808080` stroke-number texts, while its `stroke:#000000`
paths were invisible on the dark theme without the CSS override. Imported
modules are not re-executed on page reruns (see the restart note below), so
only killing and relaunching the `streamlit run` process loaded the fix; the
card then rendered correctly on first paint. Any change to `common.py`
requires a **server restart**, not just a browser refresh. Launch used:
`uv run streamlit run app/streamlit_app.py --server.headless true` (headless
is also the default in `app/.streamlit/config.toml`; the flag just preserves
the original invocation).

**Note.** A pure-CSS alternative (transparent checkbox + `:has(:checked)`
swapping animation names, no rerun at all) was considered but dropped in
favour of a real visible button — the diagram-only affordance read as "just
text" to users.

---

## U6. Top-nav pills disappear on small screens — sidebar nav takes over

**Symptom.** Narrowing the window below ~768px (any phone-width viewport)
makes the top-nav "Search"/"Dashboard" pills vanish and a left sidebar
appear — collapsed by default, with a `»` expand button in the header —
carrying the same links.

**Root cause — confirmed by reading the bundled frontend.** The
`navigationPosition` sent by the backend (`TOP`, from
`st.navigation(position="top")`) is overridden per-viewport in `App.*`
(compiled `index.*.js`):

```javascript
// navigationPosition passed to AppView:
A = this.props.isMobileViewport ? E.Position.SIDEBAR : O
// isMobile = innerWidth < parseInt(breakpoints.md)   // md = 768px
```

Below the breakpoint `TopNav` is **never mounted** — the fallback is a
React-level branch, not CSS — so the pills cannot be restored with CSS
alone. The override also ignores the requested position entirely: even
`position="hidden"` renders sidebar nav on mobile.

**Attempted workaround — reverted.** `top_bar()` was changed to emit a
`.mobile-nav` pill row (plain `<a>` anchors to `/` and `/dashboard`, active
state from a passed page slug) shown only under
`@media (max-width: 767.98px)`, while `[data-testid="stSidebar"]` and
`stExpandSidebarButton` were `display:none`; the pills' element wrapper was
hidden above the breakpoint via `:has()` + `display: contents`. Verified
working in headless Chromium at 390px (custom pills, no sidebar) and
1200px (native pills, zero footprint). **Reverted anyway:** the replacement
row lives in the page flow under the status/theme strip rather than in the
header like the native pills, and never aligned well enough — Streamlit's
default mobile sidebar was kept instead.

**Status.** Accepted default behaviour. Revisit if upstream makes the top
nav responsive or exposes the mobile breakpoint; the reverted approach is
described above if it ever becomes worth retrying.

---

## U7. `position: sticky` search row silently scrolled away

**Symptom.** `.st-key-query_row { position: sticky; top: 0 }` computed as
sticky but the row scrolled off with the rest of the page — it never stuck.

**Root causes — all verified in headless Chromium (1.64).**

1. **Containing block too small.** Streamlit wraps the keyed container in a
   `stLayoutWrapper` exactly the row's height. A sticky element can only
   travel inside its parent's box, so it had zero room. Fix: put the sticky
   on the parent via `div:has(> .st-key-query_row)` (same `:has()`
   parent-targeting the reverted mobile-nav workaround used).
2. **`top: 0` pins under the app header.** `stHeader` is
   `position: absolute`, fixed 3.75rem height, z-index ~999990, outside the
   `stMain` scroll container. `top` must be `3.75rem`, not `0`.
3. **No theme-safe background colour exists.** 1.64 exposes no CSS custom
   properties (`--background-color`/`--primary-color` etc. are all unset on
   `:root`, `body`, `.stApp`) and `color-scheme` is `normal`, so neither a
   `var()` fallback nor `Canvas` can match both themes — an opaque
   `var(--background-color, #fff)` paints a **white band in dark mode**
   (verified). The same latent bug already existed in `.kanji-tip-body`.
   Fix: `backdrop-filter: blur(14px) saturate(1.4)` instead of any
   background colour — theme-adaptive, zero JS.

**Related latent bug fixed in the same pass.** `.kanji-big` computed at
16px, not the intended clamp: Streamlit's emotion rule
`.st-emotion-cache-* p { font-size: inherit }` (class+element specificity)
beats a bare `.kanji-big` class. Selector is now `.stMarkdown .kanji-big`.

**Related dark-theme bug fixed later.** An OPEN tertiary popover trigger
(the Theme button) paints its label in a *darkened* primary —
`rgb(20,29,41)` in both themes — ~1.1:1 on `#15171A`, i.e. invisible.
`tertiaryColor`/`tertiaryTextColor` are derived from `primaryColor` in the
frontend and are **not** `config.toml` options in 1.64, so there is no
theme-side fix. `color: inherit` on
`[data-testid=stPopover] button[kind=tertiary][aria-expanded=true]`
restores readable text colour in both themes. (Still open, milder:
`st.segmented_control`'s selected option is `#3D5A80` text on a 10% accent
tint — ~2.9:1 in dark.)

**Still open — `.kanji-tip-body` stays light in dark theme.** The kanji
tooltip card (`background: var(--background-color, #fff)` — the var is unset,
so it is always white) is the same "no theme CSS vars" bug as the sticky row
in point 3. An attempted fix was reverted: read `stActiveTheme-*` from
localStorage in `inject_css()`'s script, set `data-reikun-theme` on `<html>`,
and switch `--tip-bg`/`--tip-fg` CSS vars — verified flaky on theme switch
(the attribute/script timing does not reliably track the picker's reload, so
the card could stay dark after switching back to light). No reliable fix
short of hard-coding per `?theme=` param or upstream exposing theme vars;
a wrong-colour card on switch is worse than a consistently light one.

---

## U8. First random-kanji click stalled for seconds

**Symptom.** The first click on the shuffle button took seconds; every later
click was instant. Reported with timings "embed 99 ms · retrieve 47 ms" —
i.e. the search itself was never the cost.

**Root cause.** `_random_kanji()` restricted picks to standalone words via
`random_kanji(within=headword_index())`. `headword_index()` (an `lru_cache`d
dict of every written form of every entry → minimal info, built for
`segment_japanese()` compound-query splitting) scrolls the entire Qdrant
collection — ~40 sequential payload-only requests for ~37k points — on its
first call. The shuffle button was borrowing it as a membership test. The
per-search result cache (`_search_cached`) was not involved; removing it
would only have made repeat picks slower.

**Fix.** `retrieval.is_headword(term)`: one filtered `count` on
`kanji_form`/`kanji_forms` per candidate (~1–5 ms; ~75% of frequency-ranked
kanji are headwords, so ~1.3 expected tries, capped at 8 before falling back
to an unrestricted pick). `headword_index()` now only builds when a compound
Japanese query actually needs segmentation.

**Post-migration note.** The UI that stalled is gone, but the fix itself is
live API code: `retrieval.is_headword()` still backs `/kanji/random`, and
`headword_index()` still builds lazily on first compound-ja query.

**Recommendation.** If the remaining ~5 ms per click is ever worth removing:
mark `"is_word"` in `build_kanji_table()` (true when some chunk has
`kanji_form == literal`) and filter `_common_kanji()` locally — zero network
calls. Requires a `kanji_table.json` rebuild; batch it with other data-side
changes (e.g. common-word ordering) rather than rebuilding for this alone.

---

## U9. Theme picker spacing, and a pure-black option

**Symptom.** Opening the Theme (and JLPT) popover showed a redundant
"Theme"/"JLPT level" label above the options with a gap that read as broken
spacing. Also requested: a pure-black theme.

**Fix — spacing.** Compact styling on `[data-testid="stPopoverBody"]`
(padding .4rem, min-width 0, fit-content). Dead ends: `help=` renders a `?`
tooltip icon that forces the widget label row to stay mounted even with the
label hidden — an empty 24px strip at the top of the popover; and
`label_visibility="hidden"` only applies `visibility:hidden`, keeping the
label's box (the same nonuniform gap as `"collapsed"`). Final form: visible
`Theme`/`JLPT level` labels doubling as the popover title, no `help` text.

**Fix — Black theme: tried, reverted.** Streamlit has exactly two theme
slots (`[theme.light]`/`[theme.dark]` in `config.toml`), and the frontend's
`stActiveTheme-<path>-v2` localStorage only accepts the names
`System`/`Light`/`Dark` (verified in the theme chunk — `Custom Theme *`
names just map back to those three; a custom palette can't be persisted
client-side). So "Black" could only ever be an app-side CSS override keyed
off our own state.

**Channels tried for that state, in order.**
1. `?theme=Black` param — `bind="query-params"` never wrote it (verified in
   AppTest: params stayed empty after the pick), and top-nav links carry no
   params anyway.
2. `session_state` — doesn't survive `location.reload()` (this app relies on
   that: reload = "home" semantics), so the pick was unobservable on the
   post-reload run.
3. `reikun_theme` cookie (`path=/`, read via `st.context.cookies`) — the one
   channel that survives reloads *and* page nav *and* is server-readable.
   This worked: Black applied on every page and the picker stayed in sync.

**Why it was still reverted.** The override is an app-side `<style>` that
only lands when `inject_css()` runs — *after* Streamlit's emotion styles have
already painted the dark shell (`#15171A`). Every nav is a full page load
(see #U2: the stale-tail workaround), so every Search ↔ Dashboard switch
showed a visible dark→black repaint. No earlier injection point exists
(app-side). The paint over also needed `stMain`, `stMainBlockContainer`,
`stHeader`, `stSidebar`, `stToolbar`, `stBottom`… — any missed surface left
`#15171A` islands.

**Kept from the work.** The all-keys `stActiveTheme-*` write in
`apply_theme()` (fixes cross-page persistence for Dark/Light/System — the
key is per-path) and the collapsed popover labels.

**Recommendation.** If pure black is ever wanted: the only zero-glitch route
is making it *the* dark theme — `[theme.dark] backgroundColor = "#000"` —
giving up the soft-dark option. A coexistence of both would need upstream
support for persisted custom themes, or serving a modified `index.html`
shell (not supported by `streamlit run`). For other theme-dependent surfaces
(e.g. the still-light `.kanji-tip-body` per #U7), the `reikun_theme`-cookie
approach in `inject_css()` is the reliable channel if revisited.

---

## U10. Status/theme controls onto the hero title row — and why not the nav row

**Ask.** Dashboard puts the KB-status badge + theme popover on the title row
(`header()` non-hero branch); the Search hero instead rendered them on a
right-aligned strip *above* the centred title. Could they share the hero
title's row — or better, the top-nav row next to the Search/Dashboard pills?

**Nav row: not possible natively (1.64).** The header chrome is
frontend-owned: `stTopNav` renders the `st.navigation` pills, `stToolbar`
holds only Streamlit's own ⋮ menu (`client.toolbarMode` merely collapses
it), and `st.logo` is image-only, upper-left. No API injects widgets into
`stHeader`; only CSS positioning / JS DOM moves could — the same hack class
as the reverted mobile-nav workaround (#U6). Plus on <768 px the top nav
itself unmounts (#U6), so controls parked there would vanish on phones.

**Hero title row: done, no CSS — one shared horizontal row.** `header()`
now runs a single code path for hero and compact alike:
`[title (stretch)][pair (content)]` — the badge + theme as a tight
`gap="xsmall"`, `width="content"` pair at the title's right. The title's
text stays centred *within* its column, i.e. ~half the pair's width (~38 px)
left of the page axis — imperceptible in practice, and the pair never
leaves the title's row at any viewport (heading is only ~128 px wide at
phone font sizes; safe down to ~250 px, below which the pair wraps under
the title right-aligned).

Alternatives measured and rejected (compiled bundle + headless Chromium):

- Child width semantics in a horizontal container: `stretch` →
  `flex: 1 1 8rem` for containers (`minStretchWidth` MEDIUM; elements vary),
  `content` → `flex: 0 0 fit-content` — **unshrinkable**. A content-width
  hero title (~704 px, the tagline's max-content) + controls overflows the
  736 px column and wraps the row, scattering the controls.
- **Empty `st.container`s emit no flex item at all** — flanking spacer
  containers never render. `st.space(px)` does render (`flex: 0 0 Npx`).
- `[badge][title stretch][theme]` centred within ~2 px but split the pair
  (badge left edge, theme right).
- `[space 61][title stretch][pair]` was exact on desktop but the fixed
  counterweight can't yield on phones — at 390 px 例訓 broke across two
  lines. Python can't see the viewport (`st.context` has no width).
- `st.columns([1, 6, 1])` held exact centre on desktop, but `wrap=True`
  (default) stacks the columns below 640 px — the pair stranded on its own
  strip under the tagline; `wrap=False` instead gave each column a min
  width and let the group scroll off-screen (pair clipped at 390 px).
- `st.sidebar` was ruled out on principle: any sidebar content brings the
  drawer back on desktop, hiding the controls behind `»` on every viewport.

Verified: hero centred-with-pair at 1280/390/360 px, heading one line on
phones; Dashboard and compact-Search headers unchanged (pair gap 16→8 px
only); theme pick + reload works from the new spot.

---

## U11. "Press Enter to apply" hint on the search box — no display toggle exists

**Ask.** Remove the "Press Enter to apply" hint that `st.text_input` shows
under the box while the text is dirty (typed but not yet committed). Moved
from Plan.md: investigated, documented, not done.

**Root cause — hard-coded in the frontend.** The hint is the
`InputInstructions` component (`data-testid="InputInstructions"`). Its only
gate is `allowEnterToSubmit`, which for a non-form input resolves to
`dirty && !liveDebounceMs` — i.e. "show the hint whenever an uncommitted
value exists and the input can't live-commit". Inside `st.form` it instead
follows the form's enter-to-submit setting and reads "Press Enter to submit
form". `st.text_input` has no parameter to hide it.

**The one native lever changes behaviour, not display.** `live=` (new in
1.64: `True` = 250 ms pause, or a duration string) sets `liveDebounceMs`,
which suppresses the hint — verified: the element renders empty while
typing. But it suppresses it *because Enter is no longer needed*: every
typing pause commits the value and fires a rerun. In this app that means a
partial-query `search()` per pause (Qdrant + possibly the Cohere rewrite)
and `?q=` churning mid-word — `bind="query-params"` turns each pause into a
URL write. That is a live-search redesign with real per-keystroke cost, not
a cosmetic fix. `live` + `on_change="ignore"` stops the reruns but makes
Enter inert too (ignore covers all commits) — the box would only respond to
the 🔍 button, which is worse UX for a search-first page.

**Remaining option — declined.** `[data-testid="InputInstructions"] {
display:none }` is one CSS rule and works, but the project rule is that
`data-testid` is not a public API (style.css header); the only sanctioned
hook is `st-key-*`, and there is no keyed wrapper around the instructions
element. Also worth keeping in mind: the hint is an honest affordance —
Enter does submit — and with `type="search"` the native ✕ already handles
clearing.

**Status.** Accepted as-is. If upstream ever adds an option to hide the
instructions (or a per-widget `st-key-*` lands on it), revisit.

---

## U12. `example_row`'s `level` global — safe only while the picker stays on the full-rerun path

**Caveat, not a bug — documented so it isn't discovered by accident.**

Streamlit's rerun model: a widget interaction normally reruns the whole
script top-to-bottom; the exception is `@st.fragment`, whose own widgets
rerun *only that fragment*. `example_row()` (a fragment) reads the
module-level `level` in `search.py` — computed once per full run above the
query row — for its button labels, `explain_grammar_stream()` arg, and the
stored `expl["level"]`. On a fragment-scoped rerun Python re-executes the
function with the *current* module global, which is still the value from
the last **full** run — not whatever a level widget may now hold.

It is correct today only because the JLPT `segmented_control` lives at top
level (inside `row.popover` — containers and popovers do not create
fragment scope; only `@st.fragment` does). Picking a level therefore
always triggers a full rerun that re-evaluates `level` *before* the
fragments re-render. If the picker is ever moved into a fragment (e.g.
the query row becomes one), the explain labels and stream would silently
use a stale level until the next unrelated full rerun.

General rule: **any module global read inside a fragment is a snapshot of
the last full run.** The fix, if needed, is to read the level inside the
fragment itself (`st.session_state.level`, or `st.query_params["level"]`),
not to pass the global in.

Same pattern already handled correctly elsewhere: `_stroke_diagram`'s
replay counter is read via `st.session_state` inside the fragment, which
is current on every scoped rerun.

---

## Working notes (Streamlit dev loop)

- Shared-module edits (`common.py`) are not picked up by a running server —
  **restart** before validating. Why: Streamlit's rerun model re-executes
  only the page script on each run, while Python keeps imported modules
  cached in `sys.modules` — a rerun does not re-import them, and the
  file-watcher's "source changed" prompt only offers a rerun, which changes
  nothing. Before the CSS/helpers extraction, that code lived *inside* the
  page scripts, so every rerun picked edits up automatically; moving it to
  `app/ui/common.py` is what made restarts necessary. Beware the half-stale
  state: `inject_css()` re-reads `style.css` from disk on every run, so a
  CSS-only edit *does* apply on refresh — and stale Python markup mixed with
  fresh CSS is exactly what produced the "visible checkbox + stray dots"
  screen during issue #U5. Applies unchanged to the uvicorn API today —
  it also caches imported `app/` modules and has no auto-reload, so an
  edit to e.g. `retrieval.py` serves stale results until restarted
  (surfaced during the #S6 fixes: the running server kept returning the
  old parse until the process was recycled).
- The Search page is the default page (`url_path=""`, served at `/`); a
  direct `/search` URL shows Streamlit's "Page not found" dialog over the
  main page — an overlay that swallows clicks and looks like a UI bug.
- Repro harness used throughout: Playwright + Chromium, navigating
  `stTopNavLink` clicks and counting `[data-testid="stVegaLiteChart"]` /
  `[data-testid="stTextInputField"]` after the run finishes
  (`stStatusWidget` detached).
