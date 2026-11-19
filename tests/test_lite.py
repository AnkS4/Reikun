"""Smoke tests for the JavaScript-free UI (/lite).

Everything here is backed by committed data or request validation, so it runs
without Qdrant or an LLM — /lite/search result rendering and /lite/conjugations
lookups need live services and stay out of CI scope (cookies, toggles and the
hero are verified without them).
"""

import json
import time
from urllib.parse import quote, unquote

import pytest
from fastapi.testclient import TestClient

from app import lite
from app.api import APP_VERSION, app

client = TestClient(app)


def _lite_css() -> str:
    """The Lite stylesheet (palette included) — served once, cached forever."""
    return client.get("/lite/static/lite.css").text


def test_home_is_html_without_javascript() -> None:
    r = client.get("/lite")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert 'action="/lite/search"' in r.text and 'name="q"' in r.text
    assert "<script" not in r.text.lower()


def test_home_browse_links() -> None:
    client.cookies.clear()
    home = client.get("/lite").text
    # Same three browse tiles as the SPA homepage grid — glyph, title,
    # description and link. The kana tile is the Plex JP あ (text, no icon face).
    assert home.count('class="browse-tile"') == 3
    assert 'href="/lite/kanji/group"' in home
    assert 'href="/lite/loanwords"' in home
    assert 'href="/lite/kana"' in home
    assert 'class="browse-icon tile-kana"' in home
    # Tiles draw from the subset icon font like the top-right controls.
    assert home.count('class="icon icon-') >= 4
    assert 'icon-book-open-text' in home and 'icon-lang' in home


def test_lite_serves_the_plex_mirror() -> None:
    client.cookies.clear()
    css = client.get("/lite/fonts/fonts.css")
    assert css.status_code == 200
    assert css.headers["cache-control"] == "public, max-age=31536000, immutable"
    body = css.text
    assert "@font-face" in body
    assert "ibm-plex-sans-jp-w400-japanese" in body
    home = client.get("/lite").text
    marker = '<link rel="stylesheet" href="/lite/fonts/fonts.css'
    assert marker in home
    # The mirror is declared before the lite stylesheet (faces first).
    assert home.index(marker) < home.index('<link rel="stylesheet" href="/lite/static/lite.css')
    sample = client.get("/lite/fonts/files/ibm-plex-sans-jp-w400-japanese-e5e9ee94.woff2")
    assert sample.status_code == 200
    assert sample.headers["content-type"].startswith("font/woff2")
    assert sample.content[:4] == b"wOF2"
    # Traversal and unknown shapes never leave the files dir.
    assert client.get("/lite/fonts/files/../../app/lite/__init__.py").status_code == 404
    assert client.get("/lite/fonts/files/fonts.css").status_code == 404


def test_kana_page_lists_gojuon() -> None:
    client.cookies.clear()
    r = client.get("/lite/kana")
    assert r.status_code == 200
    # Both tabs, hiragana chart by default, back-link stays inside lite.
    assert 'href="/lite/kana?variant=hiragana"' in r.text
    assert 'href="/lite/kana?variant=katakana"' in r.text
    assert ">あ<" in r.text and ">ん<" in r.text and ">ぽ<" in r.text
    assert 'href="/lite"' in r.text and 'href="/kana"' not in r.text
    kata = client.get("/lite/kana?variant=katakana").text
    assert ">ア<" in kata and ">ン<" in kata and ">ポ<" in kata
    # Unknown variant → the 400 error page, not a crash.
    bad = client.get("/lite/kana?variant=romaji")
    assert bad.status_code == 400


def test_home_mirrors_spa_hero_and_examples() -> None:
    r = client.get("/lite")
    # Same brand subtext and tagline as the Svelte hero (brand.ts / i18n),
    # plus the SPA's example-search pills, the random-kanji button, and the
    # LITE tag next to the title (like the compact header).
    assert "Semantic Japanese Dictionary &amp; Reading Assistant" in r.text
    assert "例訓" in r.text
    assert "/lite/kanji/random" in r.text
    assert "咲く" in r.text and "大君" in r.text and "courage" in r.text and "to walk" in r.text
    # The no-JS random button is a formaction submit, not a script.
    assert 'formaction="/lite/kanji/random"' in r.text
    assert '<span class="tag">lite</span>' in r.text
    assert 'class="tagline"' in r.text


