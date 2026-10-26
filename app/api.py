"""
Standalone HTTP API over the retrieval, kanji-lookup and grammar-explanation
modules — the serving half of the app (the frontend is a separate static site).

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
import time
from contextlib import asynccontextmanager
from typing import Annotated, Literal, get_args

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import (
    APP_VERSION,
    COLLECTION,
    CORS_ORIGINS,
    LLM_MODEL,
    LLM_PROVIDER,
    RATE_LIMIT_EXPLAIN,
    RATE_LIMIT_SEARCH,
    TRUSTED_PROXY_HOPS,
    qdrant_client,
)
from app.grammar_explain import (
    JLPT_LEVELS,
    MAX_HINT_CHARS,
    explain_grammar,
    explain_grammar_stream,
    last_model,
    validate_input,
)
from app.kanji_lookup import is_kanji, jlpt_kanji, random_kanji
from app.ratelimit import rate_limited
from app.render import (
    furigana_parts,
    kanji_card,
    kanji_group_cards,
    kanji_hover,
    related_words,
    segment_chip,
)
from app.retrieval import MODES, is_headword, morph_hint, search, warm_headword_index
from app.telemetry import telemetry

log = logging.getLogger("reikun.api")

# Standalone `uvicorn app.api:app` doesn't configure the root logger, so do it
# here unless something else already did (the Streamlit entrypoint, pytest…).
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

Mode = Literal["auto", "hybrid", "vector", "text"]
Level = Literal["N5", "N4", "N3", "N2", "N1"]
assert set(get_args(Mode)) == set(MODES) and set(get_args(Level)) == set(JLPT_LEVELS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm the headword trie, Sudachi dictionary and ONNX sessions on daemon
    # threads - returns immediately so /health is live during the ~2-5 s load.
    warm_headword_index()
    yield


app = FastAPI(
    title="Reikun API",
    version=APP_VERSION,
    description=(
        "Japanese dictionary search (hybrid dense + BM25), kanji details and JLPT-calibrated grammar explanations."
    ),
    lifespan=lifespan,
)

# Added before CORS so CORS stays outermost (error responses keep their CORS
# headers). Starlette's GZip skips text/event-stream, so /explain/stream is
# unaffected; small payloads (< 1 KB) aren't worth compressing.
app.add_middleware(GZipMiddleware, minimum_size=1024)

_origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],  # '*' + credentials is not a valid combo
    allow_methods=["*"],
    allow_headers=["*"],
)


# Per-client request limits (see app/ratelimit.py) — 429 + Retry-After when exceeded.
_explain_limit = Depends(rate_limited(RATE_LIMIT_EXPLAIN, TRUSTED_PROXY_HOPS))
_search_limit = Depends(rate_limited(RATE_LIMIT_SEARCH, TRUSTED_PROXY_HOPS))

# Static dictionary data: safe for browsers/CDNs to reuse for a day.
_CACHE_STATIC = "public, max-age=86400, stale-while-revalidate=604800"


# ── Schemas ──────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """FastAPI's HTTPException body — declared so non-422 errors show up in the schema."""
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    collection: str
    entries: int
    llm: str


class RubyPart(BaseModel):
    """One display segment of a headword: `rt` carries the furigana when set."""
    text: str
    rt: str | None = None


class ExampleSentence(BaseModel):
    japanese: str
    english: str = ""


class CommonWord(BaseModel):
    kanji_form: str | None = None
    reading: str = ""
    meanings: list[str] = []
    gloss: str = ""
    ruby: list[RubyPart] = []


class InflectionRow(BaseModel):
    """One row of a verb/adjective conjugation table."""
    form: str            # English row label: "Past", "Te-form", …
    surface: str         # written form: 走った
    kana: str | None = None


class SearchResult(BaseModel):
    id: int | None
    kanji_form: str | None = None
    reading: str = ""
    kanji_forms: list[str] = []
    readings: list[str] = []
    meanings: list[str] = []
    example_sentences: list[ExampleSentence] = []
    is_common: bool = False
    text: str = ""
    score: float = 0.0
    ruby: list[RubyPart] = []
    related: list[CommonWord] = []
    inflected_forms: list[InflectionRow] = []
    # when the *query itself* is one of the entry's inflected forms, its row
    # label ("走った searching 走る → "Past")
    inflection: str | None = None


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


