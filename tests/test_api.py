"""API smoke tests runnable without Qdrant/Groq.

Everything exercised here is backed by committed data
(data/processed/kanji_table.json + headword_index.marisa) or by request
validation alone. /search and /explain need live services and stay out of
CI scope; /ready is asserted tolerant (503 when Qdrant is absent — a dev
machine with a local Qdrant sees 200 instead).
"""

from fastapi.testclient import TestClient

from app.api import app

# Plain instantiation — no `with`, so the lifespan never runs and the
# Qdrant/embedder warm-up threads (which could only fail in CI) stay out of
# the test run; every dependency below loads lazily on first use.
client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_ready_responds() -> None:
    # 503 without Qdrant (CI), 200 if a local one happens to be up.
    assert client.get("/ready").status_code in (200, 503)


def test_kanji_card() -> None:
    r = client.get("/kanji/家")
    assert r.status_code == 200
    card = r.json()
    for key in ("meta", "readings", "common_words"):
        assert key in card
    assert card["stroke"] is None  # opt-in via ?strokes=true


def test_kanji_card_strokes_from_committed_data() -> None:
    # strokes.json is committed — no network, no data/kanjivg/ needed.
    stroke = client.get("/kanji/家", params={"strokes": "true"}).json()["stroke"]
    assert stroke["view_box"] == "0 0 109 109"
    assert len(stroke["strokes"]) == len(stroke["numbers"]) == 10
    assert [n["value"] for n in stroke["numbers"]] == list(range(1, 11))


def test_kanji_card_rejects_non_kanji() -> None:
    assert client.get("/kanji/x").status_code == 400


def test_kanji_batch() -> None:
    r = client.get("/kanji", params={"chars": "家猫"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"家", "猫"}
    assert body["家"] is not None


def test_kanji_batch_rejects_no_kanji() -> None:
    assert client.get("/kanji", params={"chars": "abc"}).status_code == 400


def test_kanji_random() -> None:
    for params in ({}, {"level": "N5"}):
        r = client.get("/kanji/random", params=params)
        assert r.status_code == 200
        assert len(r.json()["kanji"]) == 1


def test_search_requires_q() -> None:
    assert client.get("/search").status_code == 422


def test_search_validates_mode_and_count() -> None:
    assert client.get("/search", params={"q": "cat", "mode": "bogus"}).status_code == 422
    assert client.get("/search", params={"q": "cat", "n": 0}).status_code == 422
    assert client.get("/search", params={"q": "cat", "n": 51}).status_code == 422
    assert client.get("/search", params={"q": "   "}).status_code == 422


def test_search_too_long_short_circuits() -> None:
    # Over-long input is rejected before any embed/Qdrant call, so this is the
    # one /search path that runs end-to-end in CI — including response shaping.
    r = client.get("/search", params={"q": "x" * 151})
    assert r.status_code == 200
    body = r.json()
    assert body["results"] == [] and body["segments"] is None
    assert body["meta"] == {"route": None, "rewrite_ms": None, "embed_ms": None,
                            "retrieve_ms": None, "cached": False, "too_long": 150}


def test_explain_validates() -> None:
    assert client.post("/explain", json={"sentence": "", "level": "N5"}).status_code == 422
    assert client.post("/explain", json={"sentence": "猫", "level": "N9"}).status_code == 422


def test_feedback_records_and_validates() -> None:
    r = client.post("/feedback", json={"kind": "search", "rating": 1, "query": "cat"})
    assert r.status_code == 201
    assert client.post("/feedback", json={"kind": "search", "rating": 0}).status_code == 422
    assert client.post("/feedback", json={"kind": "bogus", "rating": 1}).status_code == 422
