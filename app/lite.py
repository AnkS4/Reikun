"""
JavaScript-free, server-rendered UI ("lite") — the DuckDuckGo-Lite-style
counterpart of the SvelteKit frontend.

Every page is one small HTML document built here; all interaction is a link or
a ``method="get"`` form, so search, kanji pages and kanji browsing work with
JavaScript disabled, in text browsers, and on slow connections. The JSON API
(``app/api.py``) is untouched: this module reuses the same retrieval/render
layer and only replaces the JSON-to-DOM step.

SPA parity: the home page keeps the full interface's hero (badge + brand +
tagline + LITE tag), example/recent search pills, random-kanji button and
furigana toggle. None of those need JS: the random button is a plain
``formaction`` submit, and the furigana preference, the recent-searches list
and the theme choice live in three first-party cookies that plain links or the
search response set and flip — no script, storage API or event handler.

Routes (mounted by ``app/api.py``):

    GET /lite                  search box + hero, examples / recent searches
    GET /lite/search?q=…       results (auto pipeline; single kanji → card)
    GET /lite/furigana         flip the furigana preference, redirect back
    GET /lite/theme            set the theme choice cookie, redirect back
    GET /lite/recent/clear     empty the recent-searches cookie, redirect back
    GET /lite/conjugations     conjugation table for one word
    GET /lite/kanji/{char}     KANJIDIC2 card + static KanjiVG stroke diagram
    GET /lite/kanji/random     redirect to a random kanji card
    GET /lite/kanji/group      browse kanji sharing strokes/grade/JLPT
    GET /lite/about            project + data-licence note

No templating dependency is used on purpose: pages are plain f-strings with
``html.escape`` on every piece of dynamic text, so the lite layer stays as
small and dependency-free as the promise it makes.
"""

import html
import json
import logging
from typing import cast
from urllib.parse import quote, unquote, urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.config import RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS, WEB_BASE_URL
from app.grammar_explain import JLPT_LEVELS
from app.kanji_lookup import is_kanji, jlpt_kanji, kanji_in, random_kanji
from app.ratelimit import rate_limited
from app.render import furigana_parts, kanji_card, kanji_group_cards, related_words, segment_chip
from app.retrieval import MAX_JA_QUERY_CHARS, SearchResponse, is_headword, search
from app.telemetry import telemetry

logger = logging.getLogger("reikun.lite")

# HTML pages, not JSON API surface — keep them out of /docs and the generated
# frontend types.
router = APIRouter(tags=["lite"], include_in_schema=False)

_search_limit = Depends(rate_limited(RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS))

# Static dictionary data: safe for browsers/CDNs to reuse for a day (same
# policy as the JSON API). Pages carrying a theme cookie render cookie-specific
# CSS, so `_page` downgrades this to a private cache.
_CACHE_STATIC = "public, max-age=86400, stale-while-revalidate=604800"

# Branding mirrors web/src/lib/brand.ts (same phrase in every locale); the
# tagline drops the grammar-explanation clause because Lite has no LLM path.
_BRAND_SUBTEXT = "Semantic Japanese Dictionary & Reading Assistant"
_TAGLINE = "Search in English or Japanese, break down sentences word-by-word with furigana and meanings, inspect kanji."
# Same starter queries as web/src/routes/+page.svelte.
# Example/recent-search pills below the search bar — the same list as
# web/src/routes/+page.svelte's EXAMPLES (update both together), kept strictly
# alternating Japanese/English so the row reads with a consistent rhythm. Each
# pill exercises a different retrieval path: single kanji, English noun,
# kanji+okurigana verb, English infinitive phrase, two-kanji compound,
# natural-language question, Japanese sentence.
_EXAMPLES = [
    "光",
    "courage",
    "咲く",
    "to walk",
    "大君",
    "How do you say rain in Japanese",
    "あの山の頂上は雪で覆われています。",
]
# Same themes as the SPA, minus the explicit "system" option: with no cookie,
# the page follows prefers-color-scheme. Legacy cookie values map over.
_THEMES = ("light", "dark")

_FURI_COOKIE = "lite_furi"
# Shared with the full version: web/src/lib/theme.svelte.ts mirrors the SPA's
# appearance choice into this same cookie (dark and oled both → "dark"), and
# app.html's inline script falls back to it before first paint — cookies are
# not port-scoped, so one choice follows you across both variants.
_THEME_COOKIE = "lite_theme"
_RECENT_COOKIE = "lite_recent"  # shared channel with the web UI — web/src/lib/recent.ts
_COOKIE_MAX_AGE = 2_592_000  # 30 days, same order as the SPA's localStorage
MAX_RECENT = 8  # matches web/src/lib/recent.ts — one shared list, one cap
_RECENT_MAX_CHARS = 150  # per-entry cap, identical to recent.ts
# A cookie rides in request headers and browsers cap it near 4 KB; capping the
# percent-encoded value far below that keeps both writers safe, whatever the
# queries (multibyte Japanese expands 3x when encoded).
_RECENT_COOKIE_BUDGET = 2400


def _read_furi(request: Request) -> bool:
    """Furigana is on unless the preference cookie says otherwise."""
    return request.cookies.get(_FURI_COOKIE, "1") != "0"


def _read_theme(request: Request) -> str:
    """No cookie → system (prefers-color-scheme decides); an explicit choice
    pins the palette. Old "oled" cookies resolve to dark."""
    value = request.cookies.get(_THEME_COOKIE, "")
    if value in ("dark", "oled"):
        return "dark"
    return "light" if value == "light" else "system"


def _read_recent(request: Request) -> list[str]:
    try:
        value = json.loads(unquote(request.cookies.get(_RECENT_COOKIE, "") or "[]"))
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and 0 < len(item) <= _RECENT_MAX_CHARS][:MAX_RECENT]


def _recent_cookie_value(current: str, query: str) -> str:
    """Most-recent-first, de-duplicated, capped — the same shape
    web/src/lib/recent.ts writes. The shared cookie is read by both variants,
    so keep the percent-encoded value inside the budget: drop stale entries
    (oldest first) and over-long inputs instead of risking the browser's
    cookie-size limit, which would silently lose the whole list."""
    try:
        previous = [item for item in json.loads(unquote(current or "[]")) if isinstance(item, str)]
    except Exception:
        previous = []
    items = [query, *(item for item in previous if item != query and 0 < len(item) <= _RECENT_MAX_CHARS)]
    items = [item for item in dict.fromkeys(items) if item][:MAX_RECENT]
    encoded = quote(json.dumps(items, separators=(",", ":")), safe="")
    while len(encoded) > _RECENT_COOKIE_BUDGET and len(items) > 1:
        items.pop()  # oldest last
        encoded = quote(json.dumps(items, separators=(",", ":")), safe="")
    return encoded


