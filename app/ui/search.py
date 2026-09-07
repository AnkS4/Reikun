"""Search page: word / sentence retrieval, kanji details, on-demand grammar explanations."""

import html
import time

import streamlit as st

from app.config import COHERE_MODEL, RERANKER
from app.grammar_explain import JLPT_LEVELS, explain_grammar
from app.kanji_lookup import is_kanji, kanji_in
from app.query_rewrite import is_japanese
from app.retrieval import MODES, search
from app.ui.common import (
    APP_ICON,
    APP_NAME,
    data_status,
    footer,
    format_kanji_text,
    inject_css,
    open_kanji_dialog,
    render_kanji_card,
    render_title,
    show_pending_dialog,
)
from monitoring.feedback_log import log_explanation, log_feedback, log_kanji_lookup, log_search

st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="centered")
inject_css()
st.session_state.setdefault("explanations", {})
st.session_state.setdefault("last_search", None)


# ── Sidebar: settings + status ───────────────────────────────────────────────

with st.sidebar:
    st.subheader("Search settings")
    mode = st.segmented_control(
        "Retrieval", MODES, default="hybrid", key="mode",
        help=(
            "hybrid — dense embeddings + BM25 keyword + exact match, fused with RRF "
            "(best in eval)\n\n"
            "vector — semantic similarity only (dense embeddings)\n\n"
            "text — BM25 keyword/lexical matching only"
        ),
    )
    num_results = st.slider("Results", 1, 15, 5, key="num_results")
    use_rerank = st.toggle("Re-rank with cross-encoder", value=RERANKER != "none", key="use_rerank",
                           disabled=RERANKER == "none")
    rewrite = st.toggle("Rewrite natural-language queries", value=True, key="rewrite",
                        help="Turns questions like “how do you say X” into a dictionary gloss before searching")
    default_level = st.segmented_control("Your JLPT level", JLPT_LEVELS, default="N5", key="default_level",
                                         help="Default level for grammar explanations") or "N5"

    st.divider()
    ready, status = data_status()
    st.caption(f"{'🟢' if ready else '🔴'} {status}")
    if st.button("Refresh status", type="tertiary", icon=":material/refresh:"):
        data_status.clear()
        st.rerun()


# ── Header + query form ──────────────────────────────────────────────────────

render_title()
st.caption("Type an English or Japanese word — get real example sentences, kanji details and level-aware grammar help.")

with st.form("search", border=False):
    col_q, col_b = st.columns([6, 1], vertical_alignment="bottom")
    query = col_q.text_input("Search", placeholder="sky · to forget · 食べる · 例 · how do you say hospital",
                             type="search", label_visibility="collapsed")
    submitted = col_b.form_submit_button("Search", type="primary", icon=":material/search:", width="stretch")

if submitted and query.strip():
    if not ready:
        st.error("The knowledge base is not ready yet — see the sidebar status.")
    else:
        with st.spinner("Searching…"):
            try:
                resp = search(query, num_results, mode or "hybrid", use_rerank=use_rerank,
                              rewrite_mode=None if rewrite else "off")
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                resp = None
        if resp:
            top = resp.results[0] if resp.results else None
            search_id = log_search(
                query.strip(), rewritten_query=resp.rewrite.query, rewrite_method=resp.rewrite.method,
                mode=resp.mode, reranked=resp.reranked, num_results=num_results, result_count=len(resp.results),
                top_result=(top or {}).get("kanji_form") or (top or {}).get("reading"), latency_ms=resp.latency_ms,
            )
            kanji = query.strip() if is_kanji(query.strip()) else None
            if kanji:
                log_kanji_lookup(kanji, source="search")
            st.session_state.last_search = {"id": search_id, "query": query.strip(), "resp": resp, "kanji": kanji}


# ── Grammar explanation (fragment: reruns only itself) ───────────────────────