def test_search_row_buttons_are_one_consistent_style() -> None:
    home = client.get("/lite").text
    # All text, same .btn treatment — no lone kana glyph sticking out.
    assert ">Search</button>" in home and ">Random kanji</button>" in home
    assert ">Furigana</a>" in home
    assert ">あ</a>" not in home


def test_theme_toggle_is_one_click_and_variant_switch(monkeypatch) -> None:
    from app import lite as lite_module

    monkeypatch.setattr(lite_module, "WEB_BASE_URL", "http://127.0.0.1:5173")
    home = client.get("/lite").text
    # System default: both directions are rendered as icon buttons but the CSS
    # hides the one matching the OS scheme — exactly one clickable toggle on
    # first visit, no explicit "system" option (as the SPA's popover would need).
    assert 'class="theme-toggle"' in home and "to-light" in home and "to-dark" in home
    assert home.count("/lite/theme") >= 2  # both directions present
    assert 'aria-label="Switch to the light theme"' in home
    assert 'aria-label="Switch to the dark theme"' in home
    controls = home.split("<main>")[0].split('class="controls"')[1].split("skip-link")[0]
    # Controls mirror the SPA's header cluster order and icon set — full
    # switch, status dot, theme sun/moon and the languages menu trigger — but
    # the glyphs come from the subset icon font (.icon-*), never SVG:
    # hardened browsers (svg.disabled) blank inline SVG for the no-JS
    # visitors lite serves.
    assert "<svg" not in controls
    assert 'class="icon icon-full"' in controls and 'class="icon icon-db"' in controls
    assert 'class="icon icon-sun"' in controls and 'class="icon icon-moon"' in controls
    assert 'class="icon icon-lang"' in controls
    assert 'aria-label="Switch to the full interface"' in controls
    assert 'class="icon-link"' in controls and 'class="status-dot' in controls
    assert 'class="theme-toggle"' in controls and 'class="lang-menu"' in controls
    assert "http://127.0.0.1:5173" in controls
    monkeypatch.undo()
    assert 'Switch to the full interface' not in client.get("/lite").text  # unset → button hidden


def test_theme_switch_sets_cookie_and_palette() -> None:
    client.cookies.clear()
    try:
        # Dark = the pure-black palette; system (no cookie) uses the media query.
        r = client.get("/lite/theme", params={"v": "dark", "next": "/lite/search?q=日"}, follow_redirects=False)
        assert r.status_code == 303
        assert "lite_theme=dark" in r.headers.get("set-cookie", "")
        assert r.headers["location"] == "/lite/search?q=%E6%97%A5"  # starlette encodes
        dark = client.get("/lite")  # client keeps the cookie
        # The palette lives in the cached stylesheet; the page only says which
        # theme to use via data-theme on <html>.
        assert 'data-theme="dark"' in dark.text
        assert "--bg:#000000" in _lite_css()  # dark palette in the stylesheet
        # One-click toggle: a pinned theme shows only the button to the other one.
        assert 'aria-label="Switch to the light theme"' in dark.text
        assert 'aria-label="Switch to the dark theme"' not in dark.text
        assert 'class="theme-toggle"' not in dark.text
        light = client.get("/lite/theme", params={"v": "light"}, follow_redirects=False)
        assert "lite_theme=light" in light.headers.get("set-cookie", "")
        light_page = client.get("/lite")
        assert 'data-theme="light"' in light_page.text
        assert "--bg:#ffffff" in _lite_css()
        # Unknown values leave the current choice alone (system is the default,
        # not a stored choice, so there is nothing to reset to).
        same = client.get("/lite/theme", params={"v": "nope"}, follow_redirects=False)
        assert "lite_theme" not in same.headers.get("set-cookie", "")
        assert next(c for c in client.cookies.jar if c.name == "lite_theme").value == "light"
    finally:  # restore the default even on failure — later tests depend on it
        client.cookies.clear()  # no cookie → system preference