def _current_path(request: Request) -> str:
    path_and_query = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return quote(path_and_query, safe="/?.=&%_-~")


def _safe_next(next_url: str | None) -> str:
    # Sites-only redirect: a /lite… path may carry a query, but never a domain.
    if next_url and next_url.startswith("/lite") and not next_url.startswith("//"):
        return next_url
    return "/lite"


# ── Small HTML helpers ───────────────────────────────────────────────────────

def esc(value: object) -> str:
    """Escape any value for HTML text/attribute context."""
    return html.escape("" if value is None else str(value))


def _href(path: str, **params: object) -> str:
    """Build a link with escaped query parameters (empty values omitted)."""
    query = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    return f"{path}?{esc(query)}" if query else path


def _ruby(parts: list[dict], furi: bool = True) -> str:
    """Render furigana parts as native <ruby> — the browser does the rest.
    With the preference off, render base text only (no <rt> annotation)."""
    out = []
    for part in parts:
        text = esc(part.get("text"))
        rt = part.get("rt")
        out.append(f"<ruby>{text}<rt>{esc(rt)}</rt></ruby>" if rt and furi else text)
    return "".join(out)


def _badge(badge: dict) -> str:
    label = esc(badge.get("label"))
    tip = esc(badge.get("tip"))
    group = badge.get("group")
    if group:
        href = _href("/lite/kanji/group", by=group.get("by"), value=group.get("value"))
        return f'<a class="badge" href="{href}" title="{tip}">{label}</a>'
    return f'<span class="badge" title="{tip}">{label}</span>'


# Theme palettes lifted from web/src/app.css — the SPA's light tokens (warm
# washi canvas) and its pure-black OLED canvas as the single dark choice.
# "system" (no cookie) resolves via prefers-color-scheme, exactly like the
# SPA's system choice does.
_LIGHT_VARS = """:root{color-scheme:light;--bg:#fcfaf6;--fg:#161514;--muted:#665f56;
--line:rgba(45,38,30,.12);--link:#1f4874;--warn:#b87728}"""
_DARK_VARS = """:root{color-scheme:dark;--bg:#000000;--fg:#ffffff;--muted:#b5b5b5;
--line:rgba(255,255,255,.14);--link:#85b8ea;--warn:#fb923c}"""
_SYS_VARS = f"""{_LIGHT_VARS}
@media (prefers-color-scheme:dark){{{_DARK_VARS}}}"""