class SearchMeta(BaseModel):
    """Per-request diagnostics. `route` is set in auto mode. On a cache hit
    the timing fields describe the original computation; on a `too_long`
    rejection they are absent — the pipeline never ran."""
    route: Literal["ja", "en_word", "en_sentence"] | None = None
    rewrite_ms: int | None = None
    embed_ms: int | None = None
    retrieve_ms: int | None = None
    segment_ms: int | None = None
    cached: bool = False
    too_long: int | None = Field(None, description="The character cap the query exceeded")


class SearchResponseModel(BaseModel):
    search_id: int | None = None
    results: list[SearchResult]
    rewrite: RewriteInfo
    mode: str
    latency_ms: int
    segments: list[Segment] | None = None
    meta: SearchMeta = SearchMeta()


class ReadingChip(BaseModel):
    """One on/kun reading; `okurigana` is the part after KANJIDIC2's dot (た.べる)."""
    stem: str
    okurigana: str | None = None


class MetaBadgeGroup(BaseModel):
    """Browse key for a *clickable* badge — strokes/grade/JLPT badges link to
    /kanji/group so the card can list words of the same metadata group."""
    by: Literal["strokes", "grade", "jlpt"]
    value: int


class MetaBadge(BaseModel):
    label: str
    tip: str
    group: MetaBadgeGroup | None = None


class StrokeNumber(BaseModel):
    x: float
    y: float
    value: int


class StrokeData(BaseModel):
    """KanjiVG stroke order as sanitized data — the frontend draws the SVG."""
    view_box: str
    strokes: list[str]
    numbers: list[StrokeNumber]


class KanjiGroupEntry(BaseModel):
    """One kanji of a same-metadata group (strokes/grade/JLPT) on the
    /kanji-group browse page — glyph, gloss and enough metadata for a grid
    card; the full card is a click away (search the literal)."""
    literal: str
    meanings: list[str] = []
    on_yomi: list[str] = []
    kun_yomi: list[str] = []
    stroke_count: int | None = None
    freq: int | None = None
    jlpt_level: int | None = None
    meta: list[MetaBadge] = []


class KanjiGroupResponse(BaseModel):
    by: Literal["strokes", "grade", "jlpt"]
    value: int
    label: str
    total: int
    offset: int
    kanjis: list[KanjiGroupEntry]


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


class KanjiHover(BaseModel):
    """Compact card for kanji-in-text hover tooltips (batch endpoint)."""
    literal: str
    meanings: list[str] = []
    on_yomi: list[str] = []
    kun_yomi: list[str] = []
    meta: list[MetaBadge] = []


class ExplainRequest(BaseModel):
    sentence: str = Field(min_length=1, description="Japanese example sentence")
    english: str = Field("", description="English translation (improves the explanation)")
    level: Level = "N5"


class ExplainResponse(BaseModel):
    explanation_id: int | None = None
    level: str
    provider: str
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

@app.get("/health", tags=["meta"], response_model=HealthResponse)
def health(response: Response) -> dict:
    """Liveness only — the process is up. Dependencies are checked by /ready."""
    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok"}


@app.get(
    "/ready",
    tags=["meta"],
    response_model=ReadyResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Qdrant unreachable, or the collection is missing/empty"}
    },
)
def ready(response: Response) -> dict:
    """Readiness: a real query against the Qdrant collection.
    503 when Qdrant is unreachable or the collection is missing/empty."""
    response.headers["Cache-Control"] = "no-store"
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
    return {"status": "ready", "collection": COLLECTION, "entries": count, "llm": LLM_MODEL}


# ── Search ───────────────────────────────────────────────────────────────────

