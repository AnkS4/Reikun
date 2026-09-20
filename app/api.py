"""
Thin HTTP API over the retrieval, kanji-lookup and grammar-explanation modules.

The Streamlit UI imports those modules directly; this exposes the same code
path over HTTP so eval tooling, scripts or an alternative frontend can use it.

    uvicorn app.api:app --host 0.0.0.0 --port 8100 --reload   # standalone
    # or mounted under /api in the UI process:  streamlit run app/asgi_app.py

Interactive docs at /docs (Swagger) and /redoc.
"""

import json
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import COHERE_MODEL, COLLECTION, qdrant_client  # noqa: E402
from app.grammar_explain import JLPT_LEVELS, explain_grammar, explain_grammar_stream  # noqa: E402
from app.kanji_lookup import is_kanji, lookup_kanji, stroke_svg  # noqa: E402
from app.retrieval import MODES, search  # noqa: E402
from scripts.feedback_log import log_explanation, log_feedback, log_kanji_lookup, log_search  # noqa: E402

# Standalone `uvicorn app.api:app` doesn't configure the root logger, so do it
# here unless something else already did (the Streamlit entrypoint, pytest…).
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

Mode = Literal["auto", "hybrid", "vector", "text"]
Level = Literal["N5", "N4", "N3", "N2", "N1"]
assert set(Mode.__args__) == set(MODES) and set(Level.__args__) == set(JLPT_LEVELS)

app = FastAPI(
    title="Reikun API",
    version="0.1.0",
    description="Japanese dictionary search (hybrid dense + BM25), kanji details and JLPT-calibrated grammar explanations.",
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    sentence: str = Field(..., min_length=1, description="Japanese example sentence")
    english: str = Field("", description="English translation (improves the explanation)")
    level: Level = "N5"


class FeedbackRequest(BaseModel):
    kind: Literal["search", "explanation"]
    ref_id: int = Field(..., description="`search_id` from /search or `explanation_id` from /explain")
    rating: Literal[1, -1]
    query: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Qdrant reachability and index size. 503 when the collection is missing or empty."""
    try:
        client = qdrant_client()
        count = client.count(COLLECTION).count if client.collection_exists(COLLECTION) else 0
    except Exception as exc:  # connection refused, DNS, …
        raise HTTPException(503, f"Qdrant unreachable: {type(exc).__name__}") from exc
    if not count:
        raise HTTPException(503, f"Collection {COLLECTION!r} missing or empty — run scripts/ingest.py")
    return {"status": "ok", "collection": COLLECTION, "entries": count, "llm": COHERE_MODEL}


@app.get("/search", tags=["search"])
def search_endpoint(
    q: str = Query(..., min_length=1, description="English or Japanese word, or a natural-language question"),
    n: int = Query(10, ge=1, le=50, description="Number of results"),
    mode: Mode = Query("auto", description="auto routes the query to the best plan; the rest are fixed pipelines"),
    rewrite: bool = Query(True, description="Normalise natural-language queries to a dictionary gloss first"),
    log: bool = Query(True, description="Record the search in the monitoring DB (feeds the dashboard)"),
) -> dict:
    """Same pipeline as the Search page: rewrite → retrieve."""
    q = q.strip()
    try:
        resp = search(q, n, mode, rewrite_mode=None if rewrite else "off")
    except Exception as exc:
        raise HTTPException(502, f"Search failed: {exc}") from exc
    search_id = None
    if log:
        top = resp.results[0] if resp.results else {}
        search_id = log_search(
            q, rewritten_query=resp.rewrite.query, rewrite_method=resp.rewrite.method, mode=resp.mode,
            num_results=n, result_count=len(resp.results),
            top_result=top.get("kanji_form") or top.get("reading"), latency_ms=resp.latency_ms,
        )
        if is_kanji(q):
            log_kanji_lookup(q, source="search")
    return {"search_id": search_id, **asdict(resp), "rewrite": {**asdict(resp.rewrite), "changed": resp.rewrite.changed}}


@app.get("/kanji/{char}", tags=["kanji"])
def kanji_endpoint(
    char: str,
    svg: bool = Query(False, description="Include the KanjiVG stroke-order SVG markup"),
    log: bool = Query(True),
) -> dict:
    """KANJIDIC2 details (readings, meanings, grade, JLPT, common words) for one kanji."""
    if not is_kanji(char):
        raise HTTPException(400, "Provide exactly one kanji character")
    d = lookup_kanji(char)
    if not d:
        raise HTTPException(404, f"No KANJIDIC2 entry for {char!r}")
    if log:
        log_kanji_lookup(char, source="api")
    return {**d, **({"stroke_svg": stroke_svg(char)} if svg else {})}


@app.post("/explain", tags=["grammar"])
def explain_endpoint(req: ExplainRequest) -> dict:
    """JLPT-level-calibrated grammar explanation (Cohere). Markdown bullets."""
    t0 = time.perf_counter()
    try:
        text, ok = explain_grammar(req.sentence, req.english, req.level), True
    except Exception as exc:
        text, ok = str(exc), False
    latency_ms = int((time.perf_counter() - t0) * 1000)
    expl_id = log_explanation(req.sentence, req.level, model=COHERE_MODEL, latency_ms=latency_ms, ok=ok)
    if not ok:
        raise HTTPException(502, f"Explanation unavailable: {text}")
    return {"explanation_id": expl_id, "level": req.level, "model": COHERE_MODEL, "latency_ms": latency_ms, "text": text}


@app.post("/explain/stream", tags=["grammar"])
def explain_stream_endpoint(req: ExplainRequest) -> StreamingResponse:
    """
    Server-sent events: `data: {"text": "…"}` chunks as Cohere streams them,
    then `data: {"done": true, "explanation_id": …, "latency_ms": …}`.
    """
    t0 = time.perf_counter()

    def events():
        chunks: list[str] = []
        ok = True
        try:
            for c in explain_grammar_stream(req.sentence, req.english, req.level):
                chunks.append(c)
                yield f"data: {json.dumps({'text': c})}\n\n"
        except Exception as exc:
            ok = False
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        latency_ms = int((time.perf_counter() - t0) * 1000)
        expl_id = log_explanation(req.sentence, req.level, model=COHERE_MODEL, latency_ms=latency_ms, ok=ok)
        yield f"data: {json.dumps({'done': True, 'explanation_id': expl_id, 'latency_ms': latency_ms})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/feedback", tags=["meta"], status_code=201)
def feedback_endpoint(req: FeedbackRequest) -> dict:
    """Thumbs up (+1) / down (-1) on a search or an explanation."""
    return {"feedback_id": log_feedback(req.kind, req.ref_id, req.rating, req.query)}