# The kanji font stack makes full CJK rendering explicit instead of hoping the
# US-centric `system-ui` chain wins for every glyph on every platform.
_CSS_MAIN = """
*{box-sizing:border-box}
/* Body metrics mirror the SPA's main container (web/src/app.css): 50rem
   column, same side padding and bottom scroll room — more air, same rhythm. */
body{margin:0 auto;padding:1.25rem 1.25rem 4rem;max-width:50rem;background:var(--bg);color:var(--fg);
font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
body,[lang=ja]{font-family:system-ui,-apple-system,"Segoe UI",Roboto,
"Hiragino Sans","Hiragino Sans Kaku Gothic ProN","Yu Gothic","Noto Sans JP",Meiryo,sans-serif}
a{color:var(--link)}
header{display:flex;align-items:baseline;gap:.5rem;margin-bottom:.35rem}
header.hero{display:block;text-align:center;margin:3rem 0 .35rem}
.hero-tag{display:inline-block;font-size:.7rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:.1rem .65rem;margin:0 0 1.25rem}
.hero-title{margin:0}
.hero .brand{font-size:2.4rem}
.tagline{color:var(--muted);font-size:1.05rem;max-width:34rem;margin:.85rem auto 0}
.brand{font-size:1.35rem;font-weight:700;text-decoration:none;color:var(--fg)}
.brand span{font-size:.8em;font-weight:400;color:var(--muted)}
.tag{font-size:.72rem;color:var(--muted);border:1px solid var(--line);border-radius:3px;
padding:0 .35rem;text-transform:uppercase;letter-spacing:.06em}
.controls{position:absolute;top:.6rem;right:.9rem;z-index:5;display:flex;flex-wrap:wrap;
gap:.25rem;align-items:center;justify-content:flex-end;font-size:.85rem;margin:0}
/* Top-right icon buttons, mirroring the SPA's header cluster: same 2rem round
   hit area, muted until hover. Titles + aria-labels carry the meaning text
   once did. */
.controls .icon-link{display:inline-flex;align-items:center;justify-content:center;
width:2rem;height:2rem;border-radius:999px;color:var(--muted)}
.controls .icon-link:hover{color:var(--fg);background:var(--line)}
.controls svg{display:block}
/* System mode renders both directions and this hides the one matching the OS
   scheme — a first visit shows exactly one button, e.g. the moon on a light OS.
   Specificity note: these selectors must outrank `.controls .icon-link`. */
.controls .theme-toggle a{display:none}
@media (prefers-color-scheme:light){.controls .theme-toggle a.to-dark{display:inline-flex}}
@media (prefers-color-scheme:dark){.controls .theme-toggle a.to-light{display:inline-flex}}
h1{font-size:1.5rem;margin:0 0 .6rem}
h2{font-size:1.2rem;margin:.4rem 0 .35rem}
form.search{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:1.25rem 0 1.5rem}
input,textarea,select,button{font:inherit;color:inherit;background:transparent;
border:1px solid var(--line);border-radius:4px;padding:.45rem .6rem}
input[name=q]{flex:1 1 18rem}
button{cursor:pointer}
button[type=submit]{padding:.45rem 1.1rem}
.btn{display:inline-block;border:1px solid var(--line);border-radius:4px;padding:.44rem .7rem;
text-decoration:none;white-space:nowrap;color:var(--fg)}
.btn:hover{border-color:var(--link);color:var(--link)}
.furi.off{text-decoration:line-through;color:var(--muted)}
.pills{display:flex;flex-wrap:wrap;gap:.45rem;margin:.35rem 0 1.25rem;padding:0}
.pill{display:inline-block;border:1px solid var(--line);border-radius:3px;padding:.15rem .6rem;
text-decoration:none}
.pill:hover{border-color:var(--link);color:var(--link)}
.pills-label{margin:1.4rem 0 .35rem;color:var(--muted);font-size:.9rem}
.pills-label a{margin-left:.6rem}
.entry{border-top:1px solid var(--line);padding:1.25rem 0}
.entry:first-of-type{border-top:0}
ruby rt{font-size:.55em;color:var(--muted)}
.gloss{margin:.5rem 0}
.reading-note,.muted{color:var(--muted);font-size:.9rem}
.warn{color:var(--warn)}
.badge{display:inline-block;font-size:.75rem;color:var(--muted);border:1px solid var(--line);
border-radius:3px;padding:0 .35rem;margin:0 .25rem .25rem 0;text-decoration:none}
.badge:hover{border-color:var(--link);color:var(--link)}
.example{margin:.75rem 0 .35rem .75rem;padding-left:.75rem;border-left:2px solid var(--line);
font-size:.92rem}
.example p{margin:.15rem 0}
/* Sentence Breakdown card — the SPA's SegChips: mono header with hint, then
   vertical tiles (word over gloss). approx tiles get dashed borders. */
.seg-card{border:1px solid var(--line);border-radius:8px;padding:.9rem 1.1rem;margin:1.25rem 0 1.5rem}
.seg-header{display:flex;align-items:center;justify-content:space-between;gap:.75rem;
flex-wrap:wrap;margin-bottom:.65rem}
.seg-title{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.72rem;
font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0;
display:flex;align-items:center;gap:.35rem}
.seg-title .badge{margin:0}
.stats-meta{font-size:.75rem;color:var(--muted)}
.seg-row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:stretch}
.seg{display:flex;flex-direction:column;text-decoration:none;padding:.4rem .65rem;
border:1px solid var(--line);border-radius:4px;text-align:center}
.seg:hover{border-color:var(--link)}
.seg.approx{border-style:dashed}
.seg-word{display:flex;align-items:flex-end;justify-content:center;font-size:1.25rem;
min-height:2.2rem;font-weight:500;color:var(--fg)}
.seg-word rt{font-size:.6em}
.seg-mean{display:block;font-size:.72rem;color:var(--muted);margin-top:auto;padding-top:.2rem;
line-height:1.3;max-width:9.5em}
table.conj{border-collapse:collapse;margin:.75rem 0}
table.conj th,table.conj td{border:1px solid var(--line);padding:.3rem .55rem;text-align:left}
/* Kanji card — two-column like the SPA's KanjiCard: glyph + stroke diagram +
   badges on the left, meanings/readings/common-words on the right. */
.kanji-card{display:flex;gap:1.75rem;border:1px solid var(--line);border-radius:10px;
padding:1.5rem;margin:1.25rem 0 1.5rem}
.kanji-left{width:11rem;flex-shrink:0;display:flex;flex-direction:column;align-items:center}
.kanji-right{flex:1;min-width:0}
.kanji-glyph{font-size:4.25rem;font-weight:400;line-height:1;margin:0 0 .75rem;text-align:center;
color:var(--fg);letter-spacing:.02em}
/* Stroke diagram in the SPA's boxed style, with its dashed practice-sheet
   quadrant guides drawn as pseudo-elements. */
.stroke-box{position:relative;width:100%;border:1px solid var(--line);border-radius:8px;padding:.5rem}
.stroke-box::before,.stroke-box::after{content:"";position:absolute;pointer-events:none}
.stroke-box::before{left:.5rem;right:.5rem;top:50%;border-top:1px dashed var(--line)}
.stroke-box::after{top:.5rem;bottom:.5rem;left:50%;border-left:1px dashed var(--line)}
.stroke-box svg{display:block;width:100%;height:auto}
/* KanjiVG `d`s are stroke outlines — draw them as thin lines like the SPA's
   StrokeSvg (fill:none + stroke), not filled shapes. */
.strokes path{fill:none;stroke:currentColor;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round}
.strokes text{fill:var(--muted);font-size:9px;text-anchor:middle}
.kbadges{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.85rem;justify-content:center}
.kbadges .badge{margin:0}
.ksection{margin-bottom:1rem}
.ksection-title{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.72rem;
font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 .35rem}
.meanings{margin:.1rem 0 .75rem;font-size:1.35rem;line-height:1.35}
.meanings .first{font-weight:500}
.meanings .rest{color:var(--muted)}
.rrow{display:flex;align-items:baseline;gap:.75rem;flex-wrap:wrap;margin:.4rem 0}
.rlabel{font-size:.95rem;min-width:4.5rem;flex-shrink:0}
.rlist{display:inline-flex;flex-wrap:wrap;gap:.35rem}
.rchip{font-size:.95rem;padding:.2rem .65rem;border:1px solid var(--line);border-radius:4px}
.rchip .oku{color:var(--muted);opacity:.7;margin-left:1px}
.kwords{list-style:none;padding:0;margin:.4rem 0 0;display:grid;
grid-template-columns:repeat(auto-fill,minmax(11rem,1fr));gap:.4rem}
.kword{display:flex;flex-direction:column;text-decoration:none;min-width:0;
padding:.4rem .65rem;border:1px solid var(--line);border-radius:4px}
.kword:hover{border-color:var(--link)}
.kword .kw-head{font-size:1.15rem;font-weight:500;color:var(--fg)}
.kword .kw-gloss{font-size:.8rem;color:var(--muted);white-space:nowrap;overflow:hidden;
text-overflow:ellipsis;margin-top:.1rem}
.kactions{margin:0 0 1.25rem;font-size:.9rem}
@media (max-width:36rem){.kanji-card{flex-direction:column;gap:1.25rem;padding:1.25rem}
.kanji-left{width:11rem;margin:0 auto}}
ul.grid{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:.5rem;margin:.75rem 0}
ul.grid li{border:1px solid var(--line);border-radius:4px;padding:.4rem .55rem;min-width:8rem}
ul.grid .glyph{font-size:1.6rem}
/* About article — the SPA's type scale: mono section labels, muted body text. */
.about h1{font-size:1.6rem}
.about .lede{font-size:1.05rem;line-height:1.7;color:var(--fg)}
.about p,.about li{font-size:.95rem;line-height:1.7;color:var(--muted)}
.about h2{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.75rem;
font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);
margin:2rem 0 .6rem}
.about ul{padding-left:1.25rem;margin:0}
.about li+li{margin-top:.4rem}
footer{margin-top:3rem;border-top:1px solid var(--line);padding-top:1.25rem;
font-size:.8rem;color:var(--muted)}
footer p{margin:.35rem 0}
"""


