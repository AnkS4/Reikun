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
    GET /lite/lang             set the interface language cookie, redirect back
    GET /lite/recent/clear     empty the recent-searches cookie, redirect back
    GET /lite/conjugations     conjugation table for one word
    GET /lite/kanji/{char}     KANJIDIC2 card + static KanjiVG stroke diagram
    GET /lite/kanji/random     redirect to a random kanji card
    GET /lite/kanji/group      browse kanji sharing strokes/grade/JLPT
    GET /lite/about            project + data-licence note
    GET /lite/privacy          privacy policy (English, like the footer)

No templating dependency is used on purpose: pages are plain f-strings with
``html.escape`` on every piece of dynamic text, so the lite layer stays as
small and dependency-free as the promise it makes.
"""

import hashlib
import html
import json
import logging
import threading
import time
from collections.abc import Callable, Coroutine
from typing import Any, cast
from urllib.parse import quote, unquote, urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.routing import APIRoute
from starlette.background import BackgroundTask

from app.config import (
    APP_VERSION,
    COLLECTION,
    RATE_LIMIT_SEARCH,
    TRUSTED_PROXY_HOPS,
    WEB_BASE_URL,
    qdrant_client,
)
from app.kanji_lookup import is_kanji, kanji_in, random_kanji
from app.ratelimit import rate_limited
from app.render import furigana_parts, kanji_card, kanji_group_cards, related_words, segment_chip
from app.retrieval import MAX_JA_QUERY_CHARS, SearchResponse, is_headword, search
from app.telemetry import telemetry

from .assets import _EMBLEM_HASH, _EMBLEM_SVG, _EMBLEM_URL, _LITE_CSS_HASH, _LITE_CSS_TEXT, _LITE_CSS_URL
from .i18n import _t

logger = logging.getLogger("reikun.lite")

_NO_STORE_HOME = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    # Legacy no-cache directives for older browsers/proxies.
    "Pragma": "no-cache",
    "Expires": "0",
}


def _with_etag(request: Request, response: Response) -> Response:
    """ETag + 304 for lite HTML. Lite pages are built as one string, so the
    hash is taken from the finished body — no re-buffering of a stream, and
    only lite routes pay for it (the JSON API never runs this)."""
    body = getattr(response, "body", None)
    if response.status_code != 200 or not isinstance(body, bytes):
        return response
    if not response.headers.get("content-type", "").startswith("text/html"):
        return response
    etag = '"' + hashlib.sha256(body).hexdigest()[:16] + '"'
    if request.url.path in ("/lite", "/lite/"):
        # The home page depends on the recent-searches cookie, so a 304 could
        # serve a stale "Example searches" copy to someone who has searched
        # since (some browsers/proxies mishandle Vary: Cookie). Always fresh.
        response.headers.update({**_NO_STORE_HOME, "ETag": etag})
        return response
    if request.headers.get("if-none-match") == etag:
        headers = {"ETag": etag, "Vary": response.headers.get("vary", "Cookie")}
        if "cache-control" in response.headers:
            headers["Cache-Control"] = response.headers["cache-control"]
        # Keep the status-probe task: a 304 still counts as a page view.
        return Response(status_code=304, headers=headers, background=response.background)
    response.headers["ETag"] = etag
    return response


class _LiteRoute(APIRoute):
    """Route class for the lite router: adds the ETag/304 step to its HTML."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            return _with_etag(request, await handler(request))

        return route


# HTML pages, not JSON API surface — keep them out of /docs and the generated
# frontend types.
router = APIRouter(tags=["lite"], include_in_schema=False, route_class=_LiteRoute)

_search_limit = Depends(rate_limited(RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS))

_CACHE_STATIC = "public, max-age=86400, stale-while-revalidate=604800"

_BRAND_SUBTEXT = "Semantic Japanese Dictionary & Reading Assistant"
_EXAMPLES = [
    "光", "courage", "咲く", "to walk", "大君",
    "How do you say rain in Japanese",
    "あの山の頂上は雪で覆われています。",
]
_THEMES = ("light", "dark")

_FURI_COOKIE = "lite_furi"
_THEME_COOKIE = "lite_theme"
_RECENT_COOKIE = "lite_recent"
_LANG_COOKIE = "lite_lang"
_LANGS = ("en", "ja")
_COOKIE_MAX_AGE = 2_592_000
MAX_RECENT = 8
_RECENT_MAX_CHARS = 150
_RECENT_COOKIE_BUDGET = 2400



@router.get("/lite/static/lite.css", include_in_schema=False)
def lite_static_css() -> Response:
    return Response(
        content=_LITE_CSS_TEXT,
        media_type="text/css",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'\"{_LITE_CSS_HASH}\"',
        },
    )


@router.get("/lite/static/emblem.svg", include_in_schema=False)
def lite_static_emblem() -> Response:
    return Response(
        content=_EMBLEM_SVG,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{_EMBLEM_HASH}"',
        },
    )

