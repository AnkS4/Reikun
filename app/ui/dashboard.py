"""Monitoring dashboard: usage, feedback and quality signals from the SQLite log."""

import altair as alt
import pandas as pd
import streamlit as st

from app.config import MONITORING_DB
from app.ui.common import APP_ICON, APP_TITLE, footer, inject_css, render_title
from monitoring.feedback_log import load_table

st.set_page_config(page_title=f"{APP_TITLE} — Dashboard", page_icon=APP_ICON, layout="wide")
inject_css()

render_title("Dashboard")
st.caption(f"Live usage and feedback metrics · source: `{MONITORING_DB}`")


@st.cache_data(ttl=15, show_spinner=False)
def tables() -> dict[str, pd.DataFrame]:
    return {t: load_table(t) for t in ("searches", "feedback", "kanji_lookups", "explanations")}


if st.button("Refresh", icon=":material/refresh:", type="tertiary"):
    tables.clear()
data = tables()
searches, feedback, kanji, expl = data["searches"], data["feedback"], data["kanji_lookups"], data["explanations"]

if searches.empty and feedback.empty and kanji.empty and expl.empty:
    st.info("No activity logged yet — run a few searches on the Search page and come back.")
    footer()
    st.stop()


def bar(df: pd.DataFrame, x: str, y: str, *, x_title: str, y_title: str, sort_desc: bool = True) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(x, title=x_title),
            y=alt.Y(y, title=y_title, sort="-x" if sort_desc else None),
            tooltip=list(df.columns),
        )
        .properties(height=280)
    )


def up_rate(df: pd.DataFrame) -> float | None:
    return None if df.empty else float((df["rating"] > 0).mean())


# ── KPI row ──────────────────────────────────────────────────────────────────
search_fb = feedback[feedback["kind"] == "search"] if not feedback.empty else feedback
expl_fb = feedback[feedback["kind"] == "explanation"] if not feedback.empty else feedback
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Searches", f"{len(searches):,}", border=True)
k2.metric("Median latency", f"{int(searches['latency_ms'].median()) if not searches.empty else 0} ms", border=True)
k3.metric("Search 👍 rate", f"{up_rate(search_fb):.0%}" if up_rate(search_fb) is not None else "—",
          delta=f"{len(search_fb)} votes", delta_arrow="off", border=True)
k4.metric("Explanations", f"{len(expl):,}",
          delta=f"{up_rate(expl_fb):.0%} 👍" if up_rate(expl_fb) is not None else "no votes", delta_arrow="off", border=True)
k5.metric("Kanji lookups", f"{len(kanji):,}", border=True)

st.divider()

# ── Row 1: volume + top queries ──────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    st.subheader("1 · Query volume")
    if searches.empty:
        st.caption("No searches yet.")
    else:
        vol = searches.assign(hour=searches["ts"].dt.floor("h")).groupby("hour").size().reset_index(name="searches")
        st.altair_chart(
            alt.Chart(vol).mark_area(line=True, opacity=0.35, interpolate="monotone")
            .encode(x=alt.X("hour:T", title="Time (UTC, hourly)"), y=alt.Y("searches:Q", title="Searches"),
                    tooltip=["hour:T", "searches:Q"]).properties(height=280),
            width="stretch",
        )
with c2:
    st.subheader("2 · Top searched words")
    if searches.empty:
        st.caption("No searches yet.")
    else:
        top = searches["rewritten_query"].fillna(searches["query"]).str.lower().value_counts().head(15)
        st.altair_chart(bar(top.rename_axis("query").reset_index(name="count"), "count:Q", "query:N",
                            x_title="Searches", y_title=None), width="stretch")

# ── Row 2: feedback + kanji ──────────────────────────────────────────────────
c3, c4 = st.columns(2)
with c3:
    st.subheader("3 · Thumbs-up rate")
    if feedback.empty:
        st.caption("No feedback yet — use 👍 / 👎 on the Search page.")
    else:
        fb = feedback.assign(vote=feedback["rating"].map({1: "👍 up", -1: "👎 down"})).groupby(["kind", "vote"]).size().reset_index(name="count")
        st.altair_chart(
            alt.Chart(fb).mark_bar(cornerRadiusEnd=3)
            .encode(x=alt.X("count:Q", title="Votes", stack="normalize", axis=alt.Axis(format="%")),
                    y=alt.Y("kind:N", title=None),
                    color=alt.Color("vote:N", title=None, scale=alt.Scale(domain=["👍 up", "👎 down"], range=["#3C9D6B", "#B4432F"])),
                    tooltip=["kind", "vote", "count"]).properties(height=280),
            width="stretch",
        )
with c4:
    st.subheader("4 · Kanji lookup frequency")
    if kanji.empty:
        st.caption("No kanji lookups yet.")
    else:
        top_k = kanji["kanji"].value_counts().head(15).rename_axis("kanji").reset_index(name="count")
        st.altair_chart(bar(top_k, "count:Q", "kanji:N", x_title="Lookups", y_title=None), width="stretch")

# ── Row 3: JLPT levels + retrieval settings + latency ────────────────────────
c5, c6, c7 = st.columns(3)
with c5:
    st.subheader("5 · JLPT level of explanation requests")
    if expl.empty:
        st.caption("No explanations requested yet.")
    else:
        lv = expl["jlpt_level"].value_counts().reindex(["N5", "N4", "N3", "N2", "N1"], fill_value=0).rename_axis("level").reset_index(name="count")
        st.altair_chart(
            alt.Chart(lv).mark_bar(cornerRadiusEnd=3)
            .encode(x=alt.X("level:N", sort=["N5", "N4", "N3", "N2", "N1"], title="JLPT level"),
                    y=alt.Y("count:Q", title="Requests"), tooltip=["level", "count"]).properties(height=280),
            width="stretch",
        )
with c6:
    st.subheader("6 · Retrieval settings used")
    if searches.empty:
        st.caption("No searches yet.")
    else:
        cfg = searches.assign(setting=searches["mode"] + searches["reranked"].map({1: " + rerank", 0: ""})
                              + searches["rewrite_method"].map(lambda m: f" · {m}" if m and m != "none" else ""))
        cfg = cfg["setting"].value_counts().rename_axis("setting").reset_index(name="count")
        st.altair_chart(bar(cfg, "count:Q", "setting:N", x_title="Searches", y_title=None), width="stretch")
with c7:
    st.subheader("7 · Search latency")
    if searches.empty:
        st.caption("No searches yet.")
    else:
        st.altair_chart(
            alt.Chart(searches).mark_bar(cornerRadiusEnd=3)
            .encode(x=alt.X("latency_ms:Q", bin=alt.Bin(maxbins=20), title="Latency (ms)"),
                    y=alt.Y("count():Q", title="Searches"), tooltip=["count()"]).properties(height=280),
            width="stretch",
        )

with st.expander("Recent searches"):
    if searches.empty:
        st.caption("No searches yet.")
    else:
        st.dataframe(
            searches.sort_values("id", ascending=False).head(50)
            [["ts", "query", "rewritten_query", "rewrite_method", "mode", "reranked", "result_count", "top_result", "latency_ms"]],
            width="stretch", hide_index=True,
        )

footer()