def test_legacy_oled_cookie_resolves_to_dark() -> None:
    client.cookies.set("lite_theme", "oled")
    try:
        page = client.get("/lite")
        assert 'data-theme="dark"' in page.text
        assert "--bg:#000000" in _lite_css()
    finally:
        client.cookies.clear()
    # No cookie at all → "system": light base + media-query dark override.
    home = client.get("/lite")
    assert 'data-theme="system"' in home.text
    css = _lite_css()
    assert "--bg:#ffffff" in css and "prefers-color-scheme:dark" in css


def test_stroke_paths_are_outlines_like_the_spa() -> None:
    # KanjiVG `d`s are outlines — lite draws them stroked (fill:none), the way
    # the SPA's StrokeSvg does; filling them yields blobs.
    client.get("/lite/kanji/日")
    css = client.get("/lite/static/lite.css").text
    assert "fill:none;stroke:currentColor" in css


def test_status_chip_is_a_native_disclosure() -> None:
    # The Lite status chip mirrors the SPA's status dot as a <details>
    # disclosure: the summary is the tinted glyph, and the panel carries the
    # same title/state/detail text the SPA's hover popover shows.
    client.cookies.clear()
    home = client.get("/lite")
    assert 'class="status-menu"' in home.text
    assert 'class="status-dot' in home.text
    assert 'class="status-pop"' in home.text
    assert 'class="popover-title"' in home.text
    assert 'class="status-line"' in home.text and 'class="status-sub"' in home.text
    controls = home.text.split('class="controls"')[1]
    assert controls.index("status-dot") < controls.index("theme-toggle") < controls.index("lang-menu")


def test_recent_pills_from_cookie_replace_examples() -> None:
    value = quote(json.dumps(["走る"], separators=(",", ":")), safe="")
    client.cookies.set("lite_recent", value)
    try:
        home = client.get("/lite")
        assert "Recent searches" in home.text and "走る" in home.text
        assert "Example searches" not in home.text  # SPA behaviour: recent wins
    finally:
        client.cookies.clear()


def test_recent_clear_redirects_and_writes_empty_shared_list() -> None:
    # Not a delete_cookie: the shared list is also read by the web UI, where an
    # absent cookie means "no shared state — keep your local copy" and would
    # resurrect the cleared history. An explicit [] clears every reader.
    r = client.get("/lite/recent/clear", follow_redirects=False)
    assert r.status_code == 303
    assert 'lite_recent="[]"' in r.headers.get("set-cookie", "")  # starlette quotes the value


def test_recent_cookie_shared_shape_stays_within_browser_budget() -> None:
    # The cookie is the shared channel with the web UI (web/src/lib/recent.ts),
    # read on every request by both variants — it must survive the browser's
    # ~4KB per-cookie cap whatever the queries: the encoded value is capped,
    # over-long entries dropped, and the count closes on the SPA's list cap.
    long_items = [f"通{'語' * 120}" for _ in range(4)]  # 4 items x ~121 chars
    value = quote(json.dumps(long_items, separators=(",", ":")), safe="")
    client.cookies.set("lite_recent", value)
    try:
        r = client.get("/lite/search", params={"q": "日"}, follow_redirects=False)
        set_cookie = r.headers.get("set-cookie", "")
        assert "lite_recent=" in set_cookie
        encoded = set_cookie.split("lite_recent=")[1].split(";")[0]
        assert len(encoded) <= 2400  # browsers cap a cookie near 4KB
        stored = json.loads(unquote(encoded))
        assert stored[0] == "日"  # newest entry always kept
        assert len(stored) <= 8 and all(len(i) <= 150 for i in stored)
        # oldest long entries were the ones dropped, never the new search
        assert len(json.loads(unquote(value))) > len(stored)
    finally:
        client.cookies.clear()