# The footer stays in English even when the rest of the site is Japanese: the
# copyright, licence name and data attributions are legal/credit lines and are
# intentionally not localised. Keep it that way (see the note in
# web/src/lib/components/Footer.svelte).
_FOOTER = """<footer>
<p>Reikun © 2026 Aniket Satbhai ·
<a href="/lite/about">About</a> ·
<a href="/lite/privacy">Privacy</a> ·
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


def _badge(badge: dict, from_word: str = "") -> str:
    label = esc(badge.get("label"))
    tip = esc(badge.get("tip"))
    group = badge.get("group")
    if group:
        params = {"by": group.get("by"), "value": group.get("value")}
        if from_word:
            params["from"] = from_word
        href = _href("/lite/kanji/group", **params)
        return f'<a class="badge" href="{href}" title="{tip}">{label}</a>'
    return f'<span class="badge" title="{tip}">{label}</span>'


def _header(hero: bool, lang: str = "en") -> str:
    if hero:
        return (
            '<header class="hero">'
            f'<p class="hero-tag">{esc(_BRAND_SUBTEXT)}</p>'
            '<h1 class="hero-title"><a class="brand" href="/lite">Reikun <span lang="ja">(例訓)</span></a>'
            '<span class="tag">lite</span></h1>'
            f'<p class="tagline">{esc(_t(lang, "lite_tagline"))}</p>'
            f'<p class="lite-note">{esc(_t(lang, "lite_note"))} '
            f'<a href="/lite/about#lite">{esc(_t(lang, "lite_noteLink"))}</a></p>'
            "</header>"
        )
    return (
        '<header><a class="brand" href="/lite">Reikun <span lang="ja">(例訓)</span></a>'
        '<span class="tag">lite</span></header>'
    )


# ── Dictionary status ───────────────────────────────────────────────────────
# A minimal indicator, not the SPA's hover popup: the page renders from the
# last known snapshot (so a page view never waits on Qdrant) and a background
# task refreshes the snapshot after the response is sent. The chip itself is a
# small pill in the top-right cluster — a dot plus a short word, with the
# detail in a native title tooltip.
_status_lock = threading.Lock()
_status_snapshot: dict[str, object] = {"ok": None, "count": None, "at": 0.0}
_STATUS_TTL = 60.0  # seconds between probes


def _status_state() -> tuple[bool | None, int | None, bool]:
    """(ok, entry count, stale?) from the last probe — no network call."""
    with _status_lock:
        ok = cast("bool | None", _status_snapshot["ok"])
        count = cast("int | None", _status_snapshot["count"])
        at = cast("float", _status_snapshot["at"])
    return ok, count, (time.monotonic() - at) > _STATUS_TTL


def _refresh_status() -> None:
    """Probe the dictionary catalogue. Runs after the response is sent, so a
    slow or sleeping Qdrant never delays a page."""
    count: int | None = None
    ok = False
    try:
        result = qdrant_client().count(COLLECTION, timeout=2)
        count = result.count
        # Same readiness rule as /ready: an empty collection is not a working
        # dictionary, however reachable the server is.
        ok = bool(count)
    except Exception as exc:  # unreachable, missing collection, timeout, …
        logger.debug("lite status: dictionary unreachable (%s)", type(exc).__name__)
    with _status_lock:
        _status_snapshot.update(ok=ok, count=count, at=time.monotonic())


def _status_chip(lang: str) -> str:
    """The dictionary status, rendered server-side as the same text pill the
    other controls use: the state word plus a native title tooltip carrying
    the detail. The page was rendered by the process that owns the Qdrant
    client, so unlike the SPA there is no "connecting" phase -- it is either
    connected or not. The state comes from the last cached snapshot (refreshed
    in the background), so a page view never waits on Qdrant. The word is
    plain text (no SVG), so it survives hardened browsers with svg.disabled
    (Tor/LibreWolf Safest)."""
    ok, count, _ = _status_state()
    if ok is None:
        state = "checking"
        label = _t(lang, "lite_statusChecking")
        aria = _t(lang, "statusTitle")
    elif ok:
        state = "ok"
        label = _t(lang, "statusConnected")
        aria = _t(lang, "statusAriaReady", count=f"{count or 0:,}")
    else:
        state = "err"
        label = _t(lang, "statusOffline")
        aria = _t(lang, "statusAriaOffline", msg=_t(lang, "lite_statusUnavailable"))
    title = label
    return (
        f'<span class="control status {state}" role="status" tabindex="0" '
        f'aria-label="{esc(aria)}" title="{esc(title)}">{esc(label)}</span>'
    )


# Top-right controls are deliberately NOT SVG. Hardened browsers (Tor
# Browser / LibreWolf "Safest") set svg.disabled=true, which blanks inline
# SVG too — the controls would vanish exactly for the no-JS visitors lite
# serves. Controls are therefore plain text: every chrome control is the same
# small labelled pill (.control), so the cluster reads uniformly without
# JavaScript, SVG, emoji or a symbol-font gamble (☀ can hit the color-emoji
# font and ignore the muted/hover colors).
#
# This is lite's whole icon language, kept uniform on purpose:
#   - controls: text labels in .control pills (see _controls);
#   - wayfinding: typographic arrows in link text (←, →, from lite/i18n.py);
#   - badges/pills/buttons: words, never glyphs.
# Lite has fewer chrome icons than the SPA by design — no AI explanations,
# no thumbs feedback, no hover tips — so the cluster mirrors the SPA's
# ORDER, not its SVG set. The one remaining SVG on any lite page is the
# kanji stroke diagram (KanjiVG stroke data — content shared with the SPA,
# not an icon); in svg-disabled browsers that box is blank while the card
# still shows glyph, readings, meanings and badges.


def _theme_toggle(theme: str, next_url: str, lang: str) -> str:
    """A single-click theme switch rendered as the same text pills as the
    other controls. With no stored choice the OS preference decides the
    palette, so the toggle pointing the opposite way is the only thing a
    first-time visitor can click — both directions are rendered and CSS hides
    the one matching the OS scheme. A pinned theme shows just the pill back to
    the other one."""
    light_label = _t(lang, "lite_themeToLight")
    dark_label = _t(lang, "lite_themeToDark")
    light_word = _t(lang, "themeLight")
    dark_word = _t(lang, "themeDark")
    if theme == "system":
        href_light = f"/lite/theme?v=light&next={quote(next_url, safe='')}"
        href_dark = f"/lite/theme?v=dark&next={quote(next_url, safe='')}"
        return (
            '<span class="theme-toggle">'
            f'<a class="control to-light" href="{href_light}" title="{esc(light_label)}"'
            f' aria-label="{esc(light_label)}">{esc(light_word)}</a>'
            f'<a class="control to-dark" href="{href_dark}" title="{esc(dark_label)}"'
            f' aria-label="{esc(dark_label)}">{esc(dark_word)}</a>'
            "</span>"
        )
    other = "dark" if theme == "light" else "light"
    href = f"/lite/theme?v={other}&next={quote(next_url, safe='')}"
    label = dark_label if other == "dark" else light_label
    word = dark_word if other == "dark" else light_word
    return (
        f'<a class="control" href="{href}" title="{esc(label)}" aria-label="{esc(label)}">'
        f"{esc(word)}</a>"
    )


def _lang_toggle(lang: str, next_url: str) -> str:
    """No-JS language switch: a text pill (the same .control as the rest of
    the cluster) showing the target language's code, that flips the shared
    lite_lang cookie via a redirect. The target language's own name lives in
    the title/aria-label."""
    other = "ja" if lang == "en" else "en"
    name = "日本語" if other == "ja" else "English"
    code = "JA" if other == "ja" else "EN"
    href = f"/lite/lang?v={other}&next={quote(next_url, safe='')}"
    label = _t(lang, "lite_langSwitch", name=name)
    return (
        f'<a class="control" href="{href}" title="{esc(label)}" aria-label="{esc(label)}" lang="{other}">'
        f"{code}</a>"
    )


def _full_switch_url(request: Request) -> str:
    """Map the current Lite page to its full-UI equivalent so the variant
    switch lands on the same content instead of always the home page."""
    if not WEB_BASE_URL:
        return ""
    base = WEB_BASE_URL.rstrip("/")
    path = request.url.path
    query = request.url.query
    if path == "/lite":
        return base
    if path == "/lite/search":
        q = request.query_params.get("q", "")
        if q:
            return f"{base}/?q={quote(q, safe='')}"
        return base
    if path == "/lite/kanji/group":
        url = f"{base}/kanji-group"
        if query:
            url += f"?{query}"
        return url
    if path == "/lite/kanji/random":
        return base
    if path.startswith("/lite/kanji/"):
        char = path[len("/lite/kanji/"):]
        url = f"{base}/kanji/{char}"
        if query:
            url += f"?{query}"
        return url
    if path == "/lite/conjugations":
        url = f"{base}/conjugations"
        if query:
            url += f"?{query}"
        return url
    if path == "/lite/about":
        return f"{base}/about"
    if path == "/lite/privacy":
        return f"{base}/privacy"
    return base


def _controls(request: Request) -> str:
    """Top-right chrome row on every page — mirrors the SPA's header-cluster
    order: full-version switch, dictionary status, theme switch, language
    switch. Every control is the same .control text pill; the titles and
    aria-labels carry the full meaning the short labels abbreviate."""
    lang = _read_lang(request)
    theme = _read_theme(request)
    next_url = _current_path(request)
    parts = []
    full_url = _full_switch_url(request)
    if full_url:
        label = _t(lang, "lite_fullSwitch")
        parts.append(
            '<a class="control" href="' + esc(full_url) + '" rel="noopener"'
            f' title="{esc(label)}" aria-label="{esc(label)}">{esc(_t(lang, "lite_fullShort"))}</a>'
        )
    parts.append(_status_chip(lang))
    parts.append(_theme_toggle(theme, next_url, lang))
    parts.append(_lang_toggle(lang, next_url))
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
    lang: str = "en",
    furi: bool = True,
) -> HTMLResponse:
    document = f"""<!doctype html>