@app.get("/search", tags=["search"], response_model=SearchResponseModel, dependencies=[_search_limit])
def search_endpoint(
    background: BackgroundTasks,
    # pattern=\S: whitespace-only input is a 422, not an embed of "".
    q: Annotated[
        str,
        Query(min_length=1, pattern=r"\S", description="English or Japanese word, or a natural-language question"),
    ],
    n: Annotated[int, Query(ge=1, le=50, description="Number of results")] = 10,
    mode: Annotated[
        Mode,
        Query(description="auto routes the query to the best plan; the rest are fixed pipelines"),
    ] = "auto",
    rewrite: Annotated[
        bool,
        Query(description="Normalise natural-language queries to a dictionary gloss first"),
    ] = True,
    log: Annotated[bool, Query(description="Record the search in the telemetry sink")] = True,
) -> dict:
    """Same pipeline as the dictionary UI: rewrite → route → retrieve.
    Results carry `ruby` parts for furigana rendering; Japanese sentences that
    decompose into word units come back in `segments` (the "parsed as" chips)."""
    q = q.strip()
    try:
        resp = search(q, n, mode, rewrite_mode=None if rewrite else "off")
    except Exception:
        # Full detail goes to the logs; the client gets no backend internals
        # (Qdrant hostnames, stack text) from an exception string.
        log.exception("search failed")
        raise HTTPException(502, "Search is temporarily unavailable. Please try again.") from None
    search_id = None
    if log:
        # .search stays inline — its row id is part of the response; the
        # kanji-lookup event isn't, so it's written after the response is sent.
        top = resp.results[0] if resp.results else {}
        search_id = telemetry().search(
            q, rewritten_query=resp.rewrite.query, rewrite_method=resp.rewrite.method, mode=resp.mode,
            num_results=n, result_count=len(resp.results),
            top_result=top.get("kanji_form") or top.get("reading"), latency_ms=resp.latency_ms,
            cached=bool(resp.meta.get("cached")), route=resp.meta.get("route"),
            embed_ms=resp.meta.get("embed_ms"), retrieve_ms=resp.meta.get("retrieve_ms"),
        )
        if is_kanji(q):
            background.add_task(telemetry().kanji_lookup, q, source="search")
    meta = dict(resp.meta)
    raw_segments = meta.pop("segments", None)
    results = []
    for r in resp.results:
        head = r.get("kanji_form") or r.get("reading") or r.get("text") or ""
        entry = {
            **r,
            "ruby": furigana_parts(head, r.get("reading")),
            # Whole-entry-card only: every written form joins the exclusion
            # set so the word can't recommend itself.
            "related": related_words(
                (head, *(r.get("kanji_forms") or ()), *(r.get("readings") or ())),
                (head, *(r.get("kanji_forms") or ()), *(r.get("readings") or ())),
            )
            if head
            else [],
        }
        results.append(entry)
    return {
        "search_id": search_id,
        "results": results,
        "rewrite": {
            "original": resp.rewrite.original,
            "query": resp.rewrite.query,
            "method": resp.rewrite.method,
            "changed": resp.rewrite.changed,
        },
        "mode": resp.mode,
        "latency_ms": resp.latency_ms,
        "segments": [segment_chip(s) for s in raw_segments] if raw_segments else None,
        "meta": meta,
    }


# ── Kanji ────────────────────────────────────────────────────────────────────

class RandomKanji(BaseModel):
    kanji: str


# Declared before /kanji/{char} so "random" isn't parsed as a kanji path param.
@app.get("/kanji/random", tags=["kanji"], response_model=RandomKanji)
def kanji_random_endpoint(

    response: Response,
    level: Annotated[
        Level | None,
        Query(description="Prefer kanji tagged at this JLPT level (falls back to the common pool)"),
    ] = None,
) -> dict:
    """A random kanji that is itself a JMdict headword — the shuffle button's
    pick. Same rules as the UI: frequency-ranked pool, optionally restricted
    to a JLPT level, up to 8 headword-verified tries then an unchecked pick."""
    response.headers["Cache-Control"] = "no-store"  # a cached "random" would repeat itself
    pool = jlpt_kanji(level) if level else None
    try:
        for _ in range(8):
            if is_headword(c := random_kanji(within=pool)):
                return {"kanji": c}
    except Exception:
        pass  # Qdrant unreachable → unchecked pick below
    return {"kanji": random_kanji(within=pool)}


GroupKey = Literal["strokes", "grade", "jlpt"]


