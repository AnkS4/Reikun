"""Shared UI helpers: CSS, cached lookups, kanji/furigana rendering, footer."""

import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode

import streamlit as st

from app.config import COLLECTION, qdrant_client
from app.kanji_lookup import is_kanji, lookup_kanji, stroke_svg
from scripts.feedback_log import log_kanji_lookup

APP_TITLE = "Reikun (例訓)"
APP_NAME = "Reikun (例訓) — Semantic Japanese Dictionary"
APP_ICON = str(Path(__file__).resolve().parent.parent / "assets" / "logo.png")

_CSS_PATH = Path(__file__).with_name("style.css")

_STROKE_STEP_S = 0.5   # delay between consecutive strokes in the animation
_KVG_PATH = re.compile(r'<path id="kvg:[0-9a-f]+-s(\d+)"')
_KVG_NUMBER = re.compile(r"<text ")
_THEMES = ("System", "Light", "Dark")


# On a client-side page switch, Streamlit ≤1.64 can leave stale elements from
# the previous page mounted: the frontend reuses the same-position root block
# and merges children positionally, but never sweeps the old page's tail. The
# app-side workaround is to skip the client-side swap for page navigation —
# a capture-phase listener turns top-nav (and title-home) clicks into plain
# full-page loads. Cheap for this app, and immune to whatever element mix
# happens to trigger the reconciliation bug.
_NAV_HARD_RELOAD_JS = """
(function () {
  if (window.__reikunNavPatched) return;
  window.__reikunNavPatched = true;
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
})();
"""


def inject_css() -> None:
    """
    Load app/ui/style.css and install the top-nav hard-reload patch.

    Emitted as a single <style>+<script> st.html body. A style-only body is
    routed to Streamlit's event container, which does not render html
    elements (1.64) — the stylesheet silently never applies. The trailing
    script makes the body non-style-only, so the element stays in the main
    container where both take effect. st.html (not st.markdown) because only
    it can opt into executing the script.
    """
    st.html(f"<style>{_CSS_PATH.read_text(encoding='utf-8')}</style>"
            f"<script>{_NAV_HARD_RELOAD_JS}</script>",
            unsafe_allow_javascript=True)


def apply_theme(choice: str) -> None:
    """
    Persist `choice` ("System" | "Light" | "Dark") exactly like the built-in
    theme picker — which is hidden (toolbarMode=minimal) — then reload.

    The frontend stores the viewer's preference in localStorage under
    `stActiveTheme-<pathname>-v2`; writing the same key and reloading applies
    it. Call only on a user-initiated change (widget on_change), otherwise
    every rerun would re-inject the script.
    """
    st.html(
        "<script>window.localStorage.setItem('stActiveTheme-' + location.pathname + '-v2', "
        f"JSON.stringify({json.dumps(choice)})); location.reload();</script>",
        unsafe_allow_javascript=True,
    )


def _flag_theme() -> None:
    """on_change for the Theme control — the script body applies it (see header)."""
    st.session_state._theme_wanted = st.session_state.theme


def _status_theme(bar) -> None:
    """KB status badge + theme popover, rendered into the horizontal `bar` row."""
    ready, status = data_status()
    bar.badge("", color="green" if ready else "red",
              icon=":material/database:", help=status)
    with bar.popover("", icon=":material/palette:", type="tertiary", help="Theme"):
        st.segmented_control(
            "Theme", _THEMES, key="theme", bind="query-params", default="System",
            on_change=_flag_theme, label_visibility="collapsed",
            help="Switching reloads the page — open grammar explanations are cleared.",
        )


def header(suffix: str | None = None, *, hero: bool = False, tagline: str | None = None) -> None:
    """
    Page header: title on the left, status badge + theme control top-right —
    one horizontal row, the classic app-bar pattern.

    hero=True keeps the centred landing title; the controls then sit in their
    own right-aligned strip above it so the centring isn't pulled off-axis.

    Both controls used to live elsewhere (a fixed-position dot in the window
    corner, a picker pinned to the bottom of the sidebar); they need no CSS
    here, and the theme control stays reachable now that navigation is at the
    top and there is no sidebar.
    """
    bar = st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center")
    if hero:
        _status_theme(bar)
        render_title(hero=True, tagline=tagline)
    else:
        with bar.container(width="stretch"):
            render_title(suffix)
        _status_theme(bar)
    # Applies a theme change: writes the same localStorage key the native
    # picker uses, then reloads. After the reload the flag is gone, so no loop.
    if wanted := st.session_state.pop("_theme_wanted", None):
        apply_theme(wanted)