<html lang="{esc(lang)}" data-theme="{esc(theme)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc(title)} · Reikun Lite</title>
<link rel="stylesheet" href="{_LITE_CSS_URL}">
</head>
<body>
{_header(hero, lang)}
{controls}
<a class="skip-link" href="#main">Skip to content</a>
<main id="main">
{body}
</main>
{_FOOTER}
</body>
</html>"""
    if cache and (theme != "system" or lang != "en" or not furi):
        # Cookie-specific markup (theme, language, hidden readings): shared
        # caches may ignore Vary: Cookie (Cloudflare does) and serve one
        # visitor's copy to another, so keep it to the browser.
        cache = cache.replace("public,", "private,", 1)
    ok, _, stale = _status_state()
    if cache and ok is not True:
        # The status chip is baked into the page: only share a copy that says
        # "Ready", never one that says "Offline" (or has not probed yet).
        cache = None
    headers = {"Cache-Control": cache or "no-store", "Vary": "Cookie"}
    response = HTMLResponse(document, status_code=status_code, headers=headers)
    if stale:
        # Probe the dictionary after the response is sent: the page never waits
        # on Qdrant, and the next view shows a fresh chip.
        response.background = BackgroundTask(_refresh_status)
    return response


def _error_page(
    title: str,
    message: str,
    status_code: int,
    theme: str = "system",
    controls: str = "",
    lang: str = "en",
) -> HTMLResponse:
    return _page(
        title,
        f'<h1>{esc(title)}</h1><p>{esc(message)}</p>'
        f'<p><a href="/lite">{esc(_t(lang, "backToSearch"))}</a></p>',
        status_code=status_code,
        theme=theme,
        controls=controls,
        lang=lang,
    )


def _search_form(
    q: str = "",
    *,
    lang: str = "en",
    furi: bool = True,
    next_url: str = "/lite",
    from_word: str = "",
    frm: str = "",
    chain: str = "",
    autofocus: bool = False,
) -> str:
    """The search row, mirroring the SPA: input, then three text buttons —
    Search, random kanji (a plain ``formaction`` redirect target, no JS) and
    the furigana toggle (a link that flips the preference cookie, then
    redirects back). Strikethrough marks furigana as off."""
    focus = " autofocus" if autofocus else ""
    toggle_title = _t(lang, "furiganaShown" if furi else "furiganaHidden")
    toggle = f"/lite/furigana?next={quote(next_url, safe='')}"
    kana_link = (
        f'<a class="btn furi{" off" if not furi else ""}" href="{toggle}"'
        f' title="{esc(toggle_title)}">{esc(_t(lang, "lite_furiganaLabel"))}</a>'
    )
    search_btn = esc(_t(lang, "search"))
    random_title = esc(_t(lang, "lite_randomKanjiLabel"))
    random_label = esc(_t(lang, "lite_randomKanjiLabel"))
    from_input = f'<input type="hidden" name="from" value="{esc(from_word)}">' if from_word else ""
    chain_val = (frm + ("|" + chain if chain else "")) if frm else chain
    chain_input = f'<input type="hidden" name="chain" value="{esc(chain_val)}">' if chain_val else ""
    return f"""<form class="search" action="/lite/search" method="get" role="search">
