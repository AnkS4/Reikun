"""Unit tests for the JMdict entity-code classification maps in
scripts/build_chunks.py — POS_TAG_MAP / MISC_TAG_MAP coverage, tag ordering,
and the resolved-text → code lookup. Offline; reads only the XML DOCTYPE
head, never the full document."""

import xml.etree.ElementTree as ET

from scripts.build_chunks import (
    _MISC_ORDER,
    _MISC_TAG_MAP,
    _POS_ORDER,
    _POS_TAG_MAP,
    _coded_tags,
    _entity_code,
    _entry_to_chunk,
)


def test_pos_map_covers_all_tag_groups() -> None:
    assert set(_POS_TAG_MAP.values()) <= set(_POS_ORDER)
    # The 2026-11-13 census: 83 occurring codes + 5 DTD no-ops
    # (adj-kari, v5uru, n-adv, n-t, n-pr).
    assert len(_POS_TAG_MAP) == 92
    for tag in _POS_ORDER:
        assert tag in _POS_TAG_MAP.values()


def test_misc_map_covers_all_tag_groups() -> None:
    assert set(_MISC_TAG_MAP.values()) <= set(_MISC_ORDER)
    # 52 occurring codes + 3 DTD no-ops (oth, X, station).
    assert len(_MISC_TAG_MAP) == 55
    for tag in _MISC_ORDER:
        assert tag in _MISC_TAG_MAP.values()


def test_entity_code_roundtrip() -> None:
    # Resolved JMdict entity texts map back to their codes.
    assert _entity_code("noun (common) (futsuumeishi)") == "n"
    assert _entity_code("Godan verb with 'ru' ending") == "v5r"
    assert _entity_code("adjectival nouns or quasi-adjectives (keiyodoshi)") == "adj-na"
    assert _entity_code("onomatopoeic or mimetic word") == "on-mim"
    assert _entity_code("word usually written using kana alone") == "uk"
    assert _entity_code("Kansai-ben") == "ksb"
    assert _entity_code("computing") == "comp"
    assert _entity_code("search-only kanji form") == "sK"
    assert _entity_code("not an entity") is None
    assert _entity_code(None) is None


def test_coded_tags_priority_order() -> None:
    # adj-na + noun must badge the adjective, not flatten into "noun".
    tags = _coded_tags(
        ["adjectival nouns or quasi-adjectives (keiyodoshi)",
         "noun (common) (futsuumeishi)"],
        _POS_TAG_MAP, _POS_ORDER)
    assert tags == ["adj-na", "noun"]
    # Tier-1 misc labels precede tier-2 register/name tags.
    tags = _coded_tags(
        ["archaic", "onomatopoeic or mimetic word", "organization name"],
        _MISC_TAG_MAP, _MISC_ORDER)
    assert tags == ["on-mim", "archaic", "name"]
    # Unmapped texts are dropped, not guessed.
    assert _coded_tags(["plain English text"], _POS_TAG_MAP, _POS_ORDER) == []


def _entry(xml: str) -> ET.Element:
    return ET.fromstring(xml)


def test_entry_to_chunk_phase2_fields() -> None:
    entry = _entry("""
    <entry>
      <ent_seq>999999999</ent_seq>
      <k_ele><keb>試験</keb><ke_inf>search-only kanji form</ke_inf></k_ele>
      <r_ele><reb>しけん</reb></r_ele>
      <sense>
        <pos>noun (common) (futsuumeishi)</pos>
        <pos>Godan verb with 'ru' ending</pos>
        <misc>word usually written using kana alone</misc>
        <dial>Kansai-ben</dial>
        <field>computing</field>
        <s_inf>sometimes used for zero</s_inf>
        <xref type="ant" seq="123">反対</xref>
        <gloss>exam</gloss>
      </sense>
      <sense>
        <pos>adverb (fukushi)</pos>
        <misc>archaic</misc>
        <gloss>trial</gloss>
      </sense>
    </entry>""")
    chunk = _entry_to_chunk(entry)
    assert chunk is not None
    senses = chunk["senses"]
    assert len(senses) == 2
    s0, s1 = senses
    # Per-sense tags keep badge order within the sense, not an entry union.
    assert s0["pos"] == ["verb", "noun"]
    assert s0["misc"] == ["kana"]
    assert s0["field"] == ["computing"]
    assert s0["dial"] == [{"code": "ksb", "name": "Kansai-ben"}]
    assert s0["s_inf"] == ["sometimes used for zero"]
    assert s0["xrefs"] == [{"seq": "123", "text": "反対", "type": "ant"}]
    assert s0["glosses"] == ["exam"]
    # Sense boundaries survive: the adverb/archaic tags stay on sense 2.
    assert s1["pos"] == ["adv"]
    assert s1["misc"] == ["archaic"]
    assert s1["glosses"] == ["trial"]
    assert "xrefs" not in s1
    # Entry-level display unions are gone — senses are canonical.
    for flat in ("pos", "misc", "field_tags", "dial", "s_inf", "xrefs"):
        assert flat not in chunk
    assert chunk["ke_inf"] == {"試験": ["sK"]}
    assert "related" not in chunk


def test_entry_to_chunk_lsource_attrs() -> None:
    entry = _entry("""
    <entry>
      <ent_seq>999999998</ent_seq>
      <k_ele><keb>テスト</keb></k_ele>
      <r_ele><reb>テスト</reb></r_ele>
      <lsource xml:lang="eng" ls_type="part" ls_wasei="y">test</lsource>
      <sense><pos>noun (common) (futsuumeishi)</pos><gloss>test</gloss></sense>
    </entry>""")
    chunk = _entry_to_chunk(entry)
    assert chunk is not None
    assert chunk["lsource"] == [
        {"lang": "eng", "text": "test", "type": "part", "wasei": True}]