def _css(theme: str) -> str:
    palette = {"system": _SYS_VARS, "light": _LIGHT_VARS, "dark": _DARK_VARS}.get(theme, _SYS_VARS)
    return f"{palette}{_CSS_MAIN}"

# The footer stays in English even when the rest of the site is Japanese: the
# copyright, licence name and data attributions are legal/credit lines and are
# intentionally not localised. Keep it that way (see the note in
# web/src/lib/components/Footer.svelte).
_FOOTER = """<footer>
<p>Reikun © 2026 Aniket Satbhai ·
<a href="/lite/about">About</a> ·
<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">GitHub</a> ·
<a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE" target="_blank"
rel="noopener noreferrer">Apache-2.0</a></p>
<p>Dictionary data powered by
<a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project" target="_blank"
rel="noopener noreferrer">JMdict</a> and
<a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project" target="_blank"
rel="noopener noreferrer">KANJIDIC2</a> (EDRDG, CC BY-SA 4.0). Sentences from
<a href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus" target="_blank"
rel="noopener noreferrer">Tanaka Corpus</a> (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams from
<a href="https://kanjivg.tagaini.net/" target="_blank" rel="noopener noreferrer">KanjiVG</a>
(Ulrich Apel, CC BY-SA 3.0).</p>
</footer>"""


def _header(hero: bool) -> str:
    if hero:
        return (
            '<header class="hero">'
            f'<p class="hero-tag">{esc(_BRAND_SUBTEXT)}</p>'
            '<h1 class="hero-title"><a class="brand" href="/lite">Reikun <span lang="ja">例訓</span></a>'
            '<span class="tag">lite</span></h1>'
            f'<p class="tagline">{esc(_TAGLINE)}</p>'
            "</header>"
        )
    return (
        '<header><a class="brand" href="/lite">Reikun <span lang="ja">例訓</span></a>'
        '<span class="tag">lite</span></header>'
    )


# Lucide-style inline SVG bodies (24x24, stroke-based) for the top-right
# controls — the same visual language as the SPA's header cluster (which uses
# this icon set). Inline markup needs no JavaScript to render.
_ICON_SUN = (
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/>'
    '<path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/>'
    '<path d="M2 12h2"/><path d="M20 12h2"/>'
    '<path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>'
)
_ICON_MOON = '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'
# square-arrow-out-up-right: the open-the-other-variant glyph
_ICON_FULL = (
    '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
    '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
)


def _icon(body: str) -> str:
    return (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
        ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{body}</svg>"
    )


def _theme_toggle(theme: str, next_url: str) -> str:
    """A single-click theme switch, drawn as icon buttons. With no stored
    choice the OS preference decides the palette, so the toggle pointing the
    opposite way is the only thing a first-time visitor can click — both a sun
    and a moon are rendered and CSS hides the one matching the OS scheme. A
    pinned theme shows just the button back to the other one."""
    if theme == "system":
        href_light = _href("/lite/theme", v="light", next=next_url)
        href_dark = _href("/lite/theme", v="dark", next=next_url)
        sun = f'<a class="icon-link to-light" href="{href_light}" title="Switch to the light theme"'
        moon = f'<a class="icon-link to-dark" href="{href_dark}" title="Switch to the dark theme"'
        return (
            '<span class="theme-toggle">'
            f'{sun} aria-label="Switch to the light theme">{_icon(_ICON_SUN)}</a>'
            f'{moon} aria-label="Switch to the dark theme">{_icon(_ICON_MOON)}</a>'
            "</span>"
        )
    other = "dark" if theme == "light" else "light"
    href = _href("/lite/theme", v=other, next=next_url)
    label = f"Switch to the {other} theme"
    glyph = _ICON_MOON if other == "dark" else _ICON_SUN
    return f'<a class="icon-link" href="{href}" title="{label}" aria-label="{label}">{_icon(glyph)}</a>'


def _controls(request: Request) -> str:
    """Top-right chrome row on every page: the one-click theme switch
    (cookie-based, light/dark with a system default) and the variant switch
    back to the full UI — configured via WEB_BASE_URL because lite and the SPA
    run on separate origins in development. Icon buttons mirror the SPA's
    header cluster; the titles carry the meaning text does not."""
    theme = _read_theme(request)
    next_url = _current_path(request)
    parts = [_theme_toggle(theme, next_url)]
    if WEB_BASE_URL:
        parts.append(
            '<a class="icon-link" href="' + esc(WEB_BASE_URL) + '" rel="noopener"'
            ' title="Switch to the full interface"'
            f' aria-label="Switch to the full interface">{_icon(_ICON_FULL)}</a>'
        )
    return '<div class="controls">' + "".join(parts) + "</div>"


def _page(
    title: str,
    body: str,
    *,
    status_code: int = 200,
    cache: str | None = None,
    hero: bool = False,
    controls: str = "",
    theme: str = "system",
) -> HTMLResponse:
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Reikun Lite</title>
<style>{_css(theme)}</style>
</head>
<body>
{_header(hero)}
{controls}
<main>
{body}
</main>
{_FOOTER}
</body>
</html>"""
    if cache and theme != "system":
        # Cookie-specific CSS: shared/CDN caches could serve one user's theme
        # to another, so keep it to the request when a theme choice exists.
        cache = cache.replace("public,", "private,", 1)
    headers = {"Cache-Control": cache or "no-store", "Vary": "Cookie"}
    return HTMLResponse(document, status_code=status_code, headers=headers)


def _error_page(
    title: str, message: str, status_code: int, theme: str = "system", controls: str = ""
) -> HTMLResponse:
    return _page(
        title,
        f'<h1>{esc(title)}</h1><p>{esc(message)}</p><p><a href="/lite">Back to search</a></p>',
        status_code=status_code,
        theme=theme,
        controls=controls,
    )


def _search_form(q: str = "", *, furi: bool = True, next_url: str = "/lite", autofocus: bool = False) -> str:
    """The search row, mirroring the SPA: input, then three text buttons —
    Search, random kanji (a plain ``formaction`` redirect target, no JS) and
    the furigana toggle (a link that flips the preference cookie, then
    redirects back). Strikethrough marks furigana as off."""
    focus = " autofocus" if autofocus else ""
    toggle_title = (
        "Furigana shown — click to hide readings" if furi else "Furigana hidden — click to show readings"
    )
    toggle = _href("/lite/furigana", next=next_url)
    kana_link = f'<a class="btn furi{" off" if not furi else ""}" href="{toggle}" title="{toggle_title}">Furigana</a>'
    return f"""<form class="search" action="/lite/search" method="get" role="search">