@app.get("/kanji/group", tags=["kanji"], response_model=KanjiGroupResponse)
def kanji_group_endpoint(
    response: Response,
    by: Annotated[GroupKey, Query(description="Kanji metadata grouping key")],
    value: Annotated[
        int, Query(ge=1, le=30, description="Group value (stroke count, KANJIDIC2 grade, or old-scale JLPT level)")
    ],
    n: Annotated[int, Query(ge=1, le=100)] = 40,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    """Browse the KANJI of one metadata group — the click target of the kanji
    card's badges ("8 strokes", "Grade 3", "JLPT N4"). Pages of characters,
    frequency-ranked most-common first; `total` drives Prev/Next pagination."""
    cards = kanji_group_cards(by, str(value), n, offset)
    if cards is None or cards["total"] == 0:
        raise HTTPException(404, f"No kanji in group {by}={value}")
    response.headers["Cache-Control"] = _CACHE_STATIC
    return cards


@app.get("/kanji", tags=["kanji"], response_model=dict[str, KanjiHover | None])
def kanji_batch_endpoint(
    response: Response,
    chars: Annotated[
        str,
        Query(
            min_length=1,
            max_length=100,
            description="Kanji characters to look up (deduped; every char is treated as one kanji)",
        ),
    ],
) -> dict:
    """Compact hover-card data for several kanji at once — one round-trip per
    sentence of tooltips. Unknown kanji map to null."""
    seen = {c: kanji_hover(c) for c in dict.fromkeys(chars) if is_kanji(c)}
    if not seen:
        raise HTTPException(400, "Provide at least one kanji character")
    response.headers["Cache-Control"] = _CACHE_STATIC
    return seen


@app.get("/kanji/{char}", tags=["kanji"], response_model=KanjiCard)
def kanji_endpoint(
    char: str,
    background: BackgroundTasks,
    strokes: Annotated[
        bool,
        Query(description="Include KanjiVG stroke order as structured data (viewBox, path d's, number labels)"),
    ] = False,
    log: Annotated[bool, Query()] = True,
) -> dict:
    """KANJIDIC2 details (meta badges, readings with okurigana parts, common
    words with ruby parts) for one kanji — the frontend renders the card."""
    if not is_kanji(char):
        raise HTTPException(400, "Provide exactly one kanji character")
    card = kanji_card(char, strokes=strokes)
    if not card:
        raise HTTPException(404, f"No KANJIDIC2 entry for {char!r}")
    if log:
        background.add_task(telemetry().kanji_lookup, char, source="api")
    return card


# ── Grammar explanations ─────────────────────────────────────────────────────

EXPLAIN_UNAVAILABLE = "The grammar explanation service is busy or unavailable. Please try again in a moment."


@app.post("/explain", tags=["grammar"], response_model=ExplainResponse, dependencies=[_explain_limit])
def explain_endpoint(req: ExplainRequest) -> dict:
    """JLPT-level-calibrated grammar explanation (LLM). Markdown bullets."""
    try:
        sentence, english, _ = validate_input(req.sentence, req.english)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    hint = morph_hint(sentence)[:MAX_HINT_CHARS]
    t0 = time.perf_counter()
    text, ok = "", True
    try:
        text = explain_grammar(sentence, english, req.level, hint=hint)
    except Exception:
        # The provider's error text can carry org/model/quota details — log it, don't relay it.
        log.exception("explain failed")
        ok = False
    latency_ms = int((time.perf_counter() - t0) * 1000)
    expl_id = telemetry().explanation(sentence, req.level, model=last_model(), latency_ms=latency_ms, ok=ok)
    if not ok:
        raise HTTPException(502, EXPLAIN_UNAVAILABLE)
    return {
        "explanation_id": expl_id,
        "level": req.level,
        "provider": LLM_PROVIDER,
        "model": last_model(),
        "latency_ms": latency_ms,
        "text": text,
    }


@app.post("/explain/stream", tags=["grammar"], dependencies=[_explain_limit])
def explain_stream_endpoint(req: ExplainRequest) -> StreamingResponse:
    """
    Server-sent events: `data: {"text": "…"}` chunks as the LLM streams them,
    then `data: {"done": true, "explanation_id": …, "latency_ms": …}`.
    """
    try:
        sentence, english, _ = validate_input(req.sentence, req.english)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    hint = morph_hint(sentence)[:MAX_HINT_CHARS]
    t0 = time.perf_counter()

    def events():
        chunks: list[str] = []
        ok = True
        try:
            for c in explain_grammar_stream(sentence, english, req.level, hint=hint):
                chunks.append(c)
                yield f"data: {json.dumps({'text': c})}\n\n"
        except Exception:
            log.exception("explain stream failed")
            ok = False
            yield f"data: {json.dumps({'error': EXPLAIN_UNAVAILABLE})}\n\n"
        latency_ms = int((time.perf_counter() - t0) * 1000)
        expl_id = telemetry().explanation(sentence, req.level, model=last_model(), latency_ms=latency_ms, ok=ok)
        payload = {
            "done": True,
            "explanation_id": expl_id,
            "latency_ms": latency_ms,
            "provider": LLM_PROVIDER,
            "model": last_model(),
        }
        yield f"data: {json.dumps(payload)}\n\n"

    # no-transform + X-Accel-Buffering: keep proxies from buffering or compressing
    # the stream, which would hold every chunk back until the end.
    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/feedback", tags=["meta"], status_code=201, response_model=FeedbackResponse)
def feedback_endpoint(req: FeedbackRequest) -> dict:
    """Thumbs up (+1) / down (-1) on a search or an explanation."""
    return {"feedback_id": telemetry().feedback(req.kind, req.ref_id, req.rating, req.query)}