@st.fragment
def explain_fragment(sentence: str, english: str, key: str) -> None:
    ctl = st.container(horizontal=True, vertical_alignment="bottom")
    level = ctl.segmented_control("JLPT level", JLPT_LEVELS, default=st.session_state.default_level,
                                  key=f"lvl_{key}", label_visibility="collapsed") or st.session_state.default_level
    if ctl.button("Explain", key=f"go_{key}", icon=":material/school:", type="primary"):
        t0 = time.perf_counter()
        with st.spinner("Asking the teacher…"):
            try:
                text, ok = explain_grammar(sentence, english, level), True
            except Exception as exc:
                text, ok = f"Explanation unavailable: {exc}", False
        expl_id = log_explanation(sentence, level, model=COHERE_MODEL,
                                  latency_ms=int((time.perf_counter() - t0) * 1000), ok=ok)
        st.session_state.explanations[key] = {"level": level, "text": text, "ok": ok, "id": expl_id}

    if expl := st.session_state.explanations.get(key):
        (st.markdown if expl["ok"] else st.warning)(expl["text"])
        row = st.container(horizontal=True, vertical_alignment="center")
        row.caption(f"AI-generated for {expl['level']} · {COHERE_MODEL}")
        if expl["ok"]:
            row.feedback("thumbs", key=f"fb_expl_{expl['id']}", on_change=_feedback_cb,
                         args=(f"fb_expl_{expl['id']}", "explanation", expl["id"], sentence))


def _feedback_cb(widget_key: str, kind: str, ref_id: int, query: str) -> None:
    value = st.session_state.get(widget_key)
    if value is not None:
        log_feedback(kind, ref_id, 1 if value == 1 else -1, query)


# ── Results ──────────────────────────────────────────────────────────────────

def render_result(r: dict, idx: int) -> None:
    head = r.get("kanji_form") or r["reading"]
    with st.container(border=True):
        reading = f'<span class="reading">{html.escape(r["reading"])}</span>' if r.get("kanji_form") else ""
        st.markdown(f'<p class="headword jp">{format_kanji_text(head)}{reading}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="meanings">{html.escape("; ".join(r["meanings"][:6]))}</p>', unsafe_allow_html=True)

        meta = st.container(horizontal=True, vertical_alignment="center")
        if r.get("is_common"):
            meta.badge("common", color="green")
        meta.caption(f"score {r['score']:.3f} · JMdict #{r['id']}")

        examples = r.get("example_sentences") or []
        for j, ex in enumerate(examples[:3]):
            st.markdown(f'<p class="sentence jp">{format_kanji_text(ex["japanese"])}</p>'
                        f'<p class="en">{html.escape(ex["english"])}</p>', unsafe_allow_html=True)
            with st.expander("Explain grammar", icon=":material/school:"):
                explain_fragment(ex["japanese"], ex["english"], key=f"{r['id']}_{j}")
        if not examples:
            st.caption("No example sentences for this entry.")

        if chars := kanji_in(head + "".join(ex["japanese"] for ex in examples[:3])):
            key = f"pills_{idx}_{r['id']}"
            st.pills("Kanji details", chars, key=key, on_change=open_kanji_dialog, args=(key,),
                     label_visibility="collapsed", help="Click a kanji for stroke order and details")


if last := st.session_state.last_search:
    resp = last["resp"]
    if last["kanji"]:
        with st.container(border=True):
            render_kanji_card(last["kanji"])

    head = st.container(horizontal=True, vertical_alignment="center")
    head.markdown(f"**{len(resp.results)} entries** · {resp.mode}{' + rerank' if resp.reranked else ''} · {resp.latency_ms} ms")
    head.feedback("thumbs", key=f"fb_search_{last['id']}", on_change=_feedback_cb,
                  args=(f"fb_search_{last['id']}", "search", last["id"], last["query"]))
    if resp.rewrite.changed:
        st.caption(f"Searched for **{resp.rewrite.query}** (rewritten from “{resp.rewrite.original}”, {resp.rewrite.method})")

    searched = resp.rewrite.query
    exact = any((r.get("kanji_form") or r.get("reading")) == searched for r in resp.results)
    if resp.results and is_japanese(searched) and not exact:
        hint = " Tip: enter a single kanji at a time for its full details." if sum(map(is_kanji, searched)) > 1 else ""
        st.info(f"“{searched}” is not a JMdict entry — showing the closest matches instead.{hint}", icon=":material/info:")

    if not resp.results:
        st.warning("Nothing found. Try a different English or Japanese word.")
    for i, r in enumerate(resp.results):
        render_result(r, i)
    show_pending_dialog()
else:
    with st.container(border=True):
        st.markdown(
            "**How to use**\n\n"
            "- **Search** an English word (*sky*, *to forget*), a Japanese word (*食べる*), or a question "
            "(*how do you say hospital*).\n"
            "- **Hover** any kanji in a result for readings; **click** a kanji chip for stroke order and common words.\n"
            "- **Explain grammar** on any example sentence for a JLPT-level-calibrated breakdown.\n"
            "- Rate results with 👍 / 👎 — feedback feeds the Dashboard page."
        )

footer()
