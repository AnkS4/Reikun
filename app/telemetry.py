"""
Usage/event logging behind a small interface.

The API is a stateless instance: by default events go to stdout as one JSON
object per line (`TELEMETRY=stdout`), which the platform's log collection can
pick up. `TELEMETRY=sqlite` keeps the existing SQLite sink
(scripts/feedback_log) for self-hosted setups and the dashboard page.

Both sinks expose the same surface — search / feedback / kanji_lookup /
explanation — returning the row id when the backend has one, else None.

Raw user-entered text never reaches a sink: queries, rewrites and explained
sentences are emitted as 12-hex-char SHA-256 prefixes (`*_hash` fields) —
enough to count repeats without storing the text.
"""

import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

from app.config import TELEMETRY

# Dedicated logger with its own stdout handler — the root logger's
# "%(levelname)s …" format would corrupt the JSON lines.
_log = logging.getLogger("reikun.telemetry")
if not _log.handlers:
    _log.propagate = False
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)


def _h(text: str | None) -> str | None:
    """SHA-256 prefix — groups identical inputs for counts without storing them."""
    return None if text is None else hashlib.sha256(text.encode()).hexdigest()[:12]


def _emit(event: str, **fields) -> None:
    _log.info(json.dumps({"event": event, "ts": datetime.now(UTC).isoformat(timespec="seconds"),
                          **fields}, ensure_ascii=False))


class Telemetry(Protocol):
    def search(self, query: str, *, rewritten_query: str, rewrite_method: str, mode: str,
               num_results: int, result_count: int, top_result: str | None, latency_ms: int,
               cached: bool = False) -> int | None: ...
    def feedback(self, kind: str, ref_id: int | None, rating: int, query: str | None = None) -> int | None: ...
    def kanji_lookup(self, kanji: str, source: str = "api") -> int | None: ...
    def explanation(self, sentence: str, jlpt_level: str, *, model: str, latency_ms: int,
                    ok: bool) -> int | None: ...


class _StdoutTelemetry:
    """One JSON line per event on stdout — the stateless default. No ids."""

    def search(self, query: str, *, rewritten_query: str, rewrite_method: str, mode: str,
               num_results: int, result_count: int, top_result: str | None, latency_ms: int,
               cached: bool = False) -> None:
        _emit("search", query_hash=_h(query), rewritten_query_hash=_h(rewritten_query),
              rewrite_method=rewrite_method, mode=mode, num_results=num_results,
              result_count=result_count, top_result=top_result, latency_ms=latency_ms, cached=cached)

    def feedback(self, kind: str, ref_id: int | None, rating: int, query: str | None = None) -> None:
        _emit("feedback", kind=kind, ref_id=ref_id, rating=rating, query_hash=_h(query))

    def kanji_lookup(self, kanji: str, source: str = "api") -> None:
        _emit("kanji_lookup", kanji=kanji, source=source)

    def explanation(self, sentence: str, jlpt_level: str, *, model: str, latency_ms: int,
                    ok: bool) -> None:
        _emit("explanation", sentence_hash=_h(sentence), jlpt_level=jlpt_level, model=model,
              latency_ms=latency_ms, ok=ok)


class _SqliteTelemetry:
    """The SQLite sink — delegates to scripts/feedback_log's writers."""

    def search(self, query: str, *, rewritten_query: str, rewrite_method: str, mode: str,
               num_results: int, result_count: int, top_result: str | None, latency_ms: int,
               cached: bool = False) -> int:
        from scripts.feedback_log import log_search
        return log_search(query, rewritten_query=rewritten_query, rewrite_method=rewrite_method,
                          mode=mode, num_results=num_results, result_count=result_count,
                          top_result=top_result, latency_ms=latency_ms, cached=cached)

    def feedback(self, kind: str, ref_id: int | None, rating: int, query: str | None = None) -> int:
        from scripts.feedback_log import log_feedback
        return log_feedback(kind, ref_id, rating, query)

    def kanji_lookup(self, kanji: str, source: str = "api") -> int:
        from scripts.feedback_log import log_kanji_lookup
        return log_kanji_lookup(kanji, source=source)

    def explanation(self, sentence: str, jlpt_level: str, *, model: str, latency_ms: int,
                    ok: bool) -> int:
        from scripts.feedback_log import log_explanation
        return log_explanation(sentence, jlpt_level, model=model, latency_ms=latency_ms, ok=ok)


_SINKS = {"stdout": _StdoutTelemetry, "sqlite": _SqliteTelemetry}


@lru_cache(maxsize=1)
def telemetry() -> Telemetry:
    """Process-wide sink selected by the TELEMETRY env var (default stdout)."""
    try:
        return _SINKS[TELEMETRY]()
    except KeyError:
        raise ValueError(f"TELEMETRY={TELEMETRY!r} invalid; expected one of {sorted(_SINKS)}") from None
