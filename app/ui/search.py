"""Search page: word / sentence retrieval, kanji details, on-demand grammar explanations."""

import html
import time

import streamlit as st

from app.config import COHERE_MODEL
from app.grammar_explain import JLPT_LEVELS, explain_grammar_stream
from app.kanji_lookup import is_kanji, kanji_in, random_kanji
from app.query_rewrite import is_japanese
from app.retrieval import entry_forms, headword_index, search
from app.ui.common import (
    APP_ICON,
    APP_NAME,
    data_status,
    footer,
    format_kanji_text,
    furigana,
    header,
    inject_css,
    open_kanji_dialog,
    render_kanji_card,
    show_pending_dialog,
)
from scripts.feedback_log import log_explanation, log_feedback, log_kanji_lookup, log_search

st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="centered")
inject_css()
st.session_state.setdefault("explanations", {})
st.session_state.setdefault("last_search", None)

TAGLINE = ("Type a word or question in English or Japanese — get kanji details, "
           "real example sentences and level-aware grammar help.")
EXAMPLES = ("office", "歩く", "魚", "How do you say air conditioner in Japanese")
DEFAULT_LEVEL = "N5"
# Retrieval is ~25 ms, so a page of ten costs the same as five;
# "Show more" refetches +PAGE_RESULTS.
DEFAULT_RESULTS = 10
PAGE_RESULTS = 10
MAX_RESULTS = 50


def _pick_example() -> None:
    """Example chip → fill the (URL-bound) search box; the rerun triggers the search."""
    if ex := st.session_state.get("example"):
        st.session_state.q = ex
        st.session_state.example = None


def _random_kanji() -> None:
    """Random button → fill the box; the rerun triggers the search."""
    # Restrict to kanji that are themselves JMdict headwords — a lone kanji
    # often isn't a standalone word, so an unrestricted pick showed the card
    # above an empty result list about a quarter of the time.
    try:
        st.session_state.q = random_kanji(within=headword_index())
    except Exception:
        st.session_state.q = random_kanji()  # index unreachable → unrestricted pick


# ?kanji=猫 deep link opens the kanji dialog once, then drops the param.
if (deep := st.query_params.get("kanji")) is not None:
    del st.query_params["kanji"]
    if is_kanji(deep):
        st.session_state.kanji_dialog = deep
        log_kanji_lookup(deep, source="dialog")

ready, _ = data_status()
has_results = st.session_state.last_search is not None
header(hero=not has_results, tagline=TAGLINE if not has_results else None)


# ── Query row ────────────────────────────────────────────────────────────────
# `q` and `level` are bound to URL query params: ?q=cat&level=N3 is shareable,
# the browser back button walks through previous searches, and the level
# survives reloads until the user changes it.
#
# key="query_row" + the matching .st-key-query_row rule in style.css pins
# this row to the top of the viewport while scrolling a long result list —
# so changing the JLPT level (used by every "Explain grammar" button below)
# never requires scrolling back up. This is the one deliberate exception to
# "no custom positioning" in this page: one rule, on the same documented
# st-key-* hook the rest of the app already relies on, nothing fancier.

row = st.container(horizontal=True, vertical_alignment="center", gap="xsmall", key="query_row")
# Input + submit live in a gapless inner row so the button sits attached to
# the box like a segmented control; the outer gap keeps the other buttons
# compact but separate.
pair = row.container(horizontal=True, vertical_alignment="center", gap=0)
query = pair.text_input("Search", key="q", bind="query-params", type="search", label_visibility="collapsed",
                        placeholder="Search", icon="")
