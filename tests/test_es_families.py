"""Etymology-link families: the offline build and the read-only API."""

from __future__ import annotations

import gzip
import json

from fastapi.testclient import TestClient

from app.api import app
from scripts.build_es_families import build


def _entry(word: str, *ancestors: str) -> dict:
    return {
        "lang_code": "es",
        "word": word,
        "senses": [{"glosses": [f"a Spanish word: {word}"]}],
        "etymology_links": [[ancestor, f"{ancestor}#Español"] for ancestor in ancestors],
    }


def test_build_groups_descendants_by_ancestor(tmp_path) -> None:
    source = tmp_path / "extract.jsonl.gz"
    with gzip.open(source, "wt", encoding="utf-8") as handle:
        for entry in (
            _entry("matar"),
            _entry("matador", "matar"),
            _entry("matabuey", "matar"),
            _entry("matacaballo", "matar"),
            _entry("panadero", "pan"),
            _entry("panadería", "pan"),
            _entry("panera", "pan"),
            {"lang_code": "en", "word": "other", "etymology_links": [["matar", "matar#Español"]]},
        ):
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    chunks = tmp_path / "chunks.json"
    chunks.write_text(
        json.dumps(
            [{"reading": word} for word in
             ("matar", "matador", "matabuey", "matacaballo", "pan", "panadero", "panadería", "panera")],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    families = build(source, chunks, limit=10, min_members=3, max_members=10)
    assert [family["word"] for family in families] == ["matar", "pan"]
    assert [member["word"] for member in families[0]["members"]] == ["matabuey", "matacaballo", "matador"]
    assert families[0]["members"][0]["gloss"].startswith("a Spanish word")


def test_es_families_endpoint_serves_the_built_index() -> None:
    r = TestClient(app).get("/es/families")
    assert r.status_code == 200
    families = r.json()["families"]
    assert len(families) > 20
    assert all(family["word"] and len(family["members"]) >= 4 for family in families)
    assert all(member["word"] for family in families for member in family["members"])
