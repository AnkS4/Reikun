"""API smoke tests runnable without Qdrant/LLM.

Everything exercised here is backed by committed data
(data/processed/kanji_table.json + headword_index.marisa) or by request
validation alone. /search and /explain need live services and stay out of
CI scope; /ready is asserted tolerant (503 when Qdrant is absent — a dev
machine with a local Qdrant sees 200 instead).
"""

from fastapi.testclient import TestClient

from app import api
from app.api import APP_VERSION, app

# Plain instantiation — no `with`, so the lifespan never runs and the
# Qdrant/embedder warm-up threads (which could only fail in CI) stay out of
# the test run; every dependency below loads lazily on first use.
client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    # version rides along for the web About page (pyproject.toml is the truth).
    assert r.status_code == 200 and r.json() == {"status": "ok", "version": APP_VERSION}


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


def test_kanji_group() -> None:
    # High stroke count kanji (>30 strokes) must not fail query validation.
    r = client.get("/kanji/group", params={"by": "strokes", "value": 33})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert any(k["literal"] in ("鱻", "麤", "龗") for k in data["kanjis"])

    # Invalid group or value out of bounds
    assert client.get("/kanji/group", params={"by": "bogus", "value": 5}).status_code == 422
    assert client.get("/kanji/group", params={"by": "strokes", "value": 0}).status_code == 422
    assert client.get("/kanji/group", params={"by": "strokes", "value": 51}).status_code == 422


def test_kanji_group_freq_ceiling() -> None:
    # by=freq accepts a cumulative top-N bound up to 3000.
    r = client.get("/kanji/group", params={"by": "freq", "value": 3000, "n": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0

    # 3001 exceeds the declared bound → 422 in the validator envelope shape.
    r = client.get("/kanji/group", params={"by": "freq", "value": 3001})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list)
    assert r.json()["detail"][0]["loc"] == ["query", "value"]

    # Non-freq groupings cap at 50 — with the validator-style envelope
    # (consistent with query-validator 422s), not the detail-string shape.
    r = client.get("/kanji/group", params={"by": "strokes", "value": 51})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list)


def test_kanji_groups_facets() -> None:
    r = client.get("/kanji/groups")
    assert r.status_code == 200
    data = r.json()
    # Stroke counts run 1-34 with no kanji at 31; jlpt is the internal 4→1 scale.
    assert [v["value"] for v in data["strokes"]] == [n for n in range(1, 35) if n != 31]
    assert [v["value"] for v in data["jlpt"]] == [4, 3, 2, 1]
    # Frequency bands are cumulative top-N counts across the ranked set.
    assert [v["value"] for v in data["freq"]] == [100, 250, 500, 1000, 1500, 2000, 2500]
    assert [v["count"] for v in data["freq"]] == [100, 250, 500, 1000, 1500, 2000, 2500]
    assert all(v["count"] > 0 for group in data.values() for v in group)


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
                            "retrieve_ms": None, "segment_ms": None,
                            "cached": False, "too_long": 150}


def test_search_result_sense_fields() -> None:
    # Per-sense structure is the public schema — glosses with their own
    # pos/misc/dial badges, s_inf notes, typed xrefs (seq/sno deep-link
    # pointers), form restrictions and examples. The old entry-level
    # pos/misc/xrefs/dial unions are gone.
    fields = api.SearchResult.model_fields
    assert "senses" in fields
    for gone in ("pos", "misc", "xrefs", "dial"):
        assert gone not in fields, gone
    sense_fields = api.SenseResult.model_fields
    for name in ("glosses", "pos", "misc", "field", "dial", "s_inf",
                 "xrefs", "stagk", "stagr", "examples"):
        assert name in sense_fields, name
    xref = api.Xref(seq="1", sno="2", text="お店", type="see")
    assert xref.sno == "2"
    # Variant-forms block: per-keb reading bindings + ke_inf labels +
    # kana-only readings; None when the entry has neither.
    assert "variants" in fields
    variant_fields = api.Variants.model_fields
    for name in ("forms", "readings", "kana_only"):
        assert name in variant_fields, name
    form_fields = api.VariantForm.model_fields
    for name in ("form", "readings", "labels"):
        assert name in form_fields, name


