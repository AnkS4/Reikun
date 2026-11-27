"""Hermetic tests for the official Tatoeba export join and lemma matcher."""

import bz2

from scripts.build_tatoeba_es import attach_tatoeba_examples


def _write(path, rows: list[str]) -> None:
    with bz2.open(path, "wt", encoding="utf-8") as stream:
        stream.write("\n".join(rows) + "\n")


def test_attaches_linked_tatoeba_pair_with_both_authors_and_source_ids(tmp_path):
    _write(tmp_path / "spa-eng_links.tsv.bz2", ["101\t201", "101\t201"])
    _write(tmp_path / "spa_sentences_detailed.tsv.bz2", [
        "101\tspa\tHablo con mi amigo todos los días.\tspanish_writer\t\\N\t2026-01-01",
    ])
    _write(tmp_path / "eng_sentences_detailed.tsv.bz2", [
        "201\teng\tI talk with my friend every day.\tenglish_writer\t\\N\t2026-01-01",
    ])
    chunks = [
        {"id": 1, "reading": "hablar", "pos": "verb", "wf_score": 5.4, "infl_forms": ["hablo"]},
        {"id": 2, "reading": "amigo", "pos": "noun", "wf_score": 4.7, "infl_forms": ["amigos"]},
        # Function words are intentionally not example-indexed.
        {"id": 3, "reading": "con", "pos": "prep", "wf_score": 7.0, "infl_forms": []},
    ]

    count = attach_tatoeba_examples(chunks, tmp_path)

    assert count == 2
    hablar, amigo, con = chunks
    assert hablar["examples_es"] == [{
        "spanish": "Hablo con mi amigo todos los días.",
        "english": "I talk with my friend every day.",
        "spanish_id": 101,
        "english_id": 201,
        "spanish_author": "spanish_writer",
        "english_author": "english_writer",
        "license": "CC BY 2.0 FR",
    }]
    assert amigo["examples_es"][0]["spanish_id"] == 101
    assert "examples_es" not in con