go = pair.button("", type="primary", icon=":material/search:", key="go", help="Search")
row.button("", icon=":material/shuffle:", help="Random kanji", on_click=_random_kanji)
# JLPT level lives next to the search box as a compact popover — it only
# matters when the user opens "Explain grammar", which is on this same page.
level = str(st.query_params.get("level") or st.session_state.get("level") or DEFAULT_LEVEL)
with row.popover(level, icon=":material/school:", help="JLPT level for grammar explanations"):
    st.segmented_control(
        "JLPT level", JLPT_LEVELS, key="level", bind="query-params", default=DEFAULT_LEVEL,
        help="Grammar explanations are calibrated to this level — saved in the URL until you change it",
    )

# A new query (or a cleared box) resets pagination to the first page.
last = st.session_state.last_search
q = (query or "").strip()
if not q or (last and last["query"] != q):
    st.session_state.want_results = DEFAULT_RESULTS
num_results = st.session_state.get("want_results", DEFAULT_RESULTS)


# ── Run the search when the query or the requested count changes ─────────────

if q and (go or last is None or last["query"] != q or last["num_results"] != num_results):
    if not ready:
        st.error("The knowledge base is not ready yet — hover the status badge above for details.")
    else:
        with st.spinner("Searching…"):
            try:
                resp = search(q, num_results)
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                resp = None
        if resp:
            top = resp.results[0] if resp.results else None
            search_id = log_search(
                q, rewritten_query=resp.rewrite.query, rewrite_method=resp.rewrite.method,
                mode=resp.mode, num_results=num_results, result_count=len(resp.results),
                top_result=(top or {}).get("kanji_form") or (top or {}).get("reading"), latency_ms=resp.latency_ms,
            )
            kanji = q if is_kanji(q) else None
            if kanji:
                log_kanji_lookup(kanji, source="search")
            st.session_state.last_search = {"id": search_id, "query": q, "resp": resp, "kanji": kanji,
                                            "num_results": num_results}
            if not has_results:
                st.rerun()  # switch from the hero layout to the compact header
# Clearing the box (the ✕ or deleting the text) leaves the results in place —
# "home" is the title link, not an empty box.


# ── Grammar explanation (fragment: reruns only itself) ───────────────────────

def _feedback_cb(widget_key: str, kind: str, ref_id: int, query: str) -> None:
    value = st.session_state.get(widget_key)
    if value is not None:
        log_feedback(kind, ref_id, 1 if value == 1 else -1, query)


@st.fragment
def example_row(ex: dict, key: str) -> None:
    """
    One example sentence: the sentence pair on the left, its "Explain grammar"
    button on the right, and the streamed explanation below when requested.
    """
    sentence, english = ex["japanese"], ex["english"]
    expl = st.session_state.explanations.get(key)

    row = st.container(horizontal=True, vertical_alignment="center")
    row.markdown(f'<p class="sentence">{format_kanji_text(sentence)}</p>'
                 f'<p class="en">{html.escape(english)}</p>', unsafe_allow_html=True, width="stretch")
    label = f"Explain grammar · {level}" if expl is None else f"Explain again · {level}"
    if (expl is None or expl["level"] != level) and row.button(
            label, key=f"go_{key}", icon=":material/school:",
            type="secondary" if expl is None else "tertiary"):
        t0 = time.perf_counter()
        chunks: list[str] = []

        def _gen():
            for c in explain_grammar_stream(sentence, english, level):
                chunks.append(c)
                yield c

        try:
            st.write_stream(_gen())
            text, ok = "".join(chunks).strip(), True
        except Exception as exc:
            text, ok = f"Explanation unavailable: {exc}", False
        expl_id = log_explanation(sentence, level, model=COHERE_MODEL,
                                  latency_ms=int((time.perf_counter() - t0) * 1000), ok=ok)
        st.session_state.explanations[key] = {"level": level, "text": text, "ok": ok, "id": expl_id}
        st.rerun(scope="fragment")  # swap streamed text for the persistent view with feedback

    if expl:
        (st.markdown if expl["ok"] else st.warning)(expl["text"])
        meta = st.container(horizontal=True, vertical_alignment="center")
        meta.caption(f"AI-generated for {expl['level']} · {COHERE_MODEL}")
        if expl["ok"]:
            meta.feedback("thumbs", key=f"fb_expl_{expl['id']}", on_change=_feedback_cb,
                          args=(f"fb_expl_{expl['id']}", "explanation", expl["id"], sentence))


