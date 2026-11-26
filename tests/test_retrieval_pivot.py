"""Retrieval routing for the Japanese rewrite pivot (no Qdrant/LLM)."""

import threading

import app.retrieval as retrieval
from app.query_rewrite import Rewrite


def _entry(word: str) -> dict:
    return {
        "id": 1,
        "kanji_form": word,
        "reading": word,
        "kanji_forms": [],
        "readings": [],
        "meanings": ["test"],
        "is_common": True,
        "score": 1.0,
    }


def _install_pivot(monkeypatch, calls, result_for):
    monkeypatch.setattr(
        retrieval,
        "rewrite_query",
        lambda query, mode=None: Rewrite(query, "supermarket", "llm", ("スーパー", "スーパーマーケット")),
    )
    monkeypatch.setattr(retrieval, "embed_query", lambda query, **kwargs: ("dense", "sparse"))

    def fake_auto(query, num_results, *, vectors, route):
        calls.append((query, route))
        return result_for(query)

    monkeypatch.setattr(retrieval, "_auto_search", fake_auto)
    retrieval._search_cached.cache_clear()


def test_pivot_uses_the_first_japanese_headword(monkeypatch):
    calls: list[tuple[str, str]] = []
    _install_pivot(monkeypatch, calls, lambda q: [_entry(q)] if q == "スーパー" else [])

    resp = retrieval.search("a place where you buy food", 5, "auto", rewrite_mode="auto")

    assert calls == [("スーパー", "ja")]
    assert resp.rewrite.query == "supermarket"
    assert resp.rewrite.japanese == ("スーパー", "スーパーマーケット")
    assert resp.meta["route"] == "ja"
    assert resp.results[0]["kanji_form"] == "スーパー"


def test_pivot_falls_back_to_english_when_japanese_candidates_are_empty(monkeypatch):
    calls: list[tuple[str, str]] = []
    _install_pivot(
        monkeypatch,
        calls,
        lambda q: [_entry(q)] if q == "supermarket" else [],
    )

    resp = retrieval.search("a place where you buy food", 5, "auto", rewrite_mode="auto")

    assert calls == [("スーパー", "ja"), ("スーパーマーケット", "ja"), ("supermarket", "en_word")]
    assert resp.meta["route"] == "en_word"
    assert resp.results[0]["kanji_form"] == "supermarket"


# ── _infl_indexed: positive latches, everything else re-probes ───────────────

def _reset_infl_probe(monkeypatch) -> None:
    """Back to the never-probed state (a module memo replaced @cache), restored
    on teardown so tests can't latch state for each other."""
    monkeypatch.setattr(retrieval, "_infl_indexed_cache", None)
    monkeypatch.setattr(retrieval, "_infl_probed_at", 0.0)


def test_infl_indexed_checked_once_per_process(monkeypatch):
    """_exact_filter runs on every search arm, so a non-positive answer must
    not get a fresh get_collection round-trip per call — it is memoized until
    the _INFL_PROBE_RETRY_S re-probe."""
    calls = 0

    class _FakeCollection:
        payload_schema = ()  # immutable; only truthiness matters to _infl_indexed

    class _FakeClient:
        def get_collection(self, *_a, **_k):
            nonlocal calls
            calls += 1
            return _FakeCollection()

    monkeypatch.setattr(retrieval, "qdrant_client", _FakeClient)
    _reset_infl_probe(monkeypatch)
    assert retrieval._infl_indexed() is False
    assert retrieval._infl_indexed() is False  # within the retry TTL: no second round-trip
    assert calls == 1
    retrieval._infl_probed_at -= retrieval._INFL_PROBE_RETRY_S + 1  # expire the memo
    assert retrieval._infl_indexed() is False  # re-probed, still not indexed
    assert calls == 2


