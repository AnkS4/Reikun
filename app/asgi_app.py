"""
Combined ASGI app: the Streamlit UI plus the FastAPI layer mounted at /api,
in a single process. This is what Docker runs (via scripts/startup.py).

    streamlit run app/asgi_app.py        # same as the UI entrypoint + /api
    uvicorn app.asgi_app:app --port 8501 # equivalent

Routes: / → Streamlit UI · /api/health · /api/search · /api/kanji/{char}
· /api/explain · /api/feedback · /api/docs (Swagger).
"""

import sys
from pathlib import Path

import streamlit as st
from starlette.routing import Mount

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api import app as api  # noqa: E402

app = st.App(
    str(Path(__file__).resolve().parent / "streamlit_app.py"),
    routes=[Mount("/api", api)],
)

if __name__ == "__main__":
    app.run()
