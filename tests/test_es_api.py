"""Spanish pack (es_words) tests — hermetic: the Qdrant calls are faked, so
CI runs these without a cluster. The collection-integration itself is
verified by hand against the local Docker Qdrant (M0 exit tests)."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import api
from app.lang import es as es_pack
from scripts import build_chunks_es

client = TestClient(api.app)


def _hit(word: str, *, meanings=("house",), infl=(), pos="noun", score=1.0):
    """Shape a qdrant hit the way _hit_to_dict reads it."""
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
    """Fake at the qdrant seam: the raw hits flow through _es_hit_to_dict like
    the real _es_query does."""
    calls = []

    def fake_query(query, num_results, vectors=None):
        calls.append((query, num_results))
        return [es_pack._es_hit_to_dict(h) for h in hits]

    monkeypatch.setattr(es_pack, "_es_query", fake_query)
    return calls


def test_es_search_returns_lemma_shape(monkeypatch):
    casa = _hit("casa", meanings=("house",), infl=("casas",))
    casa.payload.update(
        definitions_es=["Edificación destinada a vivienda."],
        etymology_es=["Del latín casa."],
        origin_languages=["latín"],
    )
    calls = _fake_query(monkeypatch, [
        casa,
        _hit("casar", meanings=("to marry",), infl=("casas",), pos="verb"),
    ])
    r = client.get("/es/search", params={"q": "house"})
    assert r.status_code == 200
    body = r.json()
    assert [x["reading"] for x in body["results"]] == ["casa", "casar"]
    assert body["results"][0]["meanings"] == ["house"]
    assert body["results"][0]["definitions_es"] == ["Edificación destinada a vivienda."]
    assert body["results"][0]["etymology_es"] == ["Del latín casa."]
    assert body["results"][0]["origin_languages"] == ["latín"]
    assert body["results"][1]["etymology_es"] == []
    # POS lives per-sense (the schema's canonical place — the old entry-level
    # pos union was deliberately removed); the es pack fills it the same way.
    assert body["results"][0]["senses"][0]["pos"] == ["noun"]
    assert body["results"][0]["ruby"] == []  # no furigana in an alphabetic language
    assert body["mode"] == "es"
    # the pack searched the normalised query with the requested count
    assert calls == [("house", 10)]


def test_es_builder_preserves_compound_forms_and_late_supplements():
    chunk = build_chunks_es._chunk({
        "word": "hablar",
        "pos": "verb",
        "forms": [
            {"form": "habré hablado", "tags": ["indicative", "future", "compound"]},
            {"form": "haya hablado", "tags": ["subjunctive", "present", "perfect"]},
        ],
        "etymology_texts": ["Del castellano antiguo fablar."],
        "categories": ["ES:Palabras provenientes del castellano antiguo", "ES:Verbos"],
    })
    build_chunks_es._merge_en(chunk, {
        "forms": [
            {"form": "es-conj", "tags": ["inflection-template"]},
            *[{"form": "-", "tags": ["combined-form", "imperative"]}] * 200,
            {"form": "hablar", "tags": ["infinitive"]},
            {"form": "hablándome", "tags": ["combined-form", "gerund"]},
        ],
    })
    assert [row["surface"] for row in chunk["inflected_forms"]] == [
        "habré hablado", "haya hablado", "hablar", "hablándome",
    ]
    assert chunk["infl_forms"] == ["hablándome", "habré hablado", "haya hablado"]
    assert chunk["origin_languages"] == ["castellano antiguo"]
    assert chunk["etymology_es"] == ["Del castellano antiguo fablar."]


def test_es_etymology_filters_and_counts_use_es_collection(monkeypatch):
    class _Client:
        def facet(self, collection, field, *, limit, exact):
            assert (collection, field, exact) == (es_pack.ES_COLLECTION, "origin_languages", True)
            return SimpleNamespace(hits=[SimpleNamespace(value="árabe", count=21)])

        def count(self, collection, *, count_filter, exact):
            assert collection == es_pack.ES_COLLECTION and exact
            condition = count_filter.must[0]
            assert condition.key == "origin_languages"
            return SimpleNamespace(count=21 if condition.match.value == "árabe" else 0)

        def query_points(self, collection, *, query_filter, limit, offset, query):
            assert collection == es_pack.ES_COLLECTION
            assert query_filter.must[0].match.value == "árabe"
            assert (limit, offset, query.order_by.key) == (20, 20, "wf_score")
            return SimpleNamespace(points=[_hit("aceite")])

    monkeypatch.setattr(es_pack, "qdrant_client", _Client)
    facets = client.get("/es/etymology")
    assert facets.status_code == 200
    assert facets.json()["sources"] == [{"lang": "árabe", "name": "Árabe", "count": 21}]
    listing = client.get("/es/etymology/entries", params={"lang": "árabe", "n": 20, "offset": 20})
    assert listing.status_code == 200
    assert listing.json()["results"][0]["reading"] == "aceite"
    assert client.get("/es/etymology/entries", params={"lang": "unknown"}).status_code == 404


def test_es_conjugations_prefers_headword_before_exact_inflection(monkeypatch):
    calls = []
    row = {"form": "indicative future compound", "surface": "habré hablado"}

    class _Client:
        def query_points(self, collection, *, query_filter, **kwargs):
            condition = query_filter.must[0]
            assert collection == es_pack.ES_COLLECTION
            calls.append(condition.key)
            matches = (
                (condition.key == "reading" and "hablar" in condition.match.any)
                or (condition.key == "infl_forms" and "hablas" in condition.match.any)
            )
            points = [SimpleNamespace(payload={"reading": "hablar", "inflected_forms": [row]})] if matches else []
            return SimpleNamespace(points=points)

    monkeypatch.setattr(es_pack, "qdrant_client", _Client)
    exact = client.get("/es/conjugations", params={"word": "HABLAR"})
    assert exact.status_code == 200 and exact.json()["word"] == "hablar"
    assert calls == ["reading"]
    calls.clear()
    inflected = client.get("/es/conjugations", params={"word": "hablas"})
    assert inflected.status_code == 200
    assert inflected.json()["inflected_forms"][0]["surface"] == row["surface"]
    assert calls == ["reading", "infl_forms"]
    assert client.get("/es/conjugations", params={"word": "aceite"}).status_code == 404


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


def test_es_exact_filters_cover_both_directions():
    word_f = es_pack.es_word_filter("hablas")
    assert [c.key for c in word_f.should] == ["reading", "infl_forms"]
    assert all(c.match.value == "hablas" for c in word_f.should)

    gloss_f = es_pack.es_gloss_filter("house")
    assert [c.key for c in gloss_f.should] == ["primary_gloss_keys"]
    assert gloss_f.should[0].match.value == "house"


def test_es_language_route_uses_relative_frequency():
    # wordfreq's es corpus carries English loans, so "house" has a high es
    # zipf — only the en-vs-es comparison routes it correctly.
    assert es_pack._looks_spanish("casa")
    assert es_pack._looks_spanish("casa grande")
    assert es_pack._looks_spanish("hablas")
    assert not es_pack._looks_spanish("house")
    assert not es_pack._looks_spanish("big house")
    assert not es_pack._looks_spanish("to speak")


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