<input type="search" name="q" value="{esc(q)}"
placeholder="{esc(_t(lang, "searchPlaceholder"))}" aria-label="{search_btn}"{focus}>
{from_input}
{chain_input}
<button type="submit">{search_btn}</button>
<button type="submit" formaction="/lite/kanji/random" title="{random_title}">{random_label}</button>
{kana_link}
</form>"""


# ── Search ───────────────────────────────────────────────────────────────────

# Same defaults as the main UI: one query box, the auto pipeline, fixed page size.
_SEARCH_COUNT = 10


@router.get("/lite", response_class=HTMLResponse)
@router.get("/lite/", response_class=HTMLResponse)
def lite_home(request: Request) -> HTMLResponse:
    lang = _read_lang(request)
    furi = _read_furi(request)
    recent = _read_recent(request)
    form = _search_form(furi=furi, lang=lang, next_url=_current_path(request), autofocus=True)

    # The SPA shows recent searches when they exist and the example pills
    # otherwise; a cookie makes both possible without JavaScript.
    if recent:
        label = (
            f'<p class="pills-label">{esc(_t(lang, "recentSearches"))} '
            f'<a href="/lite/recent/clear">{esc(_t(lang, "clear"))}</a></p>'
        )
        pills = "".join(
            f'<a class="pill" href="{_href("/lite/search", q=query)}"><span lang="ja">{esc(query)}</span></a>'
            for query in recent
        )
    else:
        label = f'<p class="pills-label">{esc(_t(lang, "exampleSearches"))}</p>'
        pills = "".join(
            f'<a class="pill" href="{_href("/lite/search", q=entry)}">{esc(entry)}</a>' for entry in _EXAMPLES
        )

    body = f"""{form}
{label}
<div class="pills">{pills}</div>"""
    return _page(
        _t(lang, "search"),
        body,
        hero=True,
        controls=_controls(request),
        theme=_read_theme(request),
        lang=lang,
    )


@router.get("/lite/search", response_class=HTMLResponse, dependencies=[_search_limit])
def lite_search(
    background: BackgroundTasks,
    request: Request,
    q: str = "",
    log: bool = Query(True, include_in_schema=False),
) -> Response:
    lang = _read_lang(request)
    query = q.strip()
    if not query:
        return _page(
            _t(lang, "search"),
            _search_form(lang=lang, autofocus=True),
            controls=_controls(request),
            theme=_read_theme(request),
            lang=lang,
        )
    furi = _read_furi(request)
    theme = _read_theme(request)
    current = _current_path(request)
    recent_value = _recent_cookie_value(request.cookies.get(_RECENT_COOKIE, ""), query)

    def _finish(status: int, body: str, title: str) -> Response:
        page = _page(title, body, status_code=status, theme=theme, controls=_controls(request), lang=lang)
        page.set_cookie(
            _RECENT_COOKIE,
            recent_value,
            max_age=_COOKIE_MAX_AGE,
            samesite="lax",
        )
        return page

    try:
        # Heuristic rewrite only: a Lite session is AI-free by construction,
        # whatever QUERY_REWRITE the deployment configured for the SPA.
        resp = search(query, _SEARCH_COUNT, "auto", rewrite_mode="heuristic")
    except Exception:
        logger.exception("lite search failed")
        return _finish(
            502,
            f'<p class="warn">{esc(_t(lang, "lite_searchUnavailable"))}</p>'
            f'<p><a href="/lite/search">{esc(_t(lang, "retry"))}</a> · '
            f'<a href="/lite">{esc(_t(lang, "backToSearch"))}</a></p>',
            _t(lang, "lite_searchUnavailable"),
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

    body = (
        _search_form(query, lang=lang, furi=furi, next_url=current, from_word=query)
        + _results_html(request, query, resp, lang)
    )
    return _finish(200, body, _t(lang, "lite_resultsTitle", query=query))


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


@router.get("/lite/lang")
def lite_lang(request: Request, v: str = "", next: str = "") -> Response:
    """Set the interface-language cookie, then redirect back — the no-JS
    language toggle in the controls row. The SPA mirrors this same cookie
    (web/src/lib/i18n.svelte.ts), so one choice follows you across variants."""
    response = RedirectResponse(_safe_next(next), status_code=303, headers={"Cache-Control": "no-store"})
    if v in _LANGS:
        response.set_cookie(_LANG_COOKIE, v, max_age=_COOKIE_MAX_AGE, samesite="lax")
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


def _read_lang(request: Request) -> str:
    """Interface language — English unless the shared cookie says Japanese."""
    value = request.cookies.get(_LANG_COOKIE, "")
    return value if value in _LANGS else "en"


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
    # Keep the original (already percent-encoded) form of the URL so it can be
    # round-tripped through the `next` query parameter without being
    # double-encoded (urlencode turns a literal '+' into '%2B').
    if request.url.query:
        return f"{request.url.path}?{request.url.query}"
    return request.url.path


def _safe_next(next_url: str | None) -> str:
    # Sites-only redirect: a /lite… path may carry a query, but never a domain.
    if next_url and next_url.startswith("/lite") and not next_url.startswith("//"):
        return next_url
    return "/lite"


def _results_html(request: Request, query: str, resp: SearchResponse, lang: str) -> str:
    """Result list styled like the SPA: caption → Sentence Breakdown chips →
    entry cards. A single-kanji query pins the full kanji card on top, and the
    message texts mirror the SPA's i18n strings."""
    furi = _read_furi(request)
    rewrite = resp.rewrite
    parts: list[str] = []

    if rewrite.changed and rewrite.query and rewrite.query != query:
        parts.append(
            f'<p class="muted">{esc(_t(lang, "searchedForBefore"))}<b>{esc(rewrite.query)}</b>'
            f'{esc(_t(lang, "searchedForAfter"))}</p>'
        )

    too_long = resp.meta.get("too_long")
    if too_long:
        shown = query if len(query) <= 24 else f"{query[:24]}…"
        key = "tooLongJa" if too_long == MAX_JA_QUERY_CHARS else "tooLong"
        parts.append(f'<p class="warn">{esc(_t(lang, key, shown=shown, max=too_long))}</p>')

    char = query if is_kanji(query) else ""
    if char:
        card = kanji_card(char, strokes=True)
        if card:
            # The pinned card for a single-kanji query: no action row — the
            # search header above already has Search / Random kanji / Furigana.
            # Badges thread the kanji itself so the group page they open
            # links back here.
            parts.append(_kanji_body(request, card, from_word=query))

    raw_segments = cast("tuple[dict, ...] | None", dict(resp.meta).pop("segments", None))
    if raw_segments and len(raw_segments) > 1:
        chips = []
        approx = False
        for raw in raw_segments:
            chip = segment_chip(raw)
            approx = approx or bool(chip.get("approx"))
            href = _href("/lite/search", q=chip["text"])
            title = f'{chip["gloss"]} ({chip["reading"]})' if chip["gloss"] else chip["reading"]
            chips.append(
                f'<a class="seg{" approx" if chip.get("approx") else ""}" href="{href}" title="{esc(title)}">'
                f'<span class="seg-word" lang="ja">{_ruby(chip["ruby"], furi)}</span>'
                f'<span class="seg-mean">{esc(chip["gloss"])}</span></a>'
            )
        approx_badge = f' <span class="badge">{esc(_t(lang, "approximate"))}</span>' if approx else ""
        parts.append(
            '<div class="seg-card"><div class="seg-header">'
            f'<p class="seg-title"><span>{esc(_t(lang, "breakdown"))}</span>{approx_badge}</p>'
            f'<span class="stats-meta">{esc(_t(lang, "breakdownHint"))}</span>'
            '</div>'
            f'<div class="seg-row">{"".join(chips)}</div></div>'
        )

    results = resp.results
    if results:
        noun = _t(lang, "entryOne") if len(results) == 1 else _t(lang, "entryMany", count=len(results))
        parts.append(
            f'<p class="stats-line"><span class="stats-count">{esc(noun)}</span>'
            f'<span class="stats-meta">{esc(resp.latency_ms)} ms</span></p>'
        )
        parts.extend(_result_card(query, result, furi, lang) for result in results)
    elif not too_long:
        if char:
            parts.append(f'<p class="warn">{esc(_t(lang, "lite_notAWord", char=char))}</p>')
        else:
            parts.append(f'<p>{esc(_t(lang, "nothingFound"))}</p>')

    return "".join(parts)