<input type="search" name="q" value="{esc(q)}"
placeholder="Japanese or English word, or a sentence" aria-label="Search"{focus}>
<input type="hidden" name="level" value="N5">
<button type="submit">Search</button>
<button type="submit" formaction="/lite/kanji/random" title="Random N5 kanji">Random kanji</button>
{kana_link}
</form>"""


# ── Search ───────────────────────────────────────────────────────────────────

# Same defaults as the main UI: one query box, the auto pipeline, fixed page size.
_SEARCH_COUNT = 20


@router.get("/lite", response_class=HTMLResponse)
@router.get("/lite/", response_class=HTMLResponse)
def lite_home(request: Request) -> HTMLResponse:
    furi = _read_furi(request)
    recent = _read_recent(request)
    form = _search_form(furi=furi, next_url=_current_path(request), autofocus=True)

    # The SPA shows recent searches when they exist and the example pills
    # otherwise; a cookie makes both possible without JavaScript.
    if recent:
        label = '<p class="pills-label">Recent searches <a href="/lite/recent/clear">Clear</a></p>'
        pills = "".join(
            f'<a class="pill" href="{_href("/lite/search", q=query)}"><span lang="ja">{esc(query)}</span></a>'
            for query in recent
        )
    else:
        label = '<p class="pills-label">Example searches</p>'
        pills = "".join(
            f'<a class="pill" href="{_href("/lite/search", q=entry)}">{esc(entry)}</a>' for entry in _EXAMPLES
        )

    body = f"""{form}
{label}
<div class="pills">{pills}</div>
<p class="reading-note">Tip: paste a Japanese sentence to see its word-by-word breakdown —
each word links to its own entry, with furigana until you hide it above.</p>"""
    return _page("Search", body, hero=True, controls=_controls(request), theme=_read_theme(request))


@router.get("/lite/search", response_class=HTMLResponse, dependencies=[_search_limit])
def lite_search(
    background: BackgroundTasks,
    request: Request,
    q: str = "",
    log: bool = Query(True, include_in_schema=False),
) -> Response:
    query = q.strip()
    if not query:
        return _page(
            "Search",
            _search_form(autofocus=True),
            controls=_controls(request),
            theme=_read_theme(request),
        )
    furi = _read_furi(request)
    theme = _read_theme(request)
    current = _current_path(request)
    recent_value = _recent_cookie_value(request.cookies.get(_RECENT_COOKIE, ""), query)

    def _finish(status: int, body: str, title: str) -> Response:
        page = _page(title, body, status_code=status, theme=theme, controls=_controls(request))
        page.set_cookie(
            _RECENT_COOKIE,
            recent_value,
            max_age=_COOKIE_MAX_AGE,
            samesite="lax",
        )
        return page

    try:
        resp = search(query, _SEARCH_COUNT, "auto")
    except Exception:
        logger.exception("lite search failed")
        return _finish(
            502,
            '<p class="warn">Search is temporarily unavailable. Please try again.</p>'
            '<p><a href="/lite/search">Retry</a> · <a href="/lite">Back to search</a></p>',
            "Search unavailable",
        )

    if log:
        top = resp.results[0] if resp.results else {}
        telemetry().search(
            query,
            rewritten_query=resp.rewrite.query,
            rewrite_method=resp.rewrite.method,
            mode=resp.mode,
            num_results=_SEARCH_COUNT,
            result_count=len(resp.results),
            top_result=top.get("kanji_form") or top.get("reading"),
            latency_ms=resp.latency_ms,
            cached=bool(resp.meta.get("cached")),
            route=cast("str | None", resp.meta.get("route")),
            embed_ms=cast("int | None", resp.meta.get("embed_ms")),
            retrieve_ms=cast("int | None", resp.meta.get("retrieve_ms")),
        )
        if is_kanji(query):
            background.add_task(telemetry().kanji_lookup, query, source="lite")

    body = _search_form(query, furi=furi, next_url=current) + _results_html(request, query, resp)
    return _finish(200, body, f"{query} — results")


@router.get("/lite/furigana")
def lite_furigana(request: Request, next: str = "") -> Response:
    """Flip the furigana preference cookie, then go back where we came from —
    the no-JS furigana toggle behind the Furigana button in the search row."""
    response = RedirectResponse(_safe_next(next), status_code=303, headers={"Cache-Control": "no-store"})
    response.set_cookie(_FURI_COOKIE, "0" if _read_furi(request) else "1", max_age=_COOKIE_MAX_AGE, samesite="lax")
    return response


@router.get("/lite/theme")
def lite_theme(request: Request, v: str = "", next: str = "") -> Response:
    """Set the theme-choice cookie, then redirect back — the no-JS theme picker
    along the top of every lite page. Only light/dark exist; without a cookie
    the page follows the system preference, so unknown values leave it alone."""
    response = RedirectResponse(_safe_next(next), status_code=303, headers={"Cache-Control": "no-store"})
    if v in _THEMES:
        response.set_cookie(_THEME_COOKIE, v, max_age=_COOKIE_MAX_AGE, samesite="lax")
    return response


@router.get("/lite/recent/clear")
def lite_recent_clear(next: str = "") -> Response:
    """Empty the recent-searches cookie — the pills row's Clear link. Writes "
    "[]\" instead of deleting the cookie: the shared list is read by the web UI
    too (web/src/lib/recent.ts keeps its own localStorage fallback for when
    cookies are blocked), and there an absent cookie reads as "no shared state,
    use your local copy" — which would resurrect this history. An explicitly
    empty list clears every reader."""
    response = RedirectResponse(_safe_next(next), status_code=303, headers={"Cache-Control": "no-store"})
    response.set_cookie(_RECENT_COOKIE, "[]", max_age=_COOKIE_MAX_AGE, samesite="lax")
    return response


def _int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _results_html(request: Request, query: str, resp: SearchResponse) -> str:
    """Result list styled like the SPA: caption → Sentence Breakdown chips →
    entry cards. A single-kanji query pins the full kanji card on top, and the
    message texts mirror the SPA's i18n strings."""
    furi = _read_furi(request)
    rewrite = resp.rewrite
    parts: list[str] = []

    if rewrite.changed and rewrite.query and rewrite.query != query:
        parts.append(f'<p class="muted">Searched for <b>{esc(rewrite.query)}</b></p>')

    too_long = resp.meta.get("too_long")
    if too_long:
        shown = query if len(query) <= 24 else f"{query[:24]}…"
        if too_long == MAX_JA_QUERY_CHARS:
            parts.append(
                f'<p class="warn">“{esc(shown)}” is too long — Japanese input is parsed up to '
                f'{esc(too_long)} characters; enter a word or a shorter sentence.</p>'
            )
        else:
            parts.append(
                f'<p class="warn">“{esc(shown)}” is too long for a dictionary lookup — enter a single word or a '
                f'short phrase ({esc(too_long)} characters max).</p>'
            )

    char = query if is_kanji(query) else ""
    if char:
        card = kanji_card(char, strokes=True)
        if card:
            # The pinned card for a single-kanji query: no action row — the
            # search header above already has Search / Random kanji / Furigana.
            parts.append(_kanji_body(request, card))

    raw_segments = dict(resp.meta).pop("segments", None)
    if raw_segments:
        chips = []
        approx = False
        for raw in cast("tuple[dict, ...]", raw_segments):
            chip = segment_chip(raw)
            approx = approx or bool(chip.get("approx"))
            href = _href("/lite/search", q=chip["text"])
            title = f'{chip["gloss"]} ({chip["reading"]})' if chip["gloss"] else chip["reading"]
            chips.append(
                f'<a class="seg{" approx" if chip.get("approx") else ""}" href="{href}" title="{esc(title)}">'
                f'<span class="seg-word" lang="ja">{_ruby(chip["ruby"], furi)}</span>'
                f'<span class="seg-mean">{esc(chip["gloss"])}</span></a>'
            )
        approx_badge = ' <span class="badge">Approximate</span>' if approx else ""
        parts.append(
            '<div class="seg-card"><div class="seg-header">'
            f'<p class="seg-title"><span>Sentence Breakdown</span>{approx_badge}</p>'
            '<span class="stats-meta">Hover for definitions · Click to view entry</span>'
            '</div>'
            f'<div class="seg-row">{"".join(chips)}</div></div>'
        )

    results = resp.results
    if results:
        noun = "1 entry" if len(results) == 1 else f"{len(results)} entries"
        parts.append(f'<p class="muted">{noun} · {esc(resp.latency_ms)} ms</p>')
        parts.extend(_result_card(query, result, furi) for result in results)
    elif not too_long:
        if char:
            parts.append(
                # The curly apostrophe mirrors the SPA's notAWord string (i18n.svelte.ts).
                f'<p class="warn">“{esc(char)}” isn’t a standalone dictionary word — see the common words '  # noqa: RUF001
                f"above for it in use.</p>"
            )
        else:
            parts.append("<p>Nothing found. Try a different English or Japanese word.</p>")

    return "".join(parts)