# ── Results ──────────────────────────────────────────────────────────────────

def render_result(r: dict, idx: int) -> None:
    head = r.get("kanji_form") or r["reading"]
    examples = r.get("example_sentences") or []
    with st.container(border=True):
        top = st.container(horizontal=True, vertical_alignment="center")
        top.markdown(f'<p class="headword">{furigana(head, r["reading"])}</p>', unsafe_allow_html=True, width="content")
        if r.get("is_common"):
            top.badge("common", color="green")
        if chars := kanji_in(head + "".join(ex["japanese"] for ex in examples[:3])):
            key = f"pills_{idx}_{r['id']}"
            top.pills("Kanji details", chars, key=key, on_change=open_kanji_dialog, args=(key,),
                      label_visibility="collapsed", help="Click a kanji for stroke order and details")
        st.markdown(f'<p class="meanings">{html.escape("; ".join(r["meanings"][:6]))}</p>', unsafe_allow_html=True)

        for j, ex in enumerate(examples[:3]):
            example_row(ex, key=f"{r['id']}_{j}")
        if not examples:
            st.caption("No example sentences for this entry.")


if last := st.session_state.last_search:
    resp = last["resp"]
    if last["kanji"]:
        with st.container(border=True):
            render_kanji_card(last["kanji"])

    head = st.container(horizontal=True, vertical_alignment="center")
    route = f"·{resp.meta['route']}" if resp.meta.get("route") else ""
    head.markdown(f"**{len(resp.results)} entries** · {resp.mode}{route} · {resp.latency_ms} ms")
    if resp.meta.get("embed_ms") is not None:
        head.caption(f"embed {resp.meta['embed_ms']} ms · retrieve {resp.meta['retrieve_ms']} ms")
    head.feedback("thumbs", key=f"fb_search_{last['id']}", on_change=_feedback_cb,
                  args=(f"fb_search_{last['id']}", "search", last["id"], last["query"]))
    if resp.rewrite.changed:
        st.caption(f"Searched for **{resp.rewrite.query}** (rewritten from “{resp.rewrite.original}”, {resp.rewrite.method})")

    searched = resp.rewrite.query
    exact = any(searched in entry_forms(r) for r in resp.results)
    if resp.results and is_japanese(searched) and not exact:
        hint = " Tip: enter a single kanji at a time for its full details." if sum(map(is_kanji, searched)) > 1 else ""
        st.info(f"“{searched}” is not a JMdict entry — showing the closest matches instead.{hint}", icon=":material/info:")
    if segments := resp.meta.get("segments"):
        # Compound Japanese query decomposed into dictionary headwords
        # ("静かな場所" → 静か + 場所) — show each part's meaning.
        parts = " + ".join(
            f"**{html.escape(s['text'])}** ({html.escape(s['reading'])}) — {html.escape('; '.join(s['meanings'][:2]))}"
            for s in segments
        )
        st.markdown(f"Parsed as: {parts}", unsafe_allow_html=True)

    if not resp.results:
        st.warning("Nothing found. Try a different English or Japanese word.")
    for i, r in enumerate(resp.results):
        render_result(r, i)
    if len(resp.results) >= num_results and num_results < MAX_RESULTS:
        def _show_more() -> None:
            st.session_state.want_results = min(num_results + PAGE_RESULTS, MAX_RESULTS)
        st.button(f"Show {PAGE_RESULTS} more", icon=":material/expand_more:", on_click=_show_more,
                  help=f"Refetches the search with up to {MAX_RESULTS} results")
else:
    st.pills("Try an example", EXAMPLES, key="example", on_change=_pick_example, label_visibility="collapsed")

show_pending_dialog()
footer()
