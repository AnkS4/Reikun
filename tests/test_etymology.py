"""Unit tests for app.etymology (lsource display enrichment) and
app.loanwords (the in-process borrowed-words index) — no Qdrant needed:
the index's scroll is replaced by a fixture through monkeypatching."""

import app.etymology as etym
import app.loanwords as loanwords


def test_enrich_lsource_label_and_tag() -> None:
    out = etym.enrich_lsource([{"lang": "spa", "text": "espada"}])
    assert out == [{
        "lang": "spa", "text": "espada",
        "label": "From Spanish", "tag": "es",
    }]


def test_enrich_lsource_bibliographic_codes_map_to_alpha2() -> None:
    # JMdict's ISO-639-2/B codes (fre/ger/dut/chi/gre) → BCP-47 tags.
    tags = {s["lang"]: s["tag"] for s in etym.enrich_lsource(
        [{"lang": c, "text": ""} for c in ("fre", "ger", "dut", "chi", "gre")]
    )}
    assert tags == {"fre": "fr", "ger": "de", "dut": "nl", "chi": "zh", "gre": "el"}


def test_enrich_lsource_no_text_branch() -> None:
    # Many sources carry no form (エルニーニョ ← spa): label alone, no tag use.
    out = etym.enrich_lsource([{"lang": "hin", "text": ""}])
    assert out[0]["label"] == "From Hindi" and out[0]["text"] == ""


def test_enrich_lsource_unknown_code_falls_back() -> None:
    out = etym.enrich_lsource([{"lang": "zzz", "text": "x"}])
    assert out[0]["label"] == "From zzz" and out[0]["tag"] == "zzz"  # ISO-639-3-shaped → usable tag
    out = etym.enrich_lsource([{"lang": "", "text": ""}])
    assert out[0]["label"] == "From " and out[0]["tag"] is None


def test_enrich_lsource_phase2_fields() -> None:
    # ls_type="part" / ls_wasei arrive with the Phase-2 payload — honoured now.
    part = etym.enrich_lsource([{"lang": "eng", "text": "", "type": "part"}])
    assert part[0]["label"] == "Partly from English"
    wasei = etym.enrich_lsource([{"lang": "eng", "text": "", "wasei": "eng"}])
    assert wasei[0]["label"] == "Wasei-eigo (Japanese-made English)"


def test_enrich_lsource_empty() -> None:
    assert etym.enrich_lsource(None) == [] and etym.enrich_lsource([]) == []


def test_enrich_lsource_is_idempotent() -> None:
    # The loanwords index enriches at build time and lite cards enrich again
    # at render — phase-2 fields must survive the second pass or "Wasei-eigo"
    # degrades to a plain "From English".
    once = etym.enrich_lsource([{"lang": "eng", "text": "", "wasei": "eng"}])
    twice = etym.enrich_lsource(once)
    assert twice[0]["label"] == "Wasei-eigo (Japanese-made English)"
    part = etym.enrich_lsource([{"lang": "eng", "text": "x", "type": "part"}])
    assert etym.enrich_lsource(part)[0]["label"] == "Partly from English"


def test_lang_names_iso639_2() -> None:
    # kir is Kyrgyz (Gilbertese is gil); bnt is the Bantu collective.
    assert etym.lang_name("kir") == "Kyrgyz"
    assert etym.LANG_TAGS["kir"] == "ky"
    assert etym.lang_name("bnt") == "Bantu"


def _fixture_index() -> dict[str, list[dict]]:
    def entry(eid: int, form: str, wf: float, lang: str) -> dict:
        return {
            "id": eid, "kanji_form": form, "reading": "よみ",
            "kanji_forms": [], "readings": [], "meanings": ["gloss"],
            "example_sentences": [], "is_common": True, "text": "t",
            "inflected_forms": [], "inflection": None, "score": wf,
            "lsource": [{"lang": lang, "text": "", "label": f"From {lang}", "tag": lang}],
            "reading_restrictions": {},
        }
    return {
        "eng": [entry(1, "コンピュータ", 5.0, "eng"), entry(2, "スマホ", 4.0, "eng")],
        "spa": [entry(3, "タバコ", 3.0, "spa")],
        # pseudo-bucket: must be hidden from the facet grid, still listable
        "wasei": [entry(4, "サラリーマン", 2.0, "eng"), entry(1, "コンピュータ", 5.0, "eng")],
    }


def test_loanword_facets_sorted_by_count(monkeypatch) -> None:
    monkeypatch.setattr(loanwords, "_loanwords", _fixture_index)
    facets = loanwords.loanword_facets()
    assert [(f["lang"], f["count"]) for f in facets] == [("eng", 2), ("spa", 1)]
    assert facets[0]["name"] == "English"


def test_wasei_pseudo_bucket_listable_but_not_a_facet(monkeypatch) -> None:
    monkeypatch.setattr(loanwords, "_loanwords", _fixture_index)
    facets = loanwords.loanword_facets()
    assert "wasei" not in [f["lang"] for f in facets]
    page = loanwords.loanwords_page("wasei", offset=0, limit=10)
    assert page is not None and page["total"] == 2
    assert "サラリーマン" in [r["kanji_form"] for r in page["results"]]


def test_loanwords_page_slices_and_404s_unknown(monkeypatch) -> None:
    monkeypatch.setattr(loanwords, "_loanwords", _fixture_index)
    page = loanwords.loanwords_page("eng", offset=1, limit=10)
    assert page is not None and page["total"] == 2 and page["offset"] == 1
    assert [r["kanji_form"] for r in page["results"]] == ["スマホ"]
    assert loanwords.loanwords_page("zzz") is None
