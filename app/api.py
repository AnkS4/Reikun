"""
Standalone HTTP API over the retrieval, kanji-lookup and grammar-explanation
modules — the serving half of the SvelteKit migration (Plan.md Phase 1).

    uvicorn app.api:app --host 0.0.0.0 --port 8000          # what Docker runs
    uvicorn app.api:app --reload                            # dev

Routes sit at the root (the old combined app mounted them under /api).
Rendering is JSON, not HTML: results carry furigana `ruby` parts, the kanji
card carries badge/readings/common-word structure, and stroke order ships as
sanitized path data — see app/render.py.

Docs: /docs (Swagger) · /redoc · /openapi.json.
"""

import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.http.exceptions import UnexpectedResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import COHERE_MODEL, COLLECTION, CORS_ORIGINS, qdrant_client  # noqa: E402
from app.grammar_explain import JLPT_LEVELS, explain_grammar, explain_grammar_stream  # noqa: E402
from app.kanji_lookup import is_kanji, jlpt_kanji, random_kanji, stroke_svg  # noqa: E402
from app.render import furigana_parts, kanji_card, kanji_hover, segment_chip  # noqa: E402
from app.retrieval import MODES, is_headword, search, warm_headword_index  # noqa: E402
from app.telemetry import telemetry  # noqa: E402

# Standalone `uvicorn app.api:app` doesn't configure the root logger, so do it
# here unless something else already did (the Streamlit entrypoint, pytest…).
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

Mode = Literal["auto", "hybrid", "vector", "text"]
Level = Literal["N5", "N4", "N3", "N2", "N1"]
assert set(Mode.__args__) == set(MODES) and set(Level.__args__) == set(JLPT_LEVELS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm the headword trie, Sudachi dictionary and ONNX sessions on daemon
    # threads — returns immediately so /health is live during the ~2–5 s load.
    warm_headword_index()
    yield


app = FastAPI(
    title="Reikun API",
    version="0.3.0",
    description="Japanese dictionary search (hybrid dense + BM25), kanji details and JLPT-calibrated grammar explanations.",
    lifespan=lifespan,
)

_origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],  # '*' + credentials is not a valid combo
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────────────

class RubyPart(BaseModel):
    """One display segment of a headword: `rt` carries the furigana when set."""
    text: str
    rt: str | None = None


class SearchResult(BaseModel):
    id: int | None
    kanji_form: str | None = None
    reading: str = ""
    kanji_forms: list[str] = []
    readings: list[str] = []
    meanings: list[str] = []
    example_sentences: list[dict] = []
    is_common: bool = False
    text: str = ""
    score: float = 0.0
    ruby: list[RubyPart] = []


class RewriteInfo(BaseModel):
    original: str
    query: str
    method: str  # none | heuristic | llm
    changed: bool


class Segment(BaseModel):
    """One word unit of a parsed Japanese sentence (a chip)."""
    text: str
    kanji_form: str | None = None
    reading: str = ""
    meanings: list[str] = []
    gloss: str = ""
    ruby: list[RubyPart] = []
    options: list[str] = []
    approx: bool = False


class SearchResponseModel(BaseModel):
    search_id: int | None = None
    results: list[SearchResult]
    rewrite: RewriteInfo
    mode: str
    latency_ms: int
    segments: list[Segment] | None = None
    meta: dict[str, Any] = {}


class ReadingChip(BaseModel):
    """One on/kun reading; `okurigana` is the part after KANJIDIC2's dot (た.べる)."""
    stem: str
    okurigana: str | None = None


class MetaBadge(BaseModel):
    label: str
    tip: str


class CommonWord(BaseModel):
    kanji_form: str | None = None
    reading: str = ""
    meanings: list[str] = []
    gloss: str = ""
    ruby: list[RubyPart] = []


class StrokeNumber(BaseModel):
    x: float
    y: float
    value: int


class StrokeData(BaseModel):
    """KanjiVG stroke order as sanitized data — the frontend draws the SVG."""
    view_box: str
    strokes: list[str]
    numbers: list[StrokeNumber]


