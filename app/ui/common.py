"""Shared UI helpers: CSS, cached lookups, kanji rendering, footer."""

import html

import streamlit as st

from app.config import COLLECTION, qdrant_client
from app.kanji_lookup import is_kanji, lookup_kanji, stroke_svg
from monitoring.feedback_log import log_kanji_lookup

APP_TITLE = "Reikun (例訓)"
APP_NAME = "Reikun (例訓) — Japanese Assistant"
APP_ICON = ":material/translate:"

_CSS = """
<style>
.jp { font-family: "Noto Sans JP", "Hiragino Sans", "Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", sans-serif; }
.headword { font-size: 2.1rem; font-weight: 600; line-height: 1.25; margin: 0 0 .15rem 0; }
.headword .reading { font-size: 1rem; font-weight: 400; opacity: .65; margin-left: .7rem; }
.meanings { margin: 0 0 .75rem 0; }
.sentence { font-size: 1.2rem; line-height: 1.7; margin: 0; }
.en { opacity: .7; margin: 0 0 .7rem 0; }
.kanji-char { cursor: help; border-bottom: 1px dotted currentColor; }
.kanji-tip { position: relative; }
.kanji-tip .kanji-tip-body {
  display: none; position: absolute; top: 1.6em; left: 0; z-index: 1000; width: 280px;
  background: var(--background-color, #fff); color: var(--text-color, #111);
  border: 1px solid rgba(128,128,128,.35); border-radius: .5rem; padding: .6rem .8rem;
  box-shadow: 0 8px 24px rgba(0,0,0,.14); font-size: .85rem; font-weight: 400; line-height: 1.5;
  text-align: left; white-space: normal;
}
.kanji-tip:hover .kanji-tip-body { display: block; }
.kanji-tip-body .big { display: block; font-size: 1.9rem; font-weight: 600; line-height: 1.1; margin-bottom: .2rem; }
.kanji-big { font-size: 4.5rem; line-height: 1; font-weight: 500; margin: 0; }
.stroke-svg svg { width: 100%; height: auto; max-width: 160px; }
.footer { opacity: .6; font-size: .8rem; line-height: 1.6; }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def render_title(suffix: str | None = None) -> None:
    """Page header: Reikun (例訓) with the same hover tooltips as inline kanji."""
    text = f"Reikun ({format_kanji_text('例訓')})"
    if suffix:
        text += f" — {html.escape(suffix)}"
    st.markdown(f'<h1 class="jp">{text}</h1>', unsafe_allow_html=True)


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
    rows = [f'<span class="big jp">{esc(char)}</span>']
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
    """Escape `text` and wrap each known kanji in a hover-tooltip span (single line)."""
    out = []
    for ch in text:
        if is_kanji(ch) and (tip := kanji_tooltip(ch)):
            out.append(f'<span class="kanji-char kanji-tip">{html.escape(ch)}<span class="kanji-tip-body">{tip}</span></span>')
        else:
            out.append(html.escape(ch))
    return "".join(out).replace("\n", " ")


def render_kanji_card(char: str) -> None:
    """Full kanji details: stroke order, readings, meta, common words."""
    d = lookup_kanji(char)
    if not d:
        st.info(f"No KANJIDIC2 entry for “{char}”.")
        return

    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown(f'<p class="kanji-big jp">{html.escape(char)}</p>', unsafe_allow_html=True)
        if svg := stroke_svg(char):
            st.markdown(f'<div class="stroke-svg">{svg}</div>', unsafe_allow_html=True)
            st.caption("Stroke order (KanjiVG)")
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
                f"- <span class='jp'>{html.escape(w.get('kanji_form') or w['reading'])}</span> "
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
    st.divider()
    st.markdown(
        '<div class="footer">Dictionary data from <b>JMdict</b> and <b>KANJIDIC2</b>, property of the '
        'Electronic Dictionary Research and Development Group, used under '
        '<a href="https://www.edrdg.org/edrdg/licence.html">CC BY-SA 4.0</a>. '
        'Example sentences from the <a href="https://tatoeba.org">Tatoeba Corpus</a> (CC BY 2.0 FR). '
        'Stroke-order diagrams from <a href="https://kanjivg.tagaini.net/">KanjiVG</a> (CC BY-SA 3.0). '
        'Grammar explanations are AI-generated (Cohere) and may contain mistakes.</div>',
        unsafe_allow_html=True,
    )