def render_title(suffix: str | None = None, *, hero: bool = False, tagline: str | None = None) -> None:
    """
    Page header: Reikun (例訓), linking back to home.

    hero=True renders the large, centred landing variant (search-first empty
    state); otherwise a compact header sits above the results.

    The English wordmark is a link back to home: the default page is served
    at "/" (st.navigation gives it url_path=""), and the reload drops session
    state — so `last_search` clears and the hero view returns. theme/level
    ride along in the URL so those widget preferences (bind="query-params")
    survive the trip; q/kanji are deliberately left behind.

    The 例訓 kanji carry format_kanji_text()'s interactive kanji_tip spans as
    *siblings* of the link, not children: the spans are focusable
    (tabindex="0") so the hover card is keyboard- and touch-reachable, and
    focusable content can't validly nest inside <a> — that mis-nesting was
    issue #1, with tooltip text bleeding into the visible title. Outside the
    anchor they stay valid, and a tap opens the card instead of navigating.

    The heading element is a div role="heading", not h1: Streamlit slugs
    heading ids from the element's text, and with the tooltip bodies inside
    an h1 the id came out as "reikun-例-訓-meanings-…" — the second half of
    issue #1. A non-h* element gets no auto slug; role/aria-level keep the
    heading semantics.
    """
    keep = {k: v for k in ("theme", "level") if isinstance(v := st.query_params.get(k), str)}
    href = "/" + (f"?{urlencode(keep)}" if keep else "")
    text = (f'<a class="title-home" href="{href}" target="_self" title="Back to search">Reikun</a>'
            f" ({format_kanji_text('例訓')})")
    if suffix:
        text += f" — {html.escape(suffix)}"
    tag = f"<p>{html.escape(tagline)}</p>" if tagline else ""
    cls = "hero" if hero else "compact"
    st.markdown(f'<div class="{cls}"><div class="title-heading" role="heading" aria-level="1">'
                f'{text}</div>{tag}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def data_status() -> tuple[bool, str]:
    """(ready, message) for the Qdrant collection; cached for a minute."""
    try:
        client = qdrant_client()
        if not client.collection_exists(COLLECTION):
            return False, "Collection missing — run scripts/ingest.py"
        count = client.count(COLLECTION).count
        return (count > 0), (f"{count:,} entries indexed" if count else "Collection empty — run scripts/ingest.py")
    except Exception as exc:  # connection refused, DNS, …
        return False, f"Qdrant unreachable: {type(exc).__name__}"


# ── Kanji rendering ──────────────────────────────────────────────────────────

def _meta_line(d: dict) -> str:
    parts = [f"{d['stroke_count']} strokes" if d.get("stroke_count") else None,
             f"Grade {d['grade']}" if d.get("grade") else None,
             f"JLPT N{d['jlpt_level']}" if d.get("jlpt_level") else None,
             f"Freq #{d['freq']}" if d.get("freq") else None]
    return " · ".join(p for p in parts if p)


@st.cache_data(show_spinner=False)
def kanji_tooltip(char: str) -> str:
    """Compact hover card (no SVG) for a kanji; '' if unknown."""
    d = lookup_kanji(char)
    if not d:
        return ""
    esc = html.escape
    # Keep every element inline: a block-level tag inside the hover <span>/<p>
    # makes the browser auto-close the paragraph, so the tooltip "leaks" out
    # and renders statically below the word instead of on hover.
    rows = [f'<span class="big">{esc(char)}</span>']
    if d.get("meanings"):
        rows.append(f"<b>Meanings</b> {esc(', '.join(d['meanings'][:6]))}<br>")
    if d.get("on_yomi"):
        rows.append(f"<b>On</b> {esc('、'.join(d['on_yomi'][:4]))}<br>")
    if d.get("kun_yomi"):
        rows.append(f"<b>Kun</b> {esc('、'.join(d['kun_yomi'][:4]))}<br>")
    if meta := _meta_line(d):
        rows.append(f'<span style="opacity:.7">{esc(meta)}</span>')
    return "".join(rows)


def format_kanji_text(text: str) -> str:
    """
    Escape `text` and wrap each known kanji in a hover-tooltip span (single line).

    tabindex="0" makes the card reachable without a mouse: keyboard users can
    tab to it and touch users get it on tap, both via :focus-within in the
    stylesheet. Hover alone would hide the readings from every phone.

    CAUTION: because each span is focusable (interactive), never nest the
    output of this function inside another interactive element (<a>,
    <button>, etc.) — interactive content can't validly nest inside
    interactive content, and browsers handle the violation inconsistently.
    See render_title()'s docstring for what that looked like in practice.
    """
    out = []
    for ch in text:
        if is_kanji(ch) and (tip := kanji_tooltip(ch)):
            out.append(f'<span class="kanji-tip" tabindex="0">{html.escape(ch)}'
                       f'<span class="kanji-tip-body">{tip}</span></span>')
        else:
            out.append(html.escape(ch))
    return "".join(out).replace("\n", " ")


def furigana(word: str, reading: str | None) -> str:
    """
    `word` as HTML with its reading as <ruby> furigana over the kanji part.

    Kana shared at the start/end of both strings (okurigana, honorific お…)
    stay outside the ruby so 食べる/たべる renders as 食[た]べる rather than
    食べる[たべる]. Kanji keep their hover tooltips.
    """
    if not reading or reading == word or not any(map(is_kanji, word)):
        return format_kanji_text(word)
    i = 0
    while i < min(len(word), len(reading)) and word[i] == reading[i] and not is_kanji(word[i]):
        i += 1
    j = 0
    while j < min(len(word), len(reading)) - i and word[-1 - j] == reading[-1 - j] and not is_kanji(word[-1 - j]):
        j += 1
    core_w, core_r = word[i:len(word) - j], reading[i:len(reading) - j]
    if not core_w or not core_r:
        return f"<ruby>{format_kanji_text(word)}<rt>{html.escape(reading)}</rt></ruby>"
    return (format_kanji_text(word[:i])
            + f"<ruby>{format_kanji_text(core_w)}<rt>{html.escape(core_r)}</rt></ruby>"
            + format_kanji_text(word[len(word) - j:]))


@st.cache_data(show_spinner=False)
def animated_stroke_svg(char: str) -> str | None:
    """
    KanjiVG SVG with per-stroke animation delays so strokes draw in order.

    `pathLength="100"` normalises every stroke to the same dash length, so the
    CSS dash-offset animation draws each stroke at a uniform speed regardless
    of its real length. Stroke numbers fade in alongside their stroke. These
    per-path `animation-delay` inline styles keep working unchanged under the
    .pa/.pb replay classes in style.css — an inline style always wins over a
    stylesheet rule for the same longhand property, so the delay isn't reset
    by the class's `animation:` shorthand.
    """
    svg = stroke_svg(char)
    if not svg:
        return None
    svg = _KVG_PATH.sub(
        lambda m: f'{m.group(0)} pathLength="100" style="animation-delay:{(int(m.group(1)) - 1) * _STROKE_STEP_S:.2f}s"', svg
    )
    n = iter(range(10_000))
    return _KVG_NUMBER.sub(lambda _: f'<text style="animation-delay:{next(n) * _STROKE_STEP_S:.2f}s" ', svg)


def _bump(key: str) -> None:
    st.session_state[key] = st.session_state.get(key, 0) + 1


@st.fragment
def _stroke_diagram(char: str) -> None:
    """Kanji glyph, a compact Replay control, and the stroke-order SVG.

    Glyph and Replay share one row *inside this fragment* (not a container
    created outside it and passed in) — st.fragment scopes reruns to
    whatever it renders itself, and bundling the static glyph here achieves
    "glyph left, Replay right" using nothing but st.container's default
    horizontal gap: no CSS, no key, no positioning rule at all. Passing a
    container reference across the fragment boundary was considered and
    rejected — untested pattern, and this app has already hit several subtle
    framework-version quirks (see Issues.md), so the simplest option that
    needs zero new assumptions wins.

    st.markdown, not st.html, for the SVG: st.html sanitises with DOMPurify's
    html-only profile, which strips <svg> entirely — the diagram would
    render empty. rehype-raw (used by st.markdown) keeps SVG.

    Browsers won't restart an animation whose name didn't change, so Replay
    bumps a session counter whose parity flips the wrapper between .pa/.pb —
    two identical keyframe names in style.css. The whole block lives in this
    fragment so Replay's rerun is scoped to just this block; a full rerun
    would close the kanji dialog (kanji_dialog consumes its session state on
    open).
    """
    head = st.container(horizontal=True, vertical_alignment="center")
    head.markdown(f'<p class="kanji-big">{html.escape(char)}</p>', unsafe_allow_html=True, width="content")
    if svg := animated_stroke_svg(char):
        key = f"_kvg_replay_{char}"
        cls = "pa" if st.session_state.get(key, 0) % 2 == 0 else "pb"
        head.button("Replay", icon=":material/replay:", key=f"{key}_btn", type="tertiary",
                    help="Replay the stroke-order animation", on_click=_bump, args=(key,))
        st.markdown(f'<div class="stroke-svg {cls}">{svg}</div>', unsafe_allow_html=True)


def render_kanji_card(char: str) -> None:
    """Full kanji details: stroke order, readings, meta, common words."""
    d = lookup_kanji(char)
    if not d:
        st.info(f"No KANJIDIC2 entry for “{char}”.")
        return

    left, right = st.columns([1, 2], gap="large")
    with left:
        _stroke_diagram(char)
    with right:
        st.markdown(f"**Meanings** — {', '.join(d.get('meanings') or ['—'])}")
        if d.get("on_yomi"):
            st.markdown(f"**On'yomi** — {'、'.join(d['on_yomi'])}")
        if d.get("kun_yomi"):
            st.markdown(f"**Kun'yomi** — {'、'.join(d['kun_yomi'])}")
        if meta := _meta_line(d):
            st.caption(meta)
        if words := d.get("common_words"):
            st.markdown("**Common words**")
            st.markdown("\n".join(
                f"- {html.escape(w.get('kanji_form') or w['reading'])} "
                f"({html.escape(w['reading'])}) — {html.escape((w.get('meanings') or [''])[0])}"
                for w in words[:8]
            ), unsafe_allow_html=True)


@st.dialog("Kanji", width="medium", on_dismiss="rerun")
def kanji_dialog(char: str) -> None:
    st.session_state.kanji_dialog = None  # consume so the dialog closes on the next rerun
    render_kanji_card(char)


def open_kanji_dialog(pills_key: str) -> None:
    """`on_change` callback for a kanji st.pills: stash the choice and reset the pills."""
    if char := st.session_state.get(pills_key):
        st.session_state.kanji_dialog = char
        st.session_state[pills_key] = None
        log_kanji_lookup(char, source="dialog")


def show_pending_dialog() -> None:
    if char := st.session_state.get("kanji_dialog"):
        kanji_dialog(char)


def footer() -> None:
    """Project copyright first, then the third-party data attributions the
    CC BY-SA licences require — the latter smaller and dimmer (.footer-data),
    since they are a legal notice rather than something to read."""
    st.divider()
    st.markdown(
        '<p class="footer-license">Reikun © 2026 Aniket Satbhai · '
        '<a href="https://github.com/AnkS4/Reikun/blob/main/LICENSE">Apache-2.0</a></p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="footer-data">Data: '
        '<a href="https://www.edrdg.org/edrdg/licence.html">JMdict &amp; KANJIDIC2 © EDRDG</a> '
        '(<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>) · '
        '<a href="https://tatoeba.org">Tatoeba</a> '
        '(<a href="https://creativecommons.org/licenses/by/2.0/fr/">CC BY 2.0 FR</a>) · '
        '<a href="https://kanjivg.tagaini.net/">KanjiVG © Ulrich Apel</a> '
        '(<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>)</p>',
        unsafe_allow_html=True,
    )
