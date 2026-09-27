"""
Reikun (例訓) — Semantic Japanese Dictionary.

Entry point for Streamlit multipage navigation:

    streamlit run app/streamlit_app.py

Pages live in app/ui/ (search.py, dashboard.py).
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval import warm_headword_index  # noqa: E402

# Warm the sentence-lookup pieces in the background — the headword index
# (an mmap'd ~26 MB marisa trie shipped in the image, or one ~44-request
# Qdrant scroll rebuild when absent) plus the Sudachi dictionary load — so
# the first user searching a Japanese sentence doesn't pay it.
warm_headword_index()

st.navigation(
    [
        st.Page("ui/search.py", title="Search", icon=":material/search:", default=True),
        st.Page("ui/dashboard.py", title="Dashboard", icon=":material/monitoring:"),
    ],
    # Top navigation: with only two pages the sidebar was pure overhead — its
    # only non-nav control (the theme picker) now lives in each page's top bar.
    position="top",
).run()