class KanjiCard(BaseModel):
    literal: str | None = None
    codepoint_hex: str | None = None
    stroke_count: int | None = None
    grade: int | None = None
    freq: int | None = None
    jlpt_level: int | None = None
    meanings: list[str] = []
    meta: list[MetaBadge] = []
    on_yomi: list[str] = []
    kun_yomi: list[str] = []
    readings: dict[str, list[ReadingChip]] = {}
    common_words: list[CommonWord] = []
    stroke: StrokeData | None = None
    stroke_svg: str | None = None


class KanjiHover(BaseModel):
    """Compact card for kanji-in-text hover tooltips (batch endpoint)."""
    literal: str
    meanings: list[str] = []
    on_yomi: list[str] = []
    kun_yomi: list[str] = []
    meta: list[MetaBadge] = []


class ExplainRequest(BaseModel):
    sentence: str = Field(..., min_length=1, description="Japanese example sentence")
    english: str = Field("", description="English translation (improves the explanation)")
    level: Level = "N5"


class ExplainResponse(BaseModel):
    explanation_id: int | None = None
    level: str
    model: str
    latency_ms: int
    text: str


class FeedbackRequest(BaseModel):
    kind: Literal["search", "explanation"]
    ref_id: int | None = Field(None, description="`search_id` from /search or `explanation_id` from /explain")
    rating: Literal[1, -1]
    query: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int | None = None


# ── Meta ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness only — the process is up. Dependencies are checked by /ready."""
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready() -> dict:
    """Readiness: a real query against the Qdrant collection.
    503 when Qdrant is unreachable or the collection is missing/empty."""
    try:  # one round-trip: a missing collection is a 404 from count, not a second request
        client = qdrant_client()
        count = client.count(COLLECTION).count
        if count:
            # Exercise the read path, not just the counter — a collection can
            # exist but be too unhealthy to serve points.
            client.scroll(COLLECTION, limit=1, with_payload=False, with_vectors=False)
    except UnexpectedResponse as exc:
        if exc.status_code != 404:
            raise HTTPException(503, f"Qdrant error: {exc.status_code}") from exc
        count = 0
    except Exception as exc:  # connection refused, DNS, …
        raise HTTPException(503, f"Qdrant unreachable: {type(exc).__name__}") from exc
    if not count:
        raise HTTPException(503, f"Collection {COLLECTION!r} missing or empty — run scripts/ingest.py")
    return {"status": "ready", "collection": COLLECTION, "entries": count, "llm": COHERE_MODEL}


# ── Search ───────────────────────────────────────────────────────────────────

@app.get("/search", tags=["search"], response_model=SearchResponseModel)
def search_endpoint(
    background: BackgroundTasks,
    q: str = Query(..., min_length=1, description="English or Japanese word, or a natural-language question"),
    n: int = Query(10, ge=1, le=50, description="Number of results"),
    mode: Mode = Query("auto", description="auto routes the query to the best plan; the rest are fixed pipelines"),
    rewrite: bool = Query(True, description="Normalise natural-language queries to a dictionary gloss first"),
    log: bool = Query(True, description="Record the search in the telemetry sink"),
) -> dict:
    """Same pipeline as the dictionary UI: rewrite → route → retrieve.
    Results carry `ruby` parts for furigana rendering; Japanese sentences that
    decompose into word units come back in `segments` (the "parsed as" chips)."""
    q = q.strip()
    try:
        resp = search(q, n, mode, rewrite_mode=None if rewrite else "off")
    except Exception as exc:
        raise HTTPException(502, f"Search failed: {exc}") from exc
    search_id = None
    if log:
        # .search stays inline — its row id is part of the response; the
        # kanji-lookup event isn't, so it's written after the response is sent.
        top = resp.results[0] if resp.results else {}
        search_id = telemetry().search(
            q, rewritten_query=resp.rewrite.query, rewrite_method=resp.rewrite.method, mode=resp.mode,
            num_results=n, result_count=len(resp.results),
            top_result=top.get("kanji_form") or top.get("reading"), latency_ms=resp.latency_ms,
            cached=bool(resp.meta.get("cached")),
        )
        if is_kanji(q):
            background.add_task(telemetry().kanji_lookup, q, source="search")
    meta = dict(resp.meta)
    raw_segments = meta.pop("segments", None)
    results = []
    for r in resp.results:
        head = r.get("kanji_form") or r.get("reading") or r.get("text") or ""
        results.append({**r, "ruby": furigana_parts(head, r.get("reading"))})
    return {
        "search_id": search_id,
        "results": results,
        "rewrite": {**asdict(resp.rewrite), "changed": resp.rewrite.changed},
        "mode": resp.mode,
        "latency_ms": resp.latency_ms,
        "segments": [segment_chip(s) for s in raw_segments] if raw_segments else None,
        "meta": meta,
    }