def _result_card(query: str, result: dict, furi: bool, lang: str) -> str:
    """One entry card, structured like the web UI's ResultCard: headword,
    meanings line, inflection note, conjugations link, kanji links, related
    words and examples. No collapsed sections — everything visible."""
    head = result.get("kanji_form") or result.get("reading") or result.get("text") or ""
    readings = result.get("readings") or []
    kanji_forms = result.get("kanji_forms") or []
    meanings = result.get("meanings") or []

    common = f'<span class="badge">{esc(_t(lang, "common"))}</span>' if result.get("is_common") else ""
    entry_id = result.get("id")
    anchor = f' id="r{esc(entry_id)}"' if entry_id is not None else ""
    head_html = _ruby(furigana_parts(head, result.get("reading")), furi)

    inflection = result.get("inflection")
    inflection_note = ""
    if inflection:
        inflection_note = (
            f'<p class="inflection-bar">'
            f'{_t(lang, "lite_inflectionNote", query=esc(query), form=esc(inflection), head=esc(head))}</p>'
        )

    parts = [f'<article class="entry"{anchor}><h2>{head_html} {common}</h2>']
    if meanings:
        parts.append(f'<p class="gloss">{esc("; ".join(meanings[:6]))}</p>')
    parts.append(inflection_note)

    # Conjugations live on their own page, reached by click (like /conjugations in the SPA).
    inflections = result.get("inflected_forms") or []
    if inflections and head:
        conj = _href("/lite/conjugations", word=head, reading=result.get("reading"))
        parts.append(
            f'<p class="conj-link"><a href="{conj}">{esc(_t(lang, "lite_conjLink", count=len(inflections)))}</a></p>'
        )

    kanji_chars = kanji_in(head)
    if kanji_chars:
        links = " ".join(
            f'<a class="kanji-link" href="{_href("/lite/kanji/" + quote(char, safe=""), **{"from": query})}">'
            f"{esc(char)}</a>"
            for char in kanji_chars
        )
        parts.append(f'<p class="reading-note">{esc(_t(lang, "lite_kanjiLabel"))}: {links}</p>')

    # Related words sit directly under the headword (no collapse), as in the web UI.
    forms = (head, *kanji_forms, *readings)
    related = related_words(forms, forms) if head else []
    if related:
        chips = " ".join(
            f'<a class="chip" href="{_href("/lite/search", q=word.get("kanji_form") or word.get("reading"))}">'
            f'{_ruby(word.get("ruby") or [], furi)} <span class="muted">{esc(word.get("gloss"))}</span></a>'
            for word in related
        )
        parts.append(
            f'<div class="related-row" aria-label="{esc(_t(lang, "relatedWords"))}">{chips}</div>'
        )

    examples = []
    for example in (result.get("example_sentences") or [])[:3]:
        japanese = example.get("japanese") or ""
        english = example.get("english") or ""
        examples.append(f'<div class="example"><p lang="ja">{esc(japanese)}</p>')
        if english:
            examples.append(f'<p class="muted">{esc(english)}</p>')
        examples.append("</div>")
    if examples:
        parts.append(f'<div class="example-section">{"".join(examples)}</div>')

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
    lang = _read_lang(request)
    word = word.strip()
    if not word:
        return _page(
            _t(lang, "conjugations"),
            f'<div class="conj-page"><h1>{esc(_t(lang, "conjugations"))}</h1>'
            f'<p class="muted">{esc(_t(lang, "lite_conjNoWord"))}</p>'
            f'<p><a class="btn" href="/lite">← {esc(_t(lang, "backToSearch"))}</a></p></div>',
            controls=_controls(request),
            theme=theme,
            lang=lang,
        )
    try:
        resp = search(word, 3, "auto", rewrite_mode="off")
    except Exception:
        logger.exception("lite conjugations failed")
        return _error_page(
            _t(lang, "lite_lookupUnavailable"),
            _t(lang, "lite_searchUnavailable"),
            502,
            theme,
            _controls(request),
            lang,
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
            _t(lang, "conjugations"),
            f'<div class="conj-page"><h1 lang="ja">{esc(headword)}</h1>'
            f'<p class="conj-sub">{_t(lang, "lite_noConjData", word=esc(headword))}</p>'
            f'<p><a class="btn" href="{_href("/lite/search", q=headword)}">← '
            f'{esc(_t(lang, "backTo", word=headword))}</a></p></div>',
            controls=_controls(request),
            theme=theme,
            lang=lang,
        )

    shown_reading = esc(headword) + (
        f'<span class="conj-reading">【{esc(reading)}】</span>' if reading and reading != word else ""
    )
    table_rows = "".join(
        f'<tr><th scope="row">{esc(row.get("form"))}</th>'
        f'<td lang="ja">{esc(row.get("surface"))}</td>'
        f'<td class="muted" lang="ja">{esc(row.get("kana") or "—")}</td></tr>'
        for row in rows
    )
    back = (
        f'<a class="btn" href="{_href("/lite/search", q=headword)}">'
        f'← {esc(_t(lang, "backTo", word=headword))}</a>'
    )
    table_head = (
        f'<thead><tr><th>{esc(_t(lang, "form"))}</th><th>{esc(_t(lang, "written"))}</th>'
        f'<th>{esc(_t(lang, "kana"))}</th></tr></thead>'
    )
    body = f"""<div class="conj-page"><nav class="conj-nav">{back}</nav>
<h1 lang="ja" class="conj-title">{shown_reading}
<span class="conj-label">{esc(_t(lang, "conjugations"))}</span>
<span class="kgroup-total">{len(rows)}</span></h1>
<p class="conj-sub">{_t(lang, "lite_conjSub", word=f'<span lang="ja">{esc(headword)}</span>')}</p>
<table class="conj">
{table_head}
<tbody>{table_rows}</tbody>
</table>
<div class="conj-page-back">{back}</div></div>"""
    return _page(
        _t(lang, "conjPageTitle", word=headword), body, controls=_controls(request), theme=theme, lang=lang
    )


