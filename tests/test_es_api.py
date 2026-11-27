"""Spanish pack (es_words) tests — hermetic: the Qdrant calls are faked, so
CI runs these without a cluster. The collection-integration itself is
verified by hand against the local Docker Qdrant (M0 exit tests)."""

from fastapi.testclient import TestClient

from app import api
from app.lang import es as es_pack

client = TestClient(api.app)


def _hit(word: str, *, meanings=("house",), infl=(), pos="noun", score=1.0):
    """Shape a qdrant hit the way _hit_to_dict reads it."""
    from types import SimpleNamespace

    payload = {
        "kanji_form": None,
        "reading": word,
        "meanings": list(meanings),
        "gloss_keys": [t.lower() for m in meanings for t in m.split()],
        "infl_forms": list(infl),
        "pos": pos,
        "text": f"{word}: {'; '.join(meanings)}",
        "senses": [{"glosses": list(meanings), "pos": [pos]}],
    }
    return SimpleNamespace(id=hash(word) & 0x7FFF_FFFF, score=score, payload=payload)


def _fake_query(monkeypatch, hits):
    """Fake at the qdrant seam: the raw hits flow through _hit_to_dict like
    the real _es_query does."""
    calls = []

    def fake_query(query, num_results, vectors=None):
        calls.append((query, num_results))
        return [es_pack._hit_to_dict(h) for h in hits]

    monkeypatch.setattr(es_pack, "_es_query", fake_query)
    return calls


def test_es_search_returns_lemma_shape(monkeypatch):
    calls = _fake_query(monkeypatch, [
        _hit("casa", meanings=("house",), infl=("casas",)),
        _hit("casar", meanings=("to marry",), infl=("casas",), pos="verb"),
    ])
    r = client.get("/es/search", params={"q": "house"})
    assert r.status_code == 200
    body = r.json()
    assert [x["reading"] for x in body["results"]] == ["casa", "casar"]
    assert body["results"][0]["meanings"] == ["house"]
    # POS lives per-sense (the schema's canonical place — the old entry-level
    # pos union was deliberately removed); the es pack fills it the same way.
    assert body["results"][0]["senses"][0]["pos"] == ["noun"]
    assert body["results"][0]["ruby"] == []  # no furigana in an alphabetic language
    assert body["mode"] == "es"
    # the pack searched the normalised query with the requested count
    assert calls == [("house", 10)]


def test_es_search_exact_inflection_reaches_the_filter(monkeypatch):
    calls = _fake_query(monkeypatch, [_hit("hablar", meanings=("to talk",), pos="verb")])
    r = client.get("/es/search", params={"q": "  Hablas  "})
    assert r.status_code == 200
    assert r.json()["results"][0]["reading"] == "hablar"
    # normalised (trimmed + lowercased) before the query
    assert calls[0][0] == "hablas"


def test_es_search_too_long_is_flagged_not_embedded(monkeypatch):
    calls = _fake_query(monkeypatch, [])
    r = client.get("/es/search", params={"q": "x" * 500})
    assert r.status_code == 200
    assert r.json()["meta"]["too_long"] == es_pack.MAX_QUERY_CHARS
    assert calls == []  # rejected before any model/DB work


def test_es_exact_filter_covers_both_directions():
    f = es_pack.es_exact_filter("hablas")
    keys = [c.key for c in f.should]
    assert keys == ["reading", "infl_forms", "gloss_keys"]
    assert all(c.match.value == "hablas" for c in f.should)


def test_es_ready_503_when_collection_missing(monkeypatch):
    class _Boom:
        def count(self, *a, **k):
            raise ConnectionError("cluster asleep")

    monkeypatch.setattr(api, "qdrant_client", lambda: _Boom())
    r = client.get("/es/ready")
    assert r.status_code == 503
    assert r.json() == {"detail": "Spanish dictionary unavailable"}


def test_es_ready_200_when_populated(monkeypatch):
    class _Count:
        count = 147762

    class _Client:
        def count(self, *a, **k):
            return _Count()

    monkeypatch.setattr(api, "qdrant_client", lambda: _Client())
    r = client.get("/es/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "collection": "es_words", "entries": 147762, "llm": api.LLM_MODEL}
