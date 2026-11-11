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
    assert 'aria-label="Switch to the light theme"' in home  # sun
    assert 'aria-label="Switch to the dark theme"' in home  # moon
    assert "aria-hidden" in home  # decorative glyphs: meaning lives in labels
    controls = home.split("<main>")[0].split('class="controls"')[1]
    assert "<svg" in controls and 'aria-label="Switch to the full interface"' in controls
    assert "http://127.0.0.1:5173" in controls
    monkeypatch.undo()
    assert 'Switch to the full interface' not in client.get("/lite").text  # unset → button hidden


def test_theme_switch_sets_cookie_and_palette() -> None:
    client.cookies.clear()
    try:
        # Dark = the OLED-black palette; system (no cookie) uses the media query.
        r = client.get("/lite/theme", params={"v": "dark", "next": "/lite/search?q=日"}, follow_redirects=False)
        assert r.status_code == 303
        assert "lite_theme=dark" in r.headers.get("set-cookie", "")
        assert r.headers["location"] == "/lite/search?q=%E6%97%A5"  # starlette encodes
        dark = client.get("/lite")  # client keeps the cookie
        # The palette lives in the cached stylesheet; the page only says which
        # theme to use via data-theme on <html>.
        assert 'data-theme="dark"' in dark.text
        assert "--bg:#000000" in _lite_css()  # OLED palette in the stylesheet
        # One-click toggle: a pinned theme shows only the button to the other one.
        assert 'aria-label="Switch to the light theme"' in dark.text
        assert 'aria-label="Switch to the dark theme"' not in dark.text
        assert 'class="theme-toggle"' not in dark.text
        light = client.get("/lite/theme", params={"v": "light"}, follow_redirects=False)
        assert "lite_theme=light" in light.headers.get("set-cookie", "")
        light_page = client.get("/lite")
        assert 'data-theme="light"' in light_page.text
        assert "--bg:#fcfaf6" in _lite_css()
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
    assert "--bg:#fcfaf6" in css and "prefers-color-scheme:dark" in css


def test_stroke_paths_are_outlines_like_the_spa() -> None:
    # KanjiVG `d`s are outlines — lite draws them stroked (fill:none), the way
    # the SPA's StrokeSvg does; filling them yields blobs.
    client.get("/lite/kanji/日")
    css = client.get("/lite/static/lite.css").text
    assert "fill:none;stroke:currentColor" in css


def test_status_chip_is_a_minimal_native_tooltip() -> None:
    # The Lite status chip is a database glyph (green/red) whose detail rides on
    # the native title attribute — no hover popup, no extra CSS.
    client.cookies.clear()
    home = client.get("/lite")
    assert 'class="status-dot' in home.text
    assert 'title="' in home.text
    assert 'class="status-pop"' not in home.text
    controls = home.text.split('class="controls"')[1]
    assert controls.index("status-dot") < controls.index("theme-toggle") < controls.index("Switch to")


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


def test_kanji_group_rejects_bad_key() -> None:
    assert client.get("/lite/kanji/group", params={"by": "color", "value": 1}).status_code == 404


def test_kanji_group_non_integer_value_is_an_html_404_not_json() -> None:
    # FastAPI would answer an int parse failure with a bare JSON 422 body —
    # lite promises HTML, so the handler coerces and falls into the error page.
    r = client.get("/lite/kanji/group", params={"by": "strokes", "value": "abc"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert "No kanji in group" in r.text


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


def test_privacy_page() -> None:
    # English in every language (legal text, like the footer), and
    # shared-cacheable like the About page.
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
        assert 'aria-label="Switch to English"' in home.text  # toggle offers the other language
        assert 'aria-label="表示言語"' not in home.text
        # The About page is English in every language (like the footer), so it
        # stays shared-cacheable even with a language cookie set. Pages are only
        # shared once the status chip says "Ready", so pin a fresh ready probe:
        # CI has no Qdrant, and a local one would make the result depend on it.
        monkeypatch.setitem(lite._status_snapshot, "ok", True)
        monkeypatch.setitem(lite._status_snapshot, "count", 1)
        monkeypatch.setitem(lite._status_snapshot, "at", time.monotonic())
        about = client.get("/lite/about")
        assert "Reikun について" not in about.text and "About Reikun" in about.text
        assert "public" in about.headers["cache-control"]
        # Unknown values leave the current choice alone (same as /lite/theme).
        same = client.get("/lite/lang", params={"v": "nope"}, follow_redirects=False)
        assert "lite_lang" not in same.headers.get("set-cookie", "")
        assert next(c for c in client.cookies.jar if c.name == "lite_lang").value == "ja"
        # Redirect target stays on /lite paths.
        bad = client.get("/lite/lang", params={"v": "en", "next": "https://evil.example"}, follow_redirects=False)
        assert bad.headers["location"] == "/lite"
    finally:  # restore the default even on failure — later tests depend on it
        client.cookies.clear()