# ── Kanji ────────────────────────────────────────────────────────────────────

@router.get("/lite/kanji/random")
def lite_kanji_random(
    request: Request,
    frm: str = Query("", alias="from"),
    chn: str = Query("", alias="chain"),
) -> RedirectResponse:
    """Redirect to a random kanji card. Lite has no JLPT-level picker, so the
    pool is the whole kanji table. ``frm`` (the page the click came from) and
    ``chn`` (its predecessor chain) are threaded so "← Back" walks the full
    chain of visited kanjis instead of skipping to the search page."""
    try:
        for _ in range(8):
            if is_headword(char := random_kanji()):
                break
        else:
            char = random_kanji()
    except Exception:
        logger.warning("lite kanji random failed; using unchecked pick", exc_info=True)
        char = random_kanji()
    # New page's chain = the current page's predecessor list (chn), NOT
    # including the current char — that becomes the new page's `from`.
    new_chain = chn
    target = f"/lite/kanji/{quote(char, safe='')}"
    params = [f"from={quote(frm, safe='')}"] if frm else []
    if new_chain:
        params.append(f"chain={quote(new_chain, safe='')}")
    if params:
        target += "?" + "&".join(params)
    response = RedirectResponse(target, status_code=303, headers={"Cache-Control": "no-store"})
    # A random pick is a lookup too — record it in the shared recent-searches
    # cookie so the homepage pills (and the SPA, which reads the same cookie)
    # show it, matching the full version's pushRecent on shuffle.
    response.set_cookie(
        _RECENT_COOKIE,
        _recent_cookie_value(request.cookies.get(_RECENT_COOKIE, ""), char),
        max_age=_COOKIE_MAX_AGE,
        samesite="lax",
    )
    return response


def _kg_meta(card: dict, lang: str) -> str:
    parts = []
    sc = card.get("stroke_count")
    if sc:
        parts.append(_t(lang, "strokesCount", n=sc))
    jlpt = card.get("jlpt_level")
    if jlpt:
        parts.append({4: "N5", 3: "N4", 2: "N2-N3", 1: "N1"}.get(jlpt, f"N{jlpt}"))
    freq = card.get("freq")
    if freq:
        parts.append(_t(lang, "freq", n=freq))
    return " · ".join(parts)


@router.get("/lite/kanji/group", response_class=HTMLResponse)
def lite_kanji_group(request: Request, by: str, value: str = "", n: str = "60", offset: str = "0",
                     frm: str = Query("", alias="from")) -> Response:
    theme = _read_theme(request)
    lang = _read_lang(request)
    # A non-integer `value` must reach the HTML error page below (not a bare
    # FastAPI 422 JSON body) — lite pages are always HTML.
    _int_value = _int(value, 0)
    if by not in ("strokes", "grade", "jlpt"):
        return _error_page(
            _t(lang, "lite_unknownGroup"),
            _t(lang, "lite_unknownGroupMsg"),
            404,
            theme,
            _controls(request),
            lang,
        )
    size = min(max(_int(n, 60), 1), 100)
    start = max(_int(offset, 0), 0)
    cards = kanji_group_cards(by, str(_int_value), size, start)
    if cards is None or cards["total"] == 0:
        return _error_page(
            _t(lang, "lite_noKanjiInGroup"),
            _t(lang, "lite_noGroupMsg", by=by, value=value),
            404,
            theme,
            _controls(request),
            lang,
        )

    # Cards thread the group as the next back-context: `from` is the group's
    # display label, `gq` is a copy of this exact URL's params so the kanji
    # page's "← Back to {label}" returns here verbatim (pagination included).
    gq = f"by={quote(by)}&value={quote(str(_int_value))}&n={size}&offset={start}"
    if frm:
        gq += f"&from={quote(frm, safe='')}"
    gq_enc = quote(gq, safe="")
    items = "".join(
        f'<li class="kg-card">'
        f'<a href="/lite/kanji/{esc(quote(card["literal"], safe=""))}'
        f'?from={quote(cards["label"], safe="")}&amp;gq={gq_enc}">'
        f'<span class="kg-glyph" lang="ja">{esc(card["literal"])}</span>'
        f'<span class="kg-gloss">{esc((card.get("meanings") or ["—"])[0])}</span>'
        f'<span class="kg-meta">{esc(_kg_meta(card, lang))}</span></a></li>'
        for card in cards["kanjis"]
    )
    nav = []
    if start > 0:
        previous = _href("/lite/kanji/group", by=by, value=value, n=size, offset=max(start - size, 0))
        if frm:
            previous += f"&from={quote(frm, safe='')}"
        nav.append(f'<a class="btn" href="{previous}">{esc(_t(lang, "previous"))}</a>')
    if start + size < cards["total"]:
        following = _href("/lite/kanji/group", by=by, value=value, n=size, offset=start + size)
        if frm:
            following += f"&from={quote(frm, safe='')}"
        nav.append(f'<a class="btn" href="{following}">{esc(_t(lang, "next"))}</a>')
    if nav:
        pages = (cards["total"] + size - 1) // size
        label = _t(lang, "pageOf", page=start // size + 1, pages=pages)
        nav.insert(1, f'<span class="kg-pager-label">{esc(label)}</span>')
        pagination = f'<nav class="kg-pager" aria-label="pages">{" ".join(nav)}</nav>'
    else:
        pagination = ""

    back_href = (
        f'/lite/kanji/{quote(frm, safe="")}'
        if len(frm) == 1 and is_kanji(frm)
        else _href("/lite/search", q=frm) if frm
        else "/lite"
    )
    back_label = (
        f"← {esc(_t(lang, 'backTo', word=frm))}" if frm else f"← {esc(_t(lang, 'backToSearch'))}"
    )
    group_label = esc(cards["label"])
    suffix = esc(_t(lang, "kanjiSuffix"))
    subtitle = esc(_t(lang, "lite_groupSubtitle", group=group_label.lower() if lang == "en" else group_label))
    body = f"""<h1 class="kgroup-title">{group_label} {suffix}
<span class="kgroup-total">{cards["total"]}</span></h1>
<p class="kgroup-sub">{subtitle}</p>
<ul class="kg-grid">{items}</ul>
{pagination}
<div class="kgroup-bottom-actions"><a href="{back_href}" class="btn">{back_label}</a></div>"""
    return _page(
        cards["label"], body, cache=_CACHE_STATIC, controls=_controls(request), theme=theme, lang=lang
    )


def _kanji_body(request: Request, card: dict, from_word: str = "") -> str:
    """The kanji card used by both /lite/kanji/{char} and the pinned card for a
    single-kanji search — KANJIDIC2 data plus the static KanjiVG SVG. Structured
    like the web UI's KanjiCard: left column with the glyph, stroke diagram and
    badges, right column with meanings, reading chips and a common-words tile
    grid. The dedicated kanji page carries a search row above the card (with the
    Furigana toggle in it), so no action row is rendered here."""
    furi = _read_furi(request)
    lang = _read_lang(request)
    char = card.get("literal") or ""

    badges = " ".join(_badge(badge, from_word) for badge in card.get("meta") or [])

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
        f'<div class="ksection"><p class="ksection-title">{esc(_t(lang, "commonWords"))}</p>'
        f'<ul class="kwords">{words}</ul></div>'
        if words
        else ""
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
            f'role="img" aria-label="{esc(_t(lang, "lite_strokeAria", char=char))}">{paths}{numbers}</svg></div>'
        )

    meanings_title = esc(_t(lang, "meanings"))
    return f"""<div class="kanji-card">
<div class="kanji-left">
<p class="kanji-glyph" lang="ja">{esc(card.get("literal"))}</p>
{stroke_html}
<p class="kbadges">{badges}</p>
</div>
<div class="kanji-right">
<div class="ksection"><p class="ksection-title">{meanings_title}</p><p class="meanings">{meaning_line}</p></div>
{f'<div class="ksection">{reading_rows}</div>' if reading_rows else ""}
{words_html}
</div>
</div>"""