def test_variant_forms_pairings() -> None:
    from app.retrieval import _variant_forms

    # re_restr: each reading binds to exactly one keb.
    out = _variant_forms({
        "kanji_forms": ["ＣＤプレーヤー", "ＣＤプレイヤー"],
        "readings": ["シーディープレーヤー", "シーディープレイヤー"],
        "reading_restrictions": {
            "シーディープレーヤー": ["ＣＤプレーヤー"],
            "シーディープレイヤー": ["ＣＤプレイヤー"],
        },
        "ke_inf": {},
    })
    assert out is not None
    assert out["forms"][0]["readings"] == ["シーディープレーヤー"]
    assert out["forms"][1]["readings"] == ["シーディープレイヤー"]
    assert out["readings"] == [] and out["kana_only"] == []

    # re_nokanji: the katakana reading applies to no written form; the
    # hiragana one is unrestricted and lands in the shared readings line.
    out = _variant_forms({
        "kanji_forms": ["梔子", "巵子", "山梔子", "梔"],
        "readings": ["くちなし", "クチナシ", "しし", "さんしし"],
        "reading_restrictions": {
            "クチナシ": [], "しし": ["梔子", "巵子"], "さんしし": ["山梔子"],
        },
        "ke_inf": {},
    })
    assert out is not None
    assert out["kana_only"] == ["クチナシ"]
    assert out["readings"] == ["くちなし"]  # unrestricted only
    assert out["forms"][0]["readings"] == ["しし"]
    assert out["forms"][2]["readings"] == ["さんしし"]
    assert out["forms"][3]["readings"] == []

    # ke_inf labels ride along per form; unrestricted readings = all.
    out = _variant_forms({
        "kanji_forms": ["明白", "偸閑"],
        "readings": ["あからさま"],
        "reading_restrictions": {},
        "ke_inf": {"明白": ["ateji", "rK"], "偸閑": ["ateji", "rK"]},
    })
    assert out is not None
    assert out["forms"][0]["labels"] == ["ateji", "rK"]
    assert out["readings"] == ["あからさま"]

    # No restrictions and no labels → no block (plain alternates).
    assert _variant_forms({
        "kanji_forms": ["犬"], "readings": ["いぬ"],
        "reading_restrictions": {}, "ke_inf": {},
    }) is None


def test_explain_validates() -> None:
    assert client.post("/explain", json={"sentence": "", "level": "N5"}).status_code == 422
    assert client.post("/explain", json={"sentence": "猫", "level": "N9"}).status_code == 422
    # Transport cap rejects oversized bodies before the handler/LLM sees them
    # (the 200-char rule is enforced later, on whitespace-normalised text).
    assert client.post("/explain", json={"sentence": "猫" * 1601}).status_code == 422
    assert client.post("/explain", json={"sentence": "猫", "english": "x" * 3201}).status_code == 422


def test_feedback_records_and_validates() -> None:
    r = client.post("/feedback", json={"kind": "search", "rating": 1, "query": "cat"})
    assert r.status_code == 201
    assert client.post("/feedback", json={"kind": "search", "rating": 0}).status_code == 422
    assert client.post("/feedback", json={"kind": "bogus", "rating": 1}).status_code == 422
    assert client.post("/feedback", json={"kind": "search", "rating": 1, "query": "x" * 513}).status_code == 422


def test_cache_headers() -> None:
    # Liveness must never be cached; static kanji hover data may be.
    assert client.get("/health").headers["cache-control"] == "no-store"
    batch = client.get("/kanji", params={"chars": "家"})
    assert batch.headers["cache-control"].startswith("public")


def test_loanwords_page_does_not_mutate_shared_index(monkeypatch) -> None:
    # loanwords_page slices the shared TTL index — the endpoint must copy
    # before attaching ruby/related, or per-request keys race readers and
    # permanently bloat the cache.
    shared = {
        "id": 1, "kanji_form": "パン", "reading": "ぱん",
        "kanji_forms": [], "readings": [], "meanings": ["bread"],
        "example_sentences": [], "is_common": True, "text": "",
        "inflected_forms": [], "lsource": [], "reading_restrictions": {},
        "ke_inf": {}, "senses": [], "score": 1.0,
    }
    page = {"lang": "por", "name": "Portuguese", "total": 1, "offset": 0,
            "results": [shared]}
    monkeypatch.setattr(api, "loanwords_page", lambda *a, **k: page)
    r = client.get("/loanwords/por")
    assert r.status_code == 200
    assert "ruby" not in shared and "related" not in shared
    shaped = r.json()["results"][0]
    assert shaped["ruby"] and shaped["related"] is not None