# ── Kanji ────────────────────────────────────────────────────────────────────

# Declared before /kanji/{char} so "random" isn't parsed as a kanji path param.
@app.get("/kanji/random", tags=["kanji"])
def kanji_random_endpoint(
    level: Level | None = Query(None, description="Prefer kanji tagged at this JLPT level (falls back to the common pool)"),
) -> dict:
    """A random kanji that is itself a JMdict headword — the shuffle button's
    pick. Same rules as the UI: frequency-ranked pool, optionally restricted
    to a JLPT level, up to 8 headword-verified tries then an unchecked pick."""
    pool = jlpt_kanji(level) if level else None
    try:
        for _ in range(8):
            if is_headword(c := random_kanji(within=pool)):
                return {"kanji": c}
    except Exception:
        pass  # Qdrant unreachable → unchecked pick below
    return {"kanji": random_kanji(within=pool)}


@app.get("/kanji", tags=["kanji"], response_model=dict[str, KanjiHover | None])
def kanji_batch_endpoint(
    chars: str = Query(..., min_length=1, max_length=100,
                       description="Kanji characters to look up (deduped; every char is treated as one kanji)"),
) -> dict:
    """Compact hover-card data for several kanji at once — one round-trip per
    sentence of tooltips. Unknown kanji map to null."""
    seen = dict.fromkeys(c for c in chars if is_kanji(c))
    if not seen:
        raise HTTPException(400, "Provide at least one kanji character")
    return {c: kanji_hover(c) for c in seen}


@app.get("/kanji/{char}", tags=["kanji"], response_model=KanjiCard)
def kanji_endpoint(
    char: str,
    background: BackgroundTasks,
    strokes: bool = Query(False, description="Include KanjiVG stroke order as structured data (viewBox, path d's, number labels)"),
    svg: bool = Query(False, description="Include the raw KanjiVG stroke-order SVG markup"),
    log: bool = Query(True),
) -> dict:
    """KANJIDIC2 details (meta badges, readings with okurigana parts, common
    words with ruby parts) for one kanji — the frontend renders the card."""
    if not is_kanji(char):
        raise HTTPException(400, "Provide exactly one kanji character")
    card = kanji_card(char, strokes=strokes)
    if not card:
        raise HTTPException(404, f"No KANJIDIC2 entry for {char!r}")
    if svg:
        card["stroke_svg"] = stroke_svg(char)
    if log:
        background.add_task(telemetry().kanji_lookup, char, source="api")
    return card


# ── Grammar explanations ─────────────────────────────────────────────────────

@app.post("/explain", tags=["grammar"], response_model=ExplainResponse)
def explain_endpoint(req: ExplainRequest) -> dict:
    """JLPT-level-calibrated grammar explanation (Cohere). Markdown bullets."""
    t0 = time.perf_counter()
    try:
        text, ok = explain_grammar(req.sentence, req.english, req.level), True
    except Exception as exc:
        text, ok = str(exc), False
    latency_ms = int((time.perf_counter() - t0) * 1000)
    expl_id = telemetry().explanation(req.sentence, req.level, model=COHERE_MODEL, latency_ms=latency_ms, ok=ok)
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
        expl_id = telemetry().explanation(req.sentence, req.level, model=COHERE_MODEL, latency_ms=latency_ms, ok=ok)
        yield f"data: {json.dumps({'done': True, 'explanation_id': expl_id, 'latency_ms': latency_ms, 'model': COHERE_MODEL})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/feedback", tags=["meta"], status_code=201, response_model=FeedbackResponse)
def feedback_endpoint(req: FeedbackRequest) -> dict:
    """Thumbs up (+1) / down (-1) on a search or an explanation."""
    return {"feedback_id": telemetry().feedback(req.kind, req.ref_id, req.rating, req.query)}