def test_infl_indexed_positive_latches_for_the_process(monkeypatch):
    """The schema is fixed at ingest and ingest completes before the API boots:
    once the arm is seen indexed it stays on for the process lifetime — TTL or
    no TTL, no further round-trips."""
    calls = 0

    class _FakeCollection:
        payload_schema = ("infl_forms",)

    class _FakeClient:
        def get_collection(self, *_a, **_k):
            nonlocal calls
            calls += 1
            return _FakeCollection()

    monkeypatch.setattr(retrieval, "qdrant_client", _FakeClient)
    _reset_infl_probe(monkeypatch)
    assert retrieval._infl_indexed() is True
    retrieval._infl_probed_at -= retrieval._INFL_PROBE_RETRY_S + 1  # expiry must not matter
    assert retrieval._infl_indexed() is True
    assert calls == 1


def test_infl_indexed_transport_error_does_not_latch(monkeypatch):
    """A failed first probe must degrade (conjugation arm off) without latching
    until restart — one dropped packet at boot may not disable exact matching
    forever. Within the retry TTL the failure is memoized (no retry storm);
    after it, the probe runs again and a recovered client flips the arm on."""
    probes = 0

    class _RecoveredCollection:
        payload_schema = ("infl_forms",)

    class _BlipClient:
        def get_collection(self, *_a, **_k):
            nonlocal probes
            probes += 1
            if probes == 1:
                raise RuntimeError("qdrant briefly unreachable")
            return _RecoveredCollection()

    monkeypatch.setattr(retrieval, "qdrant_client", _BlipClient)
    _reset_infl_probe(monkeypatch)
    assert retrieval._infl_indexed() is False  # degrade on the blip
    assert retrieval._infl_indexed() is False  # memoized within the TTL
    assert probes == 1
    retrieval._infl_probed_at -= retrieval._INFL_PROBE_RETRY_S + 1  # expire
    assert retrieval._infl_indexed() is True  # recovered: the arm rides again
    assert retrieval._infl_indexed() is True  # and the positive latches
    assert probes == 2


def test_infl_indexed_concurrent_probes_serialise(monkeypatch):
    """Two threads past an expired negative TTL used to probe concurrently:
    one stored True, the other hit a transient error and stored False over it,
    un-latching the supposedly process-permanent positive (and the expiry
    itself stampeded the probe). The probe lock must serialise them — exactly
    one round-trip, both callers see True, the latch survives."""
    probes: list[str] = []             # thread name of every get_collection
    first_inside = threading.Event()   # probe 1 is mid-flight
    second_started = threading.Event()  # caller 2 has joined the race
    second_probed = threading.Event()  # caller 2 got through to a probe of its own
    late_failure = threading.Event()   # arms a failure for any *second* probe

    class _IndexedCollection:
        payload_schema = ("infl_forms",)

    class _RacyClient:
        def get_collection(self, *_a, **_k):
            probes.append(threading.current_thread().name)
            if late_failure.is_set():  # the simulated late failure: a racy
                raise RuntimeError("transient blip on the concurrent probe")  # caller 2 hits this
            first_inside.set()
            # Hold probe 1 open until caller 2 has joined, then leave a grace
            # window for a (broken) unlocked caller 2 to sail through — under
            # the lock it is parked on acquire, so the event never fires.
            second_started.wait(5)
            second_probed.wait(0.5)
            return _IndexedCollection()

    results: dict[str, bool] = {}

    def _first() -> None:
        results["first"] = retrieval._infl_indexed()

    def _second() -> None:
        second_started.set()
        results["second"] = retrieval._infl_indexed()

    monkeypatch.setattr(retrieval, "qdrant_client", _RacyClient)
    _reset_infl_probe(monkeypatch)
    first = threading.Thread(target=_first, name="first-probe")
    first.start()
    assert first_inside.wait(5), "first probe never took flight"
    late_failure.set()  # any probe after this point fails, like a real blip
    second = threading.Thread(target=_second, name="second-probe")
    second.start()
    first.join(5)
    second.join(5)
    assert not first.is_alive() and not second.is_alive()  # never hang the suite
    assert probes == ["first-probe"]  # the second caller never reached the client
    assert results == {"first": True, "second": True}  # no failure overwrote the latch
    assert retrieval._infl_indexed_cache is True  # the positive stayed latched