def _result_card(query: str, result: dict, furi: bool) -> str:
    """One entry card, structured like the web UI's ResultCard: headword,
    meanings line, inflection note, conjugations link, kanji links, related
    words and examples. No collapsed sections — everything visible."""
    head = result.get("kanji_form") or result.get("reading") or result.get("text") or ""
    readings = result.get("readings") or []
    kanji_forms = result.get("kanji_forms") or []
    meanings = result.get("meanings") or []

    common = '<span class="badge">common</span>' if result.get("is_common") else ""
    entry_id = result.get("id")
    anchor = f' id="r{esc(entry_id)}"' if entry_id is not None else ""
    head_html = _ruby(furigana_parts(head, result.get("reading")), furi)

    inflection = result.get("inflection")
    inflection_note = ""
    if inflection:
        inflection_note = (
            f'<p class="reading-note">{esc(query)} — matched the <b>{esc(inflection)}</b> form '
            f'of <span lang="ja">{esc(head)}</span></p>'
        )

    parts = [f'<article class="entry"{anchor}><h2>{head_html} {common}</h2>']
    if meanings:
        parts.append(f'<p class="gloss">{esc("; ".join(meanings[:6]))}</p>')
    parts.append(inflection_note)

    # Conjugations live on their own page, reached by click (like /conjugations in the SPA).
    inflections = result.get("inflected_forms") or []
    if inflections and head:
        conj = _href("/lite/conjugations", word=head, reading=result.get("reading"))
        parts.append(f'<p class="conj-link"><a href="{conj}">Conjugations ({len(inflections)})</a></p>')

    kanji_chars = kanji_in(head)
    if kanji_chars:
        links = " ".join(
            f'<a href="/lite/kanji/{esc(quote(char, safe=""))}">{esc(char)}</a>' for char in kanji_chars
        )
        parts.append(f'<p class="reading-note">Kanji: {links}</p>')

    # Related words sit directly under the headword (no collapse), as in the web UI.
    forms = (head, *kanji_forms, *readings)
    related = related_words(forms, forms) if head else []
    if related:
        chips = " ".join(
            f'<a class="chip" href="{_href("/lite/search", q=word.get("kanji_form") or word.get("reading"))}">'
            f'{_ruby(word.get("ruby") or [], furi)} <span class="muted">{esc(word.get("gloss"))}</span></a>'
            for word in related
        )
        parts.append(f'<div class="related-row" aria-label="Related words">{chips}</div>')

    for example in (result.get("example_sentences") or [])[:3]:
        japanese = example.get("japanese") or ""
        english = example.get("english") or ""
        parts.append(f'<div class="example"><p lang="ja">{esc(japanese)}</p>')
        if english:
            parts.append(f'<p class="muted">{esc(english)}</p>')
        parts.append("</div>")

    parts.append("</article>")
    return "".join(parts)


# ── Conjugations ─────────────────────────────────────────────────────────────