def test_furigana_toggle_flips_cookie_and_hides_readings() -> None:
    client.cookies.clear()
    try:
        assert "<rt>" in client.get("/lite/kanji/家").text  # on by default
        r = client.get("/lite/furigana", params={"next": "/lite/search?q=家"}, follow_redirects=False)
        assert r.status_code == 303
        assert "lite_furi=0" in r.headers.get("set-cookie", "")
        assert r.headers["location"] == "/lite/search?q=%E5%AE%B6"  # starlette encodes
        card = client.get("/lite/kanji/家")  # client keeps the cookie
        assert card.status_code == 200 and "<rt>" not in card.text
        # And the toggle link reflects + can flip the state back.
        assert "/lite/furigana" in card.text
    finally:  # restore the default even on failure — later tests depend on it
        client.get("/lite/furigana", follow_redirects=False)
    assert "<rt>" in client.get("/lite/kanji/家").text


def test_furigana_next_is_sites_only() -> None:
    r = client.get("/lite/furigana", params={"next": "https://evil.example"}, follow_redirects=False)
    assert r.headers["location"] == "/lite"
    r = client.get("/lite/furigana", params={"next": "//evil.example"}, follow_redirects=False)
    assert r.headers["location"] == "/lite"


def test_search_without_query_shows_form() -> None:
    r = client.get("/lite/search")
    assert r.status_code == 200 and 'name="q"' in r.text


def test_kanji_page_from_committed_data() -> None:
    client.cookies.clear()  # furigana preference defaults to on
    r = client.get("/lite/kanji/家")
    assert r.status_code == 200
    assert "家" in r.text
    assert "<svg" in r.text and "<ruby" in r.text
    assert "/lite/kanji/group?by=" in r.text
    # The dedicated page gets its Furigana toggle — but no "Search X in the
    # dictionary" / "Random kanji" actions (that row was redundant noise).
    assert ">Furigana</a>" in r.text
    assert "Search 家 in the dictionary" not in r.text
    assert 'href="/lite/kanji/random"' not in r.text


def test_kanji_page_rejects_non_kanji() -> None:
    assert client.get("/lite/kanji/x").status_code == 400


def test_kanji_group_page() -> None:
    r = client.get("/lite/kanji/group", params={"by": "strokes", "value": 10})
    assert r.status_code == 200
    assert "/lite/kanji/" in r.text


def test_kanji_group_category_picker() -> None:
    # No `by` (or an unknown one) renders the category picker — the same
    # browse tiles as the homepage — not an error page.
    for params in ({}, {"by": "color"}):
        r = client.get("/lite/kanji/group", params=params)
        assert r.status_code == 200
        assert r.text.count('class="browse-tile"') == 3
        assert 'href="/lite/kanji/group?by=strokes"' in r.text
        assert 'href="/lite/kanji/group?by=grade"' in r.text
        assert 'href="/lite/kanji/group?by=jlpt"' in r.text


def test_kanji_group_value_picker() -> None:
    # A `by` without a usable value lists every available value + count,
    # under a title-cased heading, with no back-to-categories button.
    r = client.get("/lite/kanji/group", params={"by": "strokes"})
    assert r.status_code == 200
    assert "by=strokes&amp;value=1" in r.text
    assert "by=strokes&amp;value=34" in r.text
    assert "Strokes" in r.text
    assert "All categories" not in r.text