@router.get("/lite/kanji/{char}", response_class=HTMLResponse)
def lite_kanji(request: Request, char: str, log: bool = Query(True, include_in_schema=False),
               frm: str = Query("", alias="from"), gq: str = Query("", alias="gq"),
               chn: str = Query("", alias="chain")) -> Response:
    theme = _read_theme(request)
    lang = _read_lang(request)
    if not is_kanji(char):
        return _error_page(
            _t(lang, "lite_notKanji"), _t(lang, "lite_notKanjiMsg"), 400, theme, _controls(request), lang
        )
    card = kanji_card(char, strokes=True)
    if not card:
        return _error_page(
            _t(lang, "lite_kanjiNotFound"),
            _t(lang, "noKanjiEntry", char=char),
            404,
            theme,
            _controls(request),
            lang,
        )
    if log:
        telemetry().kanji_lookup(char, source="lite")
    if frm:
        # Back link target: reconstruct from frm (single kanji → kanji page,
        # otherwise → search). Thread frm's predecessor (first element of chn)
        # as `from` so the destination keeps its own back-context — this is
        # what lets "← Back" walk the full chain instead of skipping.
        if len(frm) == 1 and is_kanji(frm):
            back_href = f"/lite/kanji/{quote(frm, safe='')}"
        else:
            back_href = _href("/lite/search", q=frm)
        chain_parts = chn.split("|") if chn else []
        prev_frm = chain_parts[0] if chain_parts else ""
        prev_chain = "|".join(chain_parts[1:]) if len(chain_parts) > 1 else ""
        if prev_frm:
            sep = "&" if "?" in back_href else "?"
            back_href += f"{sep}from={quote(prev_frm, safe='')}"
            if prev_chain:
                back_href += f"&chain={quote(prev_chain, safe='')}"
        back_label = f"← {esc(_t(lang, 'backTo', word=frm))}"
    elif gq:
        # Arrival from a kanji-group card: `frm` is the group's label, `gq` a
        # pre-encoded copy of that group page's params — return there verbatim
        # (esc()ed so a crafted gq can't break out of the href attribute).
        back_href = f"/lite/kanji/group?{esc(gq)}"
        back_label = (
            f"← {esc(_t(lang, 'backTo', word=frm))}" if frm else f"← {esc(_t(lang, 'lite_backToGroup'))}"
        )
    else:
        back_href, back_label = "/lite", f"← {esc(_t(lang, 'backToSearch'))}"
    furi = _read_furi(request)
    current = _current_path(request)
    search_form = _search_form(lang=lang, furi=furi, next_url=current, from_word=char, frm=frm, chain=chn)
    return _page(
        _t(lang, "lite_kanjiPageTitle", char=char),
        # Badges thread this kanji (not the inherited word) as the next
        # back-context — the chain always names the page you were just on.
        search_form
        + _kanji_body(request, card, from_word=char)
        + f'<div class="kanji-page-back"><a class="btn" href="{back_href}">{back_label}</a></div>',
        cache=_CACHE_STATIC,
        controls=_controls(request),
        theme=theme,
        lang=lang,
        furi=furi,
    )


# ── About ────────────────────────────────────────────────────────────────────
# Sections and copy mirror web/src/routes/about/+page.svelte (which pulls its
# text from i18n.svelte.ts), adapted to what Lite itself does.