@router.get("/lite/conjugations", response_class=HTMLResponse, dependencies=[_search_limit])
def lite_conjugations(request: Request, word: str = "", reading: str = "") -> Response:
    """Conjugation table for one word — the target of the result card's
    "Conjugations (n)" link, mirroring the SPA's /conjugations page.

    The SPA passes pre-loaded rows through navigation state and falls back to
    a search when it lands there directly (bookmark, shared link). A static
    page has no navigation state, so it always does that second path: search
    the word (n=3, same as the SPA), take the entry whose dictionary form
    matches, and render its rows. `reading` only sharpens the heading."""
    theme = _read_theme(request)
    word = word.strip()
    if not word:
        return _page(
            "Conjugations",
            "<h1>Conjugations</h1>"
            '<p class="muted">No word given — open a search result and click its '
            '"Conjugations" link.</p>'
            '<p><a href="/lite">← Back to search</a></p>',
            controls=_controls(request),
            theme=theme,
        )
    try:
        resp = search(word, 3, "auto", rewrite_mode="off")
    except Exception:
        logger.exception("lite conjugations failed")
        return _error_page(
            "Lookup unavailable", "Search is temporarily unavailable. Please try again.", 502, theme, _controls(request)
        )

    rows = None
    headword = word
    for match in resp.results:
        if (match.get("inflected_forms") or []) and word in (match.get("kanji_form"), match.get("reading")):
            rows, headword = match["inflected_forms"], match.get("kanji_form") or match.get("reading") or word
            break
    if rows is None:  # exact form not first: first entry that ships a table wins
        for match in resp.results:
            if match.get("inflected_forms"):
                rows, headword = match["inflected_forms"], match.get("kanji_form") or match.get("reading") or word
                break
    if not rows:
        return _page(
            "Conjugations",
            f'<h1 lang="ja">{esc(headword)}</h1>'
            f'<p class="muted">No conjugation data for <span lang="ja">{esc(headword)}</span> — '
            f"only verbs and i-adjectives ship a table.</p>"
            f'<p><a href="{_href("/lite/search", q=headword)}">← Back to {esc(headword)}</a></p>',
            controls=_controls(request),
            theme=theme,
        )

    shown_reading = esc(headword) + (f"【{esc(reading)}】" if reading and reading != word else "")
    table_rows = "".join(
        f'<tr><th scope="row">{esc(row.get("form"))}</th>'
        f'<td lang="ja">{esc(row.get("surface"))}</td>'
        f'<td class="muted" lang="ja">{esc(row.get("kana"))}</td></tr>'
        for row in rows
    )
    back = f'<a href="{_href("/lite/search", q=headword)}">← Back to {esc(headword)}</a>'
    body = f"""<nav class="muted">{back}</nav>
<h1 lang="ja">{shown_reading} <span class="tag">Conjugations</span> <span class="badge">{len(rows)}</span></h1>
<p class="muted">How the forms of <span lang="ja">{esc(headword)}</span> are written and read.</p>
<table class="conj">
<thead><tr><th>Form</th><th>Written</th><th>Kana</th></tr></thead>
<tbody>{table_rows}</tbody>
</table>"""
    return _page(f"Conjugations — {headword}", body, controls=_controls(request), theme=theme)


# ── Kanji ────────────────────────────────────────────────────────────────────

@router.get("/lite/kanji/random")
def lite_kanji_random(level: str = "") -> RedirectResponse:
    wanted = level if level in JLPT_LEVELS else None
    pool = jlpt_kanji(wanted) if wanted else None
    try:
        for _ in range(8):
            if is_headword(char := random_kanji(within=pool)):
                break
        else:
            char = random_kanji(within=pool)
    except Exception:
        logger.warning("lite kanji random failed; using unchecked pick", exc_info=True)
        char = random_kanji(within=pool)
    return RedirectResponse(
        f"/lite/kanji/{quote(char, safe='')}", status_code=303, headers={"Cache-Control": "no-store"}
    )


@router.get("/lite/kanji/group", response_class=HTMLResponse)
def lite_kanji_group(request: Request, by: str, value: str = "", n: str = "60", offset: str = "0") -> Response:
    theme = _read_theme(request)
    # A non-integer `value` must reach the HTML error page below (not a bare
    # FastAPI 422 JSON body) — lite pages are always HTML.
    _int_value = _int(value, 0)
    if by not in ("strokes", "grade", "jlpt"):
        return _error_page(
            "Unknown group", "Groups are browsable by strokes, grade or JLPT level.", 404, theme, _controls(request)
        )
    size = min(max(_int(n, 60), 1), 100)
    start = max(_int(offset, 0), 0)
    cards = kanji_group_cards(by, str(_int_value), size, start)
    if cards is None or cards["total"] == 0:
        return _error_page(
            "No kanji in group", f"No kanji found for {by}={value}.", 404, theme, _controls(request)
        )

    items = "".join(
        f'<li><a href="/lite/kanji/{esc(quote(card["literal"], safe=""))}">'
        f'<span class="glyph" lang="ja">{esc(card["literal"])}</span></a><br>'
        f'{esc("; ".join(card.get("meanings") or []))}</li>'
        for card in cards["kanjis"]
    )
    nav = []
    if start > 0:
        previous = _href("/lite/kanji/group", by=by, value=value, n=size, offset=max(start - size, 0))
        nav.append(f'<a href="{previous}">← Previous</a>')
    if start + size < cards["total"]:
        following = _href("/lite/kanji/group", by=by, value=value, n=size, offset=start + size)
        nav.append(f'<a href="{following}">Next →</a>')
    pagination = f'<p class="muted">{" · ".join(nav)}</p>' if nav else ""

    body = f"""<h1>{esc(cards["label"])}</h1>
<p class="muted">{esc(cards["total"])} kanji · showing {start + 1}-{min(start + size, cards["total"])}</p>
<ul class="grid">{items}</ul>
{pagination}
<p><a href="/lite">Back to search</a></p>"""
    return _page(
        cards["label"], body, cache=_CACHE_STATIC, controls=_controls(request), theme=theme
    )


