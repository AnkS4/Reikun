"""
Reikun (例訓) — Japanese Assistant.

Entry point for Streamlit multipage navigation:

    streamlit run app/streamlit_app.py

Pages live in app/ui/ (search.py, dashboard.py).
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

st.navigation(
    [
        st.Page("ui/search.py", title="Search", icon=":material/search:", default=True),
        st.Page("ui/dashboard.py", title="Dashboard", icon=":material/monitoring:"),
    ]
).run()