@router.get("/lite/about", response_class=HTMLResponse)
def lite_about(request: Request) -> HTMLResponse:
    # Follows the interface language like the SPA's About page (same i18n
    # keys). The footer and /lite/privacy stay English: those are the
    # legal/credit lines (see web/src/lib/components/Footer.svelte).
    lang = _read_lang(request)
    data_para = (
        f'{esc(_t(lang, "dataBefore"))}'
        '<a href="https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project"'
        ' target="_blank" rel="noopener noreferrer">JMdict</a>'
        f'{esc(_t(lang, "dataAnd"))}'
        '<a href="https://www.edrdg.org/wiki/index.php/KANJIDIC_Project"'
        ' target="_blank" rel="noopener noreferrer">KANJIDIC2</a>'
        f'{esc(_t(lang, "dataAfter"))}'
        '<a href="https://www.edrdg.org/wiki/index.php/Tanaka_Corpus"'
        ' target="_blank" rel="noopener noreferrer">Tanaka Corpus</a>'
        f'{esc(_t(lang, "dataAfter2"))}'
        '<a href="https://kanjivg.tagaini.net/" target="_blank" rel="noopener noreferrer">KanjiVG</a>'
        f'{esc(_t(lang, "dataAfter3"))}'
    )
    source_para = (
        f'{esc(_t(lang, "sourceBefore"))}'
        '<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">'
        f'{esc(_t(lang, "sourceLink"))}</a>'
        f'{esc(_t(lang, "sourceAfter"))}'
    )
    body = f"""<article class="about">
<div class="about-title"><img src="{_EMBLEM_URL}" alt="" width="40" height="40">
<h1>{esc(_t(lang, "aboutTitle"))}</h1></div>
<p class="lede">{esc(_t(lang, "aboutLede"))}</p>
<h2>{esc(_t(lang, "whatItDoes"))}</h2>
<ul>
<li><b>{esc(_t(lang, "search"))}</b> — {esc(_t(lang, "searchText"))}</li>
<li><b>{esc(_t(lang, "breakdownBold"))}</b> — {esc(_t(lang, "breakdownText"))}</li>
<li><b>{esc(_t(lang, "kanjiBold"))}</b> — {esc(_t(lang, "kanjiText"))}</li>
</ul>
<h2 id="lite">{esc(_t(lang, "liteVsFull"))}</h2>
<p>{esc(_t(lang, "liteVsFullText"))}</p>
<h2>{esc(_t(lang, "howItWorks"))}</h2>
<p>{esc(_t(lang, "lite_howTextLite"))}</p>
<h2>{esc(_t(lang, "dataSources"))}</h2>
<p>{data_para}</p>
<h2>{esc(_t(lang, "privacy"))}</h2>
<p>{esc(_t(lang, "privacyText"))}</p>
<p><a href="/lite/privacy">{esc(_t(lang, "privacyMore"))}</a></p>
<h2>{esc(_t(lang, "source"))}</h2>
<p>{source_para}</p>
<h2>{esc(_t(lang, "version"))}</h2>
<p class="muted">Reikun v{esc(APP_VERSION)}</p>
</article>"""
    return _page(
        _t(lang, "aboutTitle"),
        body,
        cache=_CACHE_STATIC,
        controls=_controls(request),
        theme=_read_theme(request),
        lang=lang,
    )


# ── Privacy ──────────────────────────────────────────────────────────────────
# English in every language and static copy, mirroring
# web/src/routes/privacy/+page.svelte — legal text is not localised (see the
# note in web/src/lib/components/Footer.svelte). Keep the two documents in
# sync when either changes.

_PRIVACY_BODY = """<article class="about">
<h1>Privacy Policy</h1>
<p class="lede">Reikun is free and needs no account. This page describes exactly what
the service records, what it never records, and how long it is kept. Last updated: November 2026.</p>
<h2>What is never collected</h2>
<ul>
<li>No accounts and no sign-in — the dictionary works fully anonymously.
The only cookies are first-party preference cookies (theme, language,
furigana, recent searches).</li>
<li>No cross-site tracking and no advertising: telemetry never records IP
addresses or user-agent strings, and no third-party ad or analytics cookies
are set.</li>
<li>Cloudflare Web Analytics, when enabled, is a cookieless beacon that
reports aggregate page-view metrics only.</li>
</ul>
<h2>What is recorded to improve the dictionary</h2>
<p>Search requests are logged: the query text as you typed it, the
rewritten/translated form used for retrieval, the search mode, result counts
and latency. These logs train better embeddings and ranking. Kanji-detail
views are logged the same way.</p>
<p>Feedback (thumbs up/down) is tied to a one-way SHA-256 hash of the query,
never its raw text. Grammar-explanation requests store the sentence only as a
SHA-256 hash, alongside the JLPT level and latency.</p>
<h2>What is stored in your browser</h2>
<p>Recent searches, theme, language and furigana preference are kept in your
browser's local storage and in small first-party cookies, so the full and Lite
versions stay in sync. They are used only to render pages and are not part of
the server-side logs above.</p>
<h2>Third-party LLM providers</h2>
<p>Grammar explanations and English descriptive query rewrites are generated
on demand by an external LLM provider. When you request an explanation, the
Japanese sentence, its English translation and the selected JLPT level are
sent to the provider; long English descriptive queries may also be sent for
rewriting. Provider-side retention is governed by the provider's own terms.</p>
<h2>Where data lives and how long it is kept</h2>
<p>On the hosted deployment, telemetry goes to the platform's log store.
Self-hosted instances can persist events to a local SQLite database instead;
there, rows are kept indefinitely by default — setting
<code>TELEMETRY_RETENTION_DAYS</code> turns on an automatic purge of rows
older than that window. Hashes cannot be reversed.</p>
<h2>Questions</h2>
<p>Open an issue or discussion at
<a href="https://github.com/AnkS4/Reikun" target="_blank"
rel="noopener noreferrer">github.com/AnkS4/Reikun</a>.</p>
</article>"""


@router.get("/lite/privacy", response_class=HTMLResponse, include_in_schema=False)
def lite_privacy(request: Request) -> HTMLResponse:
    # English in every language, like the About page and the footer — the
    # policy is legal text, not UI copy. English-only keeps the page
    # shared-cacheable regardless of language cookies.
    return _page(
        "Privacy Policy",
        _PRIVACY_BODY,
        cache=_CACHE_STATIC,
        controls=_controls(request),
        theme=_read_theme(request),
        lang="en",
    )
