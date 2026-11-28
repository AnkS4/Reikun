"""Spanish edition of the JavaScript-free Lite UI.

The Worker rewrites es.reikun.app's browser-visible /lite paths to /es/lite
and forwards X-Reikun-Language-Pack: es. Static CSS/fonts and shared preference
endpoints remain at /lite/*.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, Response

from app.config import RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS
from app.es_families import es_families
from app.lang.es import es_conjugations, es_etymology_facets, es_etymology_page, search_es
from app.lite import (
    _COOKIE_MAX_AGE,
    _RECENT_COOKIE,
    _controls,
    _controls_lang,
    _fmt_count,
    _href,
    _icon,
    _LiteRoute,
    _read_recent,
    _read_theme,
    _recent_cookie_value,
    _secure_cookie,
    esc,
    lite_about,
)
from app.lite import (
    _header as _shared_header,
)
from app.lite import (
    _page as _shared_page,
)
from app.lite.i18n import _t
from app.ratelimit import rate_limited
from app.telemetry import telemetry

logger = logging.getLogger("reikun.lite.es")

# Same untranslatable brand line as the full Spanish SPA (pack.ts).
_BRAND_SUBTEXT_ES = "The open Spanish dictionary"

router = APIRouter(tags=["lite"], include_in_schema=False, route_class=_LiteRoute)
_search_limit = Depends(rate_limited(RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS))
_PAGE_SIZE = 20
_DEFAULT_COUNT = 10

# Four pinned searches: a Spanish verb, an English verb (no "to"), and one
# phrase in each language — a compact tour of what the dictionary handles.
_EXAMPLES = (
    ("hablar", "es"),
    ("meander", "en"),
    ("vergüenza ajena", "es"),
    ("raining cats and dogs", "en"),
)

_POS = {
    "verb": "Verbo", "noun": "Sustantivo", "adj": "Adjetivo",
    "adv": "Adverbio", "name": "Nombre propio", "phrase": "Frase",
    "prep": "Preposición", "pron": "Pronombre", "conj": "Conjunción",
    "intj": "Interjección", "abbrev": "Abreviatura", "num": "Numeral",
    "article": "Artículo", "proverb": "Refrán", "participle": "Participio",
}


def _header(*, hero: bool, lang: str) -> str:
    """Spanish chrome reuses the shared Lite header (emblem, brand link, note)."""
    tags = '<span class="tag">ALPHA</span><span class="tag">Lite</span>'
    note = (
        f'<p class="lite-note">{esc(_t(lang, "lite_note"))} '
        f'<a href="/lite/about#lite">{esc(_t(lang, "lite_noteLink"))}</a></p>'
    )
    return _shared_header(
        hero, lang,
        pack="es",
        subtext=_BRAND_SUBTEXT_ES,
        tagline=_t(lang, "es_lite_tagline"),
        tags=tags,
        note=note,
    )


# Same English-only footer as the full Spanish edition (and the Japanese
# Lite): legal/credit lines stay untranslatable in both variants.
_FOOTER = """<footer>
<p>Reikun © 2026 Aniket Satbhai ·
<a href="/lite/about">About</a> ·
<a href="/lite/privacy">Privacy</a> ·
<a href="https://github.com/AnkS4/Reikun" target="_blank" rel="noopener noreferrer">GitHub</a> ·
<a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE" target="_blank"
rel="noopener noreferrer">Apache-2.0</a></p>
<p>Dictionary data from
<a href="https://es.wiktionary.org/" target="_blank" rel="noopener noreferrer">Wiktionary</a>
(Wikimedia contributors, CC BY-SA 4.0), extracted with
<a href="https://github.com/tatuylonen/wiktextract" target="_blank" rel="noopener noreferrer">wiktextract</a>.
Sentences from <a href="https://tatoeba.org/" target="_blank" rel="noopener noreferrer">Tatoeba</a>
(CC-BY 2.0 FR). Frequency data from
<a href="https://github.com/rspeer/wordfreq" target="_blank" rel="noopener noreferrer">wordfreq</a>
(MIT).</p>
</footer>"""


def _render_page(request: Request, title: str, body: str, *, hero: bool = False) -> HTMLResponse:
    lang = _controls_lang(request)
    description = _t(lang, "es_lite_description")
    return _shared_page(
        title,
        body,
        controls=_controls(request),
        theme=_read_theme(request),
        lang=lang,
        furi=False,
        noindex=True,
        header_markup=_header(hero=hero, lang=lang),
        footer_markup=_FOOTER,
        description=description,
        status_pack="es",
        pack="es",
    )


def _search_form(query: str = "", *, autofocus: bool = False, lang: str = "es") -> str:
    focus = " autofocus" if autofocus else ""
    return (
        '<form class="search" action="/lite/search" method="get" role="search">'
        f'<input type="search" name="q" value="{esc(query)}" placeholder="{esc(_t(lang, "es_lite_placeholder"))}" '
        f'aria-label="{esc(_t(lang, "search"))}" autocomplete="off" autocapitalize="none" spellcheck="false"{focus}>'
        f'<button type="submit">{esc(_t(lang, "search"))}</button></form>'
    )


def _origin_links(origins: list[str], lang: str) -> str:
    return " ".join(
        f'<a class="pill" href="/lite/etymology?lang={quote(origin, safe="")}" lang="es">{esc(origin)}</a>'
        for origin in origins
    )


def _result_card(result: dict, lang: str = "es") -> str:
    reading = result.get("reading") or ""
    ipa = result.get("ipa")
    meanings = result.get("meanings") or []
    definitions = result.get("definitions_es") or []
    native_only = len(meanings) == len(definitions) and meanings == definitions
    english = "" if native_only or not meanings else (
        f'<section class="es-lite-defs"><p class="es-defs-label">{esc(_t(lang, "es_lite_english"))}</p><ul>'
        + "".join(f"<li>{esc(item)}</li>" for item in meanings)
        + "</ul></section>"
    )
    spanish = "" if not definitions else (
        f'<section class="es-lite-defs es-lite-native">'
        f'<p class="es-defs-label">{esc(_t(lang, "es_lite_spanish_defs"))}</p><ul lang="es">'
        + "".join(f"<li>{esc(item)}</li>" for item in definitions[:6])
        + "</ul></section>"
    )
    pos = list(dict.fromkeys(
        tag for sense in (result.get("senses") or []) for tag in (sense.get("pos") or [])
    ))
    badges = "".join(f'<span class="badge pos">{esc(_POS.get(tag, tag))}</span>' for tag in pos[:3])
    etymology = "".join(f'<p lang="es">{esc(item)}</p>' for item in result.get("etymology_es") or [])
    origins = result.get("origin_languages") or []
    origin_html = _origin_links(origins, lang) if origins else ""
    credit = (
        f'<p class="es-lite-credit"><a href="https://es.wiktionary.org/wiki/{quote(reading, safe="")}#Español" '
        f'target="_blank" rel="noopener noreferrer">{esc(_t(lang, "es_lite_wiktionary"))}</a></p>'
    ) if etymology or origins else ""
    forms = result.get("inflected_forms") or []
    conjugations = ""
    if forms:
        href = "/lite/conjugations?" + quote("word", safe="") + "=" + quote(reading, safe="")
        conjugations = (
            f'<p><a class="conj-toggle" href="{href}">{esc(_t(lang, "conjugations"))} '
            f'<span class="conj-count">{len(forms)}</span> →</a></p>'
        )
    ipa_html = f'<span class="es-ipa" lang="es">{esc(ipa)}</span>' if ipa else ""
    examples_html = ""
    if examples := result.get("examples_es") or []:
        rows = []
        for item in examples:
            if not isinstance(item, dict):
                continue
            spanish_id, english_id = item.get("spanish_id"), item.get("english_id")
            rows.append(
                f'<li><p lang="es">{esc(item.get("spanish"))}</p><p lang="en">{esc(item.get("english"))}</p>'
                f'<p class="es-lite-credit">{esc(_t(lang, "es_lite_tatoeba"))} '
                f'<a href="https://tatoeba.org/en/sentences/show/{esc(spanish_id)}" rel="noopener">'
                f'#{esc(spanish_id)}</a> ({esc(item.get("spanish_author")) or "?"}) · '
                f'<a href="https://tatoeba.org/en/sentences/show/{esc(english_id)}" rel="noopener">'
                f'#{esc(english_id)}</a>'
                f' ({esc(item.get("english_author")) or "?"}) · {esc(item.get("license"))}</p></li>'
            )
        if rows:
            examples_html = (
                f'<section class="es-lite-examples"><p class="es-defs-label">'
                f'{esc(_t(lang, "es_lite_examples"))}</p><ul>{"".join(rows)}</ul></section>'
            )
    return (
        '<article class="result-card"><div class="result-head">'
        f'<span class="headword es-headword" lang="es">{esc(reading)}</span>{ipa_html}{badges}</div>'
        f'{english}{spanish}{examples_html}{conjugations}'
        + (
            f'<section class="es-lite-etymology"><p class="es-defs-label">'
            f'{esc(_t(lang, "es_lite_etymology"))}</p>{etymology}{origin_html}{credit}</section>'
            if etymology or origins else ""
        )
        + '</article>'
    )


@router.get("/es/lite", response_class=HTMLResponse)
@router.get("/es/lite/", response_class=HTMLResponse)
def es_lite_home(request: Request) -> HTMLResponse:
    lang = _controls_lang(request)
    chips = "".join(
        f'<a class="pill" href="/lite/search?q={quote(query, safe="")}">'
        f'<span lang="{example_lang}">{esc(query)}</span></a>'
        for query, example_lang in _EXAMPLES
    )
    body = _search_form(autofocus=True, lang=lang) + (
        f'<p class="pills-label">{esc(_t(lang, "es_lite_examples"))}</p>'
        f'<div class="pills">{chips}</div>'
        f'<section class="es-lite-browse"><p class="pills-label">{esc(_t(lang, "es_lite_explore"))}</p>'
        '<div class="browse-grid two-up">'
        '<a class="browse-tile" href="/lite/etymology">'
        f'<span class="browse-icon">{_icon("blend")}</span>'
        f'<span class="browse-name">{esc(_t(lang, "es_lite_etymology"))}</span>'
        f'<span class="browse-desc">{esc(_t(lang, "es_lite_browse_etymology"))}</span></a>'
        '<a class="browse-tile" href="/lite/families">'
        f'<span class="browse-icon">{_icon("school")}</span>'
        f'<span class="browse-name">{esc(_t(lang, "es_lite_families"))}</span>'
        f'<span class="browse-desc">{esc(_t(lang, "es_lite_browse_families"))}</span></a></div></section>'
    )
    return _render_page(request, _t(lang, "es_lite_title"), body, hero=True)


@router.get("/es/lite/search", response_class=HTMLResponse, dependencies=[_search_limit])
def es_lite_search(request: Request, q: str = "") -> Response:
    query = q.strip()
    lang = _controls_lang(request)
    if not query:
        return _render_page(request, _t(lang, "search"), _search_form(autofocus=True, lang=lang))
    try:
        response = search_es(query, _DEFAULT_COUNT)
    except Exception:
        logger.exception("Spanish Lite search failed")
        body = _search_form(query, lang=lang) + f'<p class="warn">{esc(_t(lang, "es_lite_search_error"))}</p>'
        return _render_page(request, _t(lang, "es_lite_search_error_title"), body)
    top = response.results[0] if response.results else {}
    telemetry().search(
        query, rewritten_query=response.rewrite.query, rewrite_method=response.rewrite.method,
        mode=response.mode, num_results=_DEFAULT_COUNT, result_count=len(response.results),
        top_result=top.get("reading"), latency_ms=response.latency_ms,
        cached=bool(response.meta.get("cached")), route=None, embed_ms=None, retrieve_ms=None,
    )
    body = _search_form(query, lang=lang)
    body += (
        f'<p class="pills-label">'
        f'{esc(_t(lang, "es_lite_result_count", count=len(response.results)))} '
        f'· {response.latency_ms} ms</p>'
    )
    if response.results:
        body += "".join(_result_card(result, lang) for result in response.results)
    else:
        body += f'<p class="notice">{esc(_t(lang, "es_lite_no_results"))}</p>'
    page = _render_page(request, _t(lang, "lite_resultsTitle", query=query), body)
    page.set_cookie(
        _RECENT_COOKIE,
        _recent_cookie_value(request.cookies.get(_RECENT_COOKIE, ""), query),
        max_age=_COOKIE_MAX_AGE,
        samesite="lax",
        secure=_secure_cookie(request),
    )
    return page


@router.get("/es/lite/history", response_class=HTMLResponse)
def es_lite_history(request: Request) -> HTMLResponse:
    lang = _controls_lang(request)
    recent = _read_recent(request)
    body = f'<h1>{esc(_t(lang, "recentSearches"))}</h1>'
    if recent:
        # Plain pills, matching the Spanish Lite home's pinned searches.
        items = "".join(
            f'<a class="pill" href="/lite/search?q={quote(query, safe="")}">{esc(query)}</a>'
            for query in recent
        )
        label = esc(_t(lang, "recentSearches"))
        body += (
            f'<div class="pills" aria-label="{label}">{items}</div>'
            '<p><a href="/lite/recent/clear?next=%2Flite%2Fhistory">'
            f'{esc(_t(lang, "clear"))}</a></p>'
        )
    else:
        body += f'<p>{esc(_t(lang, "noRecentSearches"))}</p>'
    body += f'<p><a href="/lite">{esc(_t(lang, "backToSearch"))}</a></p>'
    return _render_page(request, _t(lang, "recentSearches"), body)


@router.get("/es/lite/conjugations", response_class=HTMLResponse)
def es_lite_conjugations(request: Request, word: str = Query(default="", max_length=150)) -> HTMLResponse:
    lang = _controls_lang(request)
    query = word.strip()
    body = (
        f'<p><a class="btn" href="/lite/search?q={quote(query, safe="")}">'
        f'← {esc(_t(lang, "backTo", word=query))}</a></p>'
    )
    if not query:
        body += f'<p class="notice">{esc(_t(lang, "es_lite_conj_no_word"))}</p>'
        return _render_page(request, _t(lang, "conjugations"), body)
    table = es_conjugations(query)
    if not table:
        body += f'<p class="notice">{esc(_t(lang, "es_lite_conj_no_data", word=query))}</p>'
        return _render_page(request, f"{_t(lang, 'conjugations')} — {query}", body)
    body += (
        f'<h1 lang="es">{esc(table["word"])}</h1><p class="pills-label">'
        f'{esc(_t(lang, "conjugations"))} ({len(table["inflected_forms"])})</p>'
    )
    body += _conjugation_tables(table["inflected_forms"], lang)
    return _render_page(request, f"{_t(lang, 'conjugations')} — {table['word']}", body)


def _conjugation_tables(rows: list[dict], lang: str) -> str:
    labels = (
        ("combined-form", _t(lang, "es_lite_conj_clitics")),
        ("imperative", _t(lang, "es_lite_conj_imperative")),
        ("subjunctive", _t(lang, "es_lite_conj_subjunctive")),
        ("conditional", _t(lang, "es_lite_conj_conditional")),
        ("indicative", _t(lang, "es_lite_conj_indicative")),
        ("infinitive", _t(lang, "es_lite_conj_nonfinite")),
        ("gerund", _t(lang, "es_lite_conj_nonfinite")),
        ("participle", _t(lang, "es_lite_conj_nonfinite")),
    )
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        surface = row.get("surface") or ""
        if not any(char.isalpha() for char in surface):
            continue
        form = row.get("form") or ""
        label = next((name for needle, name in labels if needle in form), None)
        if label:
            buckets.setdefault(label, []).append(row)
    parts = []
    for label, grouped in buckets.items():
        parts.append(
            f'<table class="conj-page-table"><caption>{esc(label)}</caption><thead><tr>'
            f'<th>{esc(_t(lang, "form"))}</th><th>{esc(_t(lang, "written"))}</th></tr></thead><tbody>'
        )
        parts.extend(
            f'<tr><th scope="row">{esc((row.get("form") or "").replace("-", " "))}</th>'
            f'<td lang="es">{esc(row.get("surface"))}</td></tr>'
            for row in grouped
        )
        parts.append('</tbody></table>')
    return "".join(parts)


@router.get("/es/lite/about", response_class=HTMLResponse)
def es_lite_about(request: Request) -> HTMLResponse:
    """Same About document as Japanese Lite, with Spanish pack chrome/credits."""
    lang = _controls_lang(request)
    return lite_about(
        request,
        header_markup=_header(hero=False, lang=lang),
        footer_markup=_FOOTER,
    )


@router.get("/es/lite/privacy", response_class=HTMLResponse)
def es_lite_privacy(request: Request) -> HTMLResponse:
    lang = _controls_lang(request)
    title = _t(lang, "privacy")
    body = f'<h1>{esc(title)}</h1><p>{esc(_t(lang, "es_lite_privacy_text"))}</p>'
    return _render_page(request, title, body)


@router.get("/es/lite/etymology", response_class=HTMLResponse)
def es_lite_etymology(request: Request, lang: str = "", offset: int = Query(default=0, ge=0)) -> HTMLResponse:
    ui_lang = _controls_lang(request)
    title = _t(ui_lang, "es_lite_etymology")
    if not lang:
        facets = es_etymology_facets()
        cards = "".join(
            f'<li><a class="browse-tile" href="/lite/etymology?lang={quote(item["lang"], safe="")}">'
            f'<span class="browse-name">{esc(item["name"])}</span><span class="browse-desc">'
            f'{esc(_t(ui_lang, "es_lite_entries", count=_fmt_count(item["count"], ui_lang)))}</span></a></li>'
            for item in facets
        )
        body = f'<h1>{esc(title)}</h1><p>{esc(_t(ui_lang, "es_lite_origin_intro"))}</p><ul class="kg-grid">{cards}</ul>'
        return _render_page(request, title, body)
    page = es_etymology_page(lang, offset, _PAGE_SIZE)
    if not page:
        body = f'<h1>{esc(title)}</h1><p>{esc(_t(ui_lang, "es_lite_no_origins"))}</p>'
        return _render_page(request, title, body)
    cards = "".join(_result_card(item, ui_lang) for item in page["results"])
    paging = []
    if offset:
        paging.append(
            f'<a class="btn" href="/lite/etymology?lang={quote(lang, safe="")}&offset={max(0, offset-_PAGE_SIZE)}">'
            f'← {esc(_t(ui_lang, "previous"))}</a>'
        )
    if offset + _PAGE_SIZE < page["total"]:
        paging.append(
            f'<a class="btn" href="/lite/etymology?lang={quote(lang, safe="")}&offset={offset+_PAGE_SIZE}">'
            f'{esc(_t(ui_lang, "next"))} →</a>'
        )
    body = (
        f'<h1 lang="es">{esc(page["name"])}</h1>'
        f'<p class="pills-label">{esc(_t(ui_lang, "es_lite_entries", count=_fmt_count(page["total"], ui_lang)))}</p>'
        f'{cards}<nav class="kg-pager">{" ".join(paging)}</nav>'
        f'<p><a href="/lite/etymology">← {esc(_t(ui_lang, "es_lite_all_origins"))}</a></p>'
    )
    return _render_page(request, f"{page['name']} — {title}", body)


@router.get("/es/lite/families", response_class=HTMLResponse)
def es_lite_families(request: Request, word: str = "") -> HTMLResponse:
    """Word families derived from Wiktionary etymology links."""
    ui_lang = _controls_lang(request)
    title = _t(ui_lang, "familiesTitle")
    families = es_families()
    chosen = next((f for f in families if f["word"].lower() == word.strip().lower()), None) if word else None
    if chosen:
        cards = "".join(
            f'<li><a class="kg-card" href="{_href("/lite/search", q=member["word"])}">'
            f'<span class="kv-value" lang="es">{esc(member["word"])}</span>'
            f'<span class="kg-meta">{esc(member["gloss"])}</span></a></li>'
            for member in chosen["members"]
        )
        count = _fmt_count(len(chosen["members"]), ui_lang)
        label = esc(_t(ui_lang, "familiesMembers", count=count))
        body = (
            f'<h1 lang="es">{esc(chosen["word"])}</h1>'
            f'<p class="pills-label">{label}</p>'
            f'<ul class="kg-grid">{cards}</ul>'
            f'<p><a href="/lite/families">← {esc(_t(ui_lang, "familiesBack"))}</a></p>'
        )
        return _render_page(request, f"{chosen['word']} — {title}", body)
    def _card(family: dict) -> str:
        count = _fmt_count(len(family["members"]), ui_lang)
        label = esc(_t(ui_lang, "familiesMembers", count=count))
        return (
            f'<li><a class="kg-card" href="{_href("/lite/families", word=family["word"])}">'
            f'<span class="kv-value" lang="es">{esc(family["word"])}</span>'
            f'<span class="kg-meta">{label}</span></a></li>'
        )

    cards = "".join(_card(family) for family in families)
    body = (
        f'<h1>{esc(title)}</h1><p>{esc(_t(ui_lang, "familiesIntro"))} '
        '<a href="https://es.wiktionary.org/" target="_blank" rel="noopener noreferrer">Wiktionary</a>.</p>'
        f'<ul class="kg-grid">{cards}</ul>'
    )
    return _render_page(request, title, body)