def test_kanji_group_non_integer_value_shows_picker_not_json() -> None:
    # FastAPI would answer an int parse failure with a bare JSON 422 body —
    # lite promises HTML, so the handler coerces and falls into the picker.
    r = client.get("/lite/kanji/group", params={"by": "strokes", "value": "abc"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "by=strokes&amp;value=" in r.text


def test_error_and_empty_pages_carry_the_controls_row() -> None:
    # Every lite page offers the theme toggle and variant switch — including
    # the empty form and error pages. A missing row would strand a pinned-theme
    # visitor (e.g. hitting /lite/search?q= empty on a stale bookmark).
    empty = client.get("/lite/search", params={"q": ""})
    assert empty.status_code == 200 and 'class="controls"' in empty.text
    client.cookies.clear()  # start from a pinned theme, like a returning visitor
    client.cookies.set("lite_theme", "dark")
    try:
        pinned = client.get("/lite/search", params={"q": ""})
        assert 'data-theme="dark"' in pinned.text and 'class="controls"' in pinned.text
    finally:
        client.cookies.clear()
    bad = client.get("/lite/kanji/x")
    assert bad.status_code == 400 and 'class="controls"' in bad.text


def test_random_kanji_redirects_to_card() -> None:
    r = client.get("/lite/kanji/random", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/lite/kanji/")
    # The pick joins the shared recents cookie — the same channel the SPA
    # reads — so the homepage pills show it after the redirect.
    set_cookie = r.headers.get("set-cookie", "")
    assert "lite_recent=" in set_cookie
    char = unquote(r.headers["location"].rsplit("/", 1)[-1].split("?")[0])
    encoded = set_cookie.split("lite_recent=")[1].split(";")[0].strip('"')
    assert json.loads(unquote(encoded))[0] == char


def test_conjugations_without_word_shows_notice() -> None:
    r = client.get("/lite/conjugations")
    assert r.status_code == 200
    assert "No word given" in r.text


def test_no_explain_in_lite() -> None:
    # Grammar explanations are intentionally absent from lite (LLM cost/ethics):
    # the route must not exist and the search page must not link to it.
    assert client.get("/lite/explain").status_code == 404
    home = client.get("/lite").text
    assert "explain" not in home.lower()


def test_about_page() -> None:
    r = client.get("/lite/about")
    assert r.status_code == 200
    assert "JMdict" in r.text and "KANJIDIC2" in r.text
    # SPA-parity sections and type treatment (mono labels, muted body).
    assert 'class="about"' in r.text
    assert "Data and sources" in r.text and "Privacy" in r.text and "Source" in r.text
    # Release version, server-rendered from pyproject.toml (no extra request).
    assert f"Reikun v{APP_VERSION}" in r.text
    # The privacy section links the dedicated policy page.
    assert 'href="/lite/privacy"' in r.text
    # Same section order as the SPA About, with a dedicated Version section and
    # the anchor the home page's lite note links to.
    assert '<h2 id="lite">' in r.text and "<h2>Version</h2>" in r.text
    assert 'href="/lite/about#lite"' in client.get("/lite").text


def test_about_page_has_no_external_assets() -> None:
    # Lite stays asset-free apart from its stylesheet: no emblem request.
    r = client.get("/lite/about")
    assert "<img" not in r.text and "emblem" not in r.text
    assert client.get("/lite/static/emblem.svg").status_code == 404


def test_privacy_page(monkeypatch: pytest.MonkeyPatch) -> None:
    # English in every language (legal text, like the footer), and
    # shared-cacheable like the About page. Pages are only shared once the
    # status chip says "Ready", so pin a fresh ready probe: CI has no Qdrant,
    # and a local one would make the result depend on it.
    monkeypatch.setitem(lite._status_snapshot, "ok", True)
    monkeypatch.setitem(lite._status_snapshot, "count", 1)
    monkeypatch.setitem(lite._status_snapshot, "at", time.monotonic())
    r = client.get("/lite/privacy")
    assert r.status_code == 200
    assert "Privacy Policy" in r.text
    assert "TELEMETRY_RETENTION_DAYS" in r.text
    assert "public" in r.headers["cache-control"]
    # The footer links it from every lite page.
    assert 'href="/lite/privacy"' in client.get("/lite").text


def test_language_toggle_flips_cookie_and_translates_the_page(monkeypatch: pytest.MonkeyPatch) -> None:
    client.cookies.clear()
    try:
        r = client.get("/lite/lang", params={"v": "ja", "next": "/lite/search?q=家"}, follow_redirects=False)
        assert r.status_code == 303
        assert "lite_lang=ja" in r.headers.get("set-cookie", "")
        assert r.headers["location"] == "/lite/search?q=%E5%AE%B6"  # starlette encodes
        home = client.get("/lite")  # client keeps the cookie
        assert '<html lang="ja"' in home.text
        assert ">検索</button>" in home.text  # search button
        assert 'class="lang-menu"' in home.text  # <details> disclosure menu
        assert 'aria-label="インターフェースの言語: 日本語"' in home.text  # menu labelled in-page language
        assert 'href="/lite/lang?v=en&next=' in home.text  # English entry in the list
        # The About page follows the language (like the SPA's), so with a
        # language cookie it is private. The privacy policy's legal text stays
        # English in every language (like the footer), but its controls row
        # still localizes — so a non-English visitor gets a private copy too.
        # Pages are only shared once the status chip says "Ready", so pin a
        # fresh ready probe: CI has no Qdrant, and a local one would make the
        # result depend on it.
        monkeypatch.setitem(lite._status_snapshot, "ok", True)
        monkeypatch.setitem(lite._status_snapshot, "count", 1)
        monkeypatch.setitem(lite._status_snapshot, "at", time.monotonic())
        about = client.get("/lite/about")
        assert "Reikunについて" in about.text and "バージョン" in about.text
        assert "private" in about.headers["cache-control"]
        privacy = client.get("/lite/privacy")
        assert "Privacy Policy" in privacy.text
        assert "private" in privacy.headers["cache-control"]
        # Unknown values leave the current choice alone (same as /lite/theme).
        same = client.get("/lite/lang", params={"v": "nope"}, follow_redirects=False)
        assert "lite_lang" not in same.headers.get("set-cookie", "")
        assert next(c for c in client.cookies.jar if c.name == "lite_lang").value == "ja"
        # Redirect target stays on /lite paths.
        bad = client.get("/lite/lang", params={"v": "en", "next": "https://evil.example"}, follow_redirects=False)
        assert bad.headers["location"] == "/lite"
    finally:  # restore the default even on failure — later tests depend on it
        client.cookies.clear()



def test_result_card_renders_etymology_line() -> None:
    # lsource arrives raw ([{lang, text}]) from search(); the card enriches it
    # to "From Spanish — tabaco" with a BCP-47 lang tag on the source form.
    result = {
        "id": 1, "kanji_form": "タバコ", "reading": "たばこ",
        "kanji_forms": [], "readings": [], "meanings": ["tobacco, cigaret"],
        "example_sentences": [], "is_common": False, "text": "",
        "inflected_forms": [], "inflection": None, "score": 1.0,
        "lsource": [{"lang": "spa", "text": "tabaco"}],
        "reading_restrictions": {},
    }
    html_out = lite._result_card("", result, True, "en")
    assert "From Spanish" in html_out
    assert 'class="etym-src" lang="es"' in html_out and "tabaco" in html_out


def test_result_card_etymology_no_text_branch() -> None:
    result = {
        "id": 2, "kanji_form": None, "reading": "えるにーにょ",
        "kanji_forms": [], "readings": [], "meanings": ["El Niño"],
        "example_sentences": [], "is_common": False, "text": "",
        "inflected_forms": [], "inflection": None, "score": 1.0,
        "lsource": [{"lang": "spa", "text": ""}],
        "reading_restrictions": {},
    }
    html_out = lite._result_card("", result, True, "en")
    assert "From Spanish" in html_out and "etym-src" not in html_out


def test_loanwords_facet_page(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lite, "loanword_facets",
        lambda: [{"lang": "spa", "name": "Spanish", "count": 164}],
    )
    r = client.get("/lite/loanwords")
    assert r.status_code == 200
    assert "Borrowed words" in r.text and "Spanish" in r.text and "164 words" in r.text
    assert 'class="kg-card"' in r.text and 'href="/lite/loanwords/spa"' in r.text


def test_loanwords_lang_page(monkeypatch: pytest.MonkeyPatch) -> None:
    result = {
        "id": 3, "kanji_form": "タバコ", "reading": "たばこ",
        "kanji_forms": [], "readings": [], "meanings": ["tobacco"],
        "example_sentences": [], "is_common": False, "text": "",
        "inflected_forms": [], "inflection": None, "score": 3.0,
        "lsource": [{"lang": "spa", "text": "tabaco", "label": "From Spanish", "tag": "es"}],
        "reading_restrictions": {},
    }
    monkeypatch.setattr(
        lite, "loanwords_page",
        lambda lang, offset, limit: {
            "lang": lang, "name": "Spanish", "total": 164, "offset": offset,
            "results": [result],
        } if lang == "spa" else None,
    )
    r = client.get("/lite/loanwords/spa")
    assert r.status_code == 200
    assert "タバコ" in r.text and "From Spanish" in r.text
    assert "All languages" in r.text and 'href="/lite/loanwords"' in r.text
    # Unknown language → the HTML 404 page, not a JSON error.
    bad = client.get("/lite/loanwords/zzz")
    assert bad.status_code == 404 and bad.headers["content-type"].startswith("text/html")


def test_loanwords_lang_page_furi_cookie_makes_it_private(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cards hide readings when the furigana toggle is off — a shared cache
    # must not serve that variant to a visitor who wants them (and vice
    # versa). Same downgrade rule as the search page.
    monkeypatch.setitem(lite._status_snapshot, "ok", True)
    monkeypatch.setitem(lite._status_snapshot, "count", 1)
    monkeypatch.setitem(lite._status_snapshot, "at", time.monotonic())
    result = {
        "id": 3, "kanji_form": "タバコ", "reading": "たばこ",
        "kanji_forms": [], "readings": [], "meanings": ["tobacco"],
        "example_sentences": [], "is_common": False, "text": "",
        "inflected_forms": [], "inflection": None, "score": 3.0,
        "lsource": [{"lang": "spa", "text": "tabaco", "label": "From Spanish", "tag": "es"}],
        "reading_restrictions": {},
    }
    monkeypatch.setattr(
        lite, "loanwords_page",
        lambda lang, offset, limit: {
            "lang": lang, "name": "Spanish", "total": 1, "offset": offset,
            "results": [result],
        },
    )
    client.cookies.set("lite_furi", "0")
    try:
        r = client.get("/lite/loanwords/spa")
        assert r.status_code == 200
        assert "private" in r.headers["cache-control"]
        assert "<rt" not in r.text  # readings hidden
    finally:
        client.cookies.clear()


def _bare_result(**extra) -> dict:
    return {
        "id": 9, "kanji_form": "試験", "reading": "しけん",
        "kanji_forms": [], "readings": [], "meanings": ["exam"],
        "example_sentences": [], "is_common": False, "text": "",
        "inflected_forms": [], "inflection": None, "score": 1.0,
        "lsource": [], "reading_restrictions": {}, **extra,
    }


def test_result_card_sense_blocks() -> None:
    result = _bare_result(
        senses=[
            {
                "glosses": ["exam"],
                "pos": ["verb", "noun", "adv", "other"],   # capped at 3
                "misc": ["on-mim", "kana", "archaic", "name"],  # tier-1 only
                "dial": [{"code": "ksb", "name": "Kansai-ben"}],
                "s_inf": ["sometimes used for zero"],
                "examples": [{"japanese": "試験を受ける", "english": "take an exam"}],
            },
            {"glosses": ["trial"], "pos": ["adv"], "misc": ["archaic"]},
        ],
    )
    html_out = lite._result_card("", result, True, "en")
    # Sense blocks carry stable fragment ids for xref deep links.
    assert 'id="r9-s1"' in html_out and 'id="r9-s2"' in html_out
    assert ">exam<" in html_out or "exam" in html_out
    assert "trial" in html_out
    # Badges live inside the sense block, not the h2.
    h2 = html_out.split("<h2")[1].split("</h2>")[0]
    assert "badge pos" not in h2 and "Kansai-ben" not in h2
    assert 'class="badge pos"' in html_out and ">Verb<" in html_out and ">Noun<" in html_out
    assert ">Adverb<" in html_out and ">Other<" not in html_out  # 4th pos tag cut
    assert "Onomatopoeia" in html_out and "Kana" in html_out
    assert "Archaic" not in html_out and ">Name<" not in html_out  # tier-2 hidden
    assert "Kansai-ben" in html_out and 'title="Dialect"' in html_out
    # Per-sense usage note renders as English JMdict text.
    assert 'class="sense-note" lang="en"' in html_out and "sometimes used for zero" in html_out
    # Per-sense example renders inside its block.
    assert "試験を受ける" in html_out and "take an exam" in html_out


def test_result_card_variant_forms() -> None:
    result = _bare_result(
        kanji_form="梔子", reading="くちなし",
        kanji_forms=["梔子", "巵子", "山梔子", "梔"],
        readings=["くちなし", "クチナシ", "しし", "さんしし"],
        reading_restrictions={
            "クチナシ": [], "しし": ["梔子", "巵子"], "さんしし": ["山梔子"],
        },
        variants={
            "forms": [
                {"form": "梔子", "readings": ["しし"], "labels": []},
                {"form": "巵子", "readings": ["しし"], "labels": []},
                {"form": "山梔子", "readings": ["さんしし"], "labels": ["oK"]},
                {"form": "梔", "readings": [], "labels": []},
            ],
            "readings": ["はな", "くちなし"],  # はな unrestricted, くちなし = primary (hidden)
            "kana_only": ["クチナシ"],
        },
    )
    html_out = lite._result_card("", result, True, "en")
    assert 'class="variants"' in html_out and "Variant forms" in html_out
    # Per-form bound readings render on their own rows.
    assert "梔子" in html_out and "しし" in html_out and "さんしし" in html_out
    # ke_inf label → localized tag.
    assert "old form" in html_out
    # Shared unrestricted line skips the primary reading (already in h2).
    assert "read as" in html_out and "はな" in html_out
    # re_nokanji reading gets the kana-only tag.
    assert "kana only" in html_out and "クチナシ" in html_out


def test_result_card_etymology_links_borrowed_words() -> None:
    result = _bare_result(
        lsource=[{"lang": "chi", "text": "你好"}],
    )
    html_out = lite._result_card("", result, True, "en")
    # The "From Chinese" label links to that language's borrowed-words page.
    assert 'class="etym-link"' in html_out
    assert 'href="/lite/loanwords/chi"' in html_out
    assert "From Chinese" in html_out
    # The source form keeps its own lang tag and stays plain text.
    assert 'class="etym-src" lang="zh"' in html_out and "你好" in html_out


def test_result_card_sense_form_restrictions() -> None:
    result = _bare_result(
        senses=[{
            "glosses": ["place"],
            "stagk": ["彼所"],
            "stagr": ["あそこ", "あすこ"],
        }],
    )
    html_out = lite._result_card("", result, True, "en")
    assert 'class="sense-variants"' in html_out
    assert "written forms: 彼所" in html_out
    assert "readings: あそこ · あすこ" in html_out


def test_result_card_sense_blocks_localized() -> None:
    result = _bare_result(
        senses=[{"glosses": ["試験"], "pos": ["verb"], "misc": ["abbr"]}],
    )
    html_out = lite._result_card("", result, True, "ja")
    assert ">動詞<" in html_out and ">略語<" in html_out


def test_result_card_xref_chips_deep_link() -> None:
    result = _bare_result(
        senses=[{
            "glosses": ["store"],
            "xrefs": [
                {"seq": "2409240", "sno": "1", "text": "お店", "type": "see"},
                {"seq": "2409240", "sno": "2", "text": "お店", "type": "see"},
                {"seq": "1", "text": "反対", "type": "ant"},
            ],
        }],
    )
    html_out = lite._result_card("", result, True, "en")
    assert "Antonyms" in html_out and "See also" in html_out
    assert 'class="chip xref-ant"' in html_out
    # Deep link: search for the headword + #r<seq>-s<sno> fragment.
    assert 'href="/lite/search?q=%E3%81%8A%E5%BA%97#r2409240-s1"' in html_out
    assert 'href="/lite/search?q=%E3%81%8A%E5%BA%97#r2409240-s2"' in html_out
    assert 'href="/lite/search?q=%E5%8F%8D%E5%AF%BE#r1"' in html_out  # no sno → card anchor
    # no xrefs → no row at all
    assert "xref-row" not in lite._result_card("", _bare_result(), True, "en")