def _kanji_body(request: Request, card: dict, actions: bool = False) -> str:
    """The kanji card used by both /lite/kanji/{char} and the pinned card for a
    single-kanji search — KANJIDIC2 data plus the static KanjiVG SVG. Structured
    like the web UI's KanjiCard: left column with the glyph, stroke diagram and
    badges, right column with meanings, reading chips and a common-words tile
    grid. With ``actions`` the dedicated kanji page gains its Furigana toggle;
    the pinned card inside a search result renders without any action row (the
    search header above it already carries Search/Random kanji/Furigana)."""
    furi = _read_furi(request)
    char = card.get("literal") or ""

    badges = " ".join(_badge(badge) for badge in card.get("meta") or [])

    def _chips(key: str) -> str:
        chips = []
        for chip in (card.get("readings") or {}).get(key) or []:
            okurigana = chip.get("okurigana")
            suffix = f'<span class="oku">{esc(okurigana)}</span>' if okurigana else ""
            chips.append(f'<span class="rchip" lang="ja">{esc(chip.get("stem"))}{suffix}</span>')
        return f'<span class="rlist" lang="ja">{"".join(chips)}</span>' if chips else ""

    # Reading labels carry furigana themselves — honouring the same toggle.
    reading_rows = ""
    for label, label_rt, chips in (("音読み", "おんよみ", _chips("on")), ("訓読み", "くんよみ", _chips("kun"))):
        if not chips:
            continue
        shown = (
            f"<ruby lang=\"ja\">{label}<rt>{label_rt}</rt></ruby>" if furi else f'<span lang="ja">{label}</span>'
        )
        reading_rows += f'<div class="rrow"><span class="rlabel">{shown}</span>{chips}</div>'

    meanings = card.get("meanings") or []
    meaning_line = (
        f'<span class="first">{esc(meanings[0])}</span>'
        + (f'<span class="rest">, {esc(", ".join(meanings[1:]))}</span>' if meanings[1:] else "")
    ) if meanings else "—"

    words = "".join(
        f'<li><a class="kword" href="{_href("/lite/search", q=word.get("kanji_form") or word.get("reading"))}">'
        f'<span class="kw-head" lang="ja">{_ruby(word.get("ruby") or [], furi)}</span>'
        f'<span class="kw-gloss">{esc(word.get("gloss"))}</span></a></li>'
        for word in card.get("common_words") or []
    )
    words_html = (
        f'<div class="ksection"><p class="ksection-title">Common words</p><ul class="kwords">{words}</ul></div>'
        if words else ""
    )

    stroke = card.get("stroke")
    stroke_html = ""
    if stroke:
        paths = "".join(f'<path d="{esc(d)}"/>' for d in stroke.get("strokes") or [])
        numbers = "".join(
            f'<text x="{esc(number.get("x"))}" y="{esc(number.get("y"))}">{esc(number.get("value"))}</text>'
            for number in stroke.get("numbers") or []
        )
        # Boxed like the SPA's stroke-svg, including its dashed practice-sheet
        # quadrant guides (pure CSS, no JS — the SPA's replay button needs one).
        stroke_html = (
            '<div class="stroke-box">'
            f'<svg class="strokes" viewBox="{esc(stroke.get("view_box"))}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Stroke order for {esc(char)}">{paths}{numbers}</svg></div>'
        )

    actions_row = ""
    if actions:
        furi_link = _href("/lite/furigana", next=_current_path(request))
        actions_row = (
            f'<p class="kactions"><a class="furi{" off" if not furi else ""}" href="{furi_link}"'
            ' title="Toggle furigana readings">Furigana</a></p>'
        )
    return f"""<div class="kanji-card">
<div class="kanji-left">
<p class="kanji-glyph" lang="ja">{esc(card.get("literal"))}</p>
{stroke_html}
<p class="kbadges">{badges}</p>
</div>
<div class="kanji-right">
<div class="ksection"><p class="ksection-title">Meanings</p><p class="meanings">{meaning_line}</p></div>
{f'<div class="ksection">{reading_rows}</div>' if reading_rows else ""}
{words_html}
</div>
</div>
{actions_row}"""


@router.get("/lite/kanji/{char}", response_class=HTMLResponse)
def lite_kanji(request: Request, char: str, log: bool = Query(True, include_in_schema=False)) -> Response:
    theme = _read_theme(request)
    if not is_kanji(char):
        return _error_page("Not a kanji", "Provide exactly one kanji character.", 400, theme, _controls(request))
    card = kanji_card(char, strokes=True)
    if not card:
        return _error_page("Kanji not found", f"No KANJIDIC2 entry for {char}.", 404, theme, _controls(request))
    if log:
        telemetry().kanji_lookup(char, source="lite")
    return _page(
        f"Kanji {char}",
        _kanji_body(request, card, actions=True),
        cache=_CACHE_STATIC,
        controls=_controls(request),
        theme=theme,
    )


# ── About ────────────────────────────────────────────────────────────────────
# Sections and copy mirror web/src/routes/about/+page.svelte (which pulls its
# text from i18n.svelte.ts), adapted to what Lite itself does.

@router.get("/lite/about", response_class=HTMLResponse)
def lite_about(request: Request) -> HTMLResponse:
    body = """<article class="about">
<h1>About Reikun</h1>
<p class="lede">Reikun (例訓) is a free, open-source Japanese reading assistant — a semantic
dictionary that works in both English and Japanese. This Lite view is rendered entirely on the
server, so it works without scripts, in text browsers and on slow connections.</p>
<h2>What it does</h2>
<ul>
<li><b>Search</b> — look up words in English or Japanese; natural-language questions
("how do you say X") are rewritten into dictionary terms automatically.</li>
<li><b>Sentence breakdown</b> — paste a Japanese sentence and it is split into word units
with furigana and per-word glosses; each unit links to its own entry.</li>
<li><b>Kanji</b> — readings, meanings, common compounds, JLPT level, and stroke-order
diagrams.</li>
<li><b>Not in Lite</b> — grammar explanations calibrated to a JLPT level are only in the
full interface; Lite keeps every page small and off the LLM path.</li>
</ul>
<h2>How it works</h2>
<p>Search runs hybrid retrieval — dense vector embeddings plus BM25 — fused in Qdrant, with
query routing that picks the right plan for English words, English sentences, and Japanese
input. Sentence parsing uses the Sudachi morphological analyzer; embeddings are quantized
ONNX models running on CPU. Every Lite page is one HTML string — there is no frontend bundle.</p>
<h2>Data and sources</h2>
<p>Dictionary data comes from <a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"
target="_blank" rel="noopener noreferrer">JMdict</a> and
<a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project" target="_blank"
rel="noopener noreferrer">KANJIDIC2</a> (EDRDG, CC BY-SA 4.0). Example sentences are from
<a href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus" target="_blank"
rel="noopener noreferrer">Tanaka Corpus</a> (Tatoeba, CC-BY 2.0 FR). Kanji stroke diagrams from
<a href="https://kanjivg.tagaini.net/" target="_blank" rel="noopener noreferrer">KanjiVG</a>
(Ulrich Apel, CC BY-SA 3.0).</p>
<h2>Privacy</h2>
<p>No cross-site tracking. Search query text is logged to improve embeddings and ranking;
feedback query text is stored only as SHA-256 hashes. Lite keeps three small cookies on this
device only: your recent searches, your furigana preference, and your theme choice. No
analytics, no third-party requests.</p>
<h2>Source</h2>
<p>Reikun is built by Aniket Satbhai. The code is
<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">on GitHub</a>
under the Apache-2.0 license. The full interface lives at
<a href="https://reikun.app" target="_blank" rel="noopener noreferrer">reikun.app</a>; the JSON API
is documented at <a href="/docs">/docs</a>.</p>
</article>"""
    return _page(
        "About", body, cache=_CACHE_STATIC, controls=_controls(request), theme=_read_theme(request)
    )
