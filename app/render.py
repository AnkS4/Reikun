"""
Frontend-ready JSON shaping — the API-side counterpart of app/ui/common.py's
HTML rendering. Everything here is plain data (no markup): the SvelteKit
frontend renders <ruby>, chips, badges and stroke SVGs from these structures.

Deliberately dependency-light (kanji_lookup + config only) so it is importable
in the lean API image — no Streamlit, no pandas.
"""

from app.kanji_lookup import has_kanji, is_kanji, lookup_kanji, stroke_data


def furigana_parts(word: str, reading: str | None) -> list[dict]:
    """
    `word` + its `reading` → display parts for <ruby> rendering.

    Returns [{"text": …, "rt": …}, …]; `rt` is None for segments rendered
    without furigana. Kana shared at the start/end of both strings (okurigana,
    honorific お…) stay outside the ruby so 食べる/たべる splits as
    食[た]べる — same trim as ui/common.py's furigana(), which wraps these
    parts in HTML.
    """
    if not reading or reading == word or not has_kanji(word):
        return [{"text": word, "rt": None}]
    i = 0
    while i < min(len(word), len(reading)) and word[i] == reading[i] and not is_kanji(word[i]):
        i += 1
    j = 0
    while j < min(len(word), len(reading)) - i and word[-1 - j] == reading[-1 - j] and not is_kanji(word[-1 - j]):
        j += 1
    core_w, core_r = word[i:len(word) - j], reading[i:len(reading) - j]
    if not core_w or not core_r:
        return [{"text": word, "rt": reading}]
    parts = [{"text": core_w, "rt": core_r}]
    if j:
        parts.append({"text": word[len(word) - j:], "rt": None})
    if i:
        parts.insert(0, {"text": word[:i], "rt": None})
    return parts


def _grade_badge(grade: int) -> dict:
    """{label, tip} for a KANJIDIC2 grade code — 1-6 kyōiku (primary school
    year), 8 jōyō (secondary school, general use), 9-10 jinmeiyō (names)."""
    if grade <= 6:
        tip = f"Kyōiku kanji — general-use characters taught in year {grade} of primary school"
    elif grade == 8:
        tip = "Jōyō kanji — one of the 2,136 general-use characters, taught in secondary school"
    else:
        tip = ("Jinmeiyō kanji — characters approved for use in personal names"
               + ("; variant form of a jōyō kanji" if grade == 10 else ""))
    return {"label": f"Grade {grade}", "tip": tip}


def meta_parts(d: dict) -> list[dict]:
    """[{label, tip}] badges for a kanji's strokes / grade / JLPT / frequency
    rank, skipping fields the entry lacks."""
    parts = []
    if d.get("stroke_count"):
        parts.append({"label": f"{d['stroke_count']} strokes",
                      "tip": "Number of strokes in the standard stroke order"})
    if d.get("grade"):
        parts.append(_grade_badge(d["grade"]))
    if d.get("jlpt_level"):
        # kanji_table stores KANJIDIC2's former 4-level scale (4 elementary →
        # 1 advanced); old level 2 spans N2-N3 so it can't be shown as one level.
        label = {4: "N5", 3: "N4", 2: "N2-N3", 1: "N1"}.get(d["jlpt_level"], f"N{d['jlpt_level']}")
        parts.append({"label": f"JLPT {label}",
                      "tip": "Japanese Language Proficiency Test level this kanji is expected at "
                             "(N5 easiest, N1 hardest)"})
    if d.get("freq"):
        parts.append({"label": f"Freq #{d['freq']}",
                      "tip": "Frequency rank among the 2,500 most-used kanji in newspapers (1 = most common)"})
    return parts


def reading_chip(reading: str) -> dict:
    """One on/kun reading → {stem, okurigana}. KANJIDIC2 kun'yomi mark the
    okurigana part with a dot (た.べる) — the frontend renders it muted."""
    stem, dot, oku = reading.partition(".")
    return {"stem": stem, "okurigana": oku if dot else None}


def _word_json(word: dict) -> dict:
    """One 'common word' entry → display JSON (headword, ruby parts, first gloss)."""
    head = word.get("kanji_form") or word.get("reading") or ""
    return {
        "kanji_form": word.get("kanji_form"),
        "reading": word.get("reading") or "",
        "meanings": word.get("meanings") or [],
        "gloss": (word.get("meanings") or [""])[0],
        "ruby": furigana_parts(head, word.get("reading")),
    }


def kanji_card(char: str, *, strokes: bool = False) -> dict | None:
    """
    Full kanji-card JSON for /kanji/{char}, or None when KANJIDIC2 has no entry.

    Beyond the raw table fields (literal, codepoint_hex, meanings, on_yomi,
    kun_yomi, stroke_count, grade, freq, jlpt_level) this adds the pieces the
    Streamlit card used to compose in HTML: meta badges, readings split into
    stem/okurigana, common words (kanji-itself word first) with ruby parts,
    and — with strokes=True — the KanjiVG stroke data as structured JSON.
    """
    d = lookup_kanji(char)
    if not d:
        return None
    # JMdict order is roughly by reading, so the word that *is* this kanji can
    # land anywhere — pull it to the top; the rest keep their order.
    words = sorted((d.get("common_words") or ())[:8], key=lambda w: w.get("kanji_form") != char)
    on_yomi = d.get("on_yomi") or []
    kun_yomi = d.get("kun_yomi") or []
    card = {
        "literal": d.get("literal"),
        "codepoint_hex": d.get("codepoint_hex"),
        "stroke_count": d.get("stroke_count"),
        "grade": d.get("grade"),
        "freq": d.get("freq"),
        "jlpt_level": d.get("jlpt_level"),
        "meanings": d.get("meanings") or [],
        "meta": meta_parts(d),
        "on_yomi": on_yomi,
        "kun_yomi": kun_yomi,
        "readings": {
            "on": [reading_chip(r) for r in on_yomi],
            "kun": [reading_chip(r) for r in kun_yomi],
        },
        "common_words": [_word_json(w) for w in words],
    }
    if strokes:
        card["stroke"] = stroke_data(char)
    return card


def kanji_hover(char: str) -> dict | None:
    """Compact hover-card JSON for /kanji batch lookups: top meanings, a few
    readings, and the meta line — or None for kanji KANJIDIC2 doesn't know."""
    d = lookup_kanji(char)
    if not d:
        return None
    return {
        "literal": char,
        "meanings": (d.get("meanings") or [])[:6],
        "on_yomi": (d.get("on_yomi") or [])[:4],
        "kun_yomi": (d.get("kun_yomi") or [])[:4],
        "meta": meta_parts(d),
    }


def chip_ruby(text: str, reading: str) -> list[dict]:
    """Ruby parts for a sentence-segment chip.

    An all-kana segment whose reading differs from its surface (は→わ, へ→え)
    still gets whole-word furigana — furigana_parts() alone would skip it
    (it only rubies kanji)."""
    if reading and reading != text and not has_kanji(text):
        return [{"text": text, "rt": reading}]
    return furigana_parts(text, reading)


def segment_chip(seg: dict) -> dict:
    """One segment_japanese() part → the chip JSON the frontend renders:
    text + ruby parts, a two-gloss summary, hover detail (options), and the
    approx flag marking fallback-segmenter guesses."""
    return {
        "text": seg["text"],
        "kanji_form": seg.get("kanji_form"),
        "reading": seg.get("reading") or "",
        "meanings": seg.get("meanings") or [],
        "gloss": "; ".join((seg.get("meanings") or [])[:2]),
        "ruby": chip_ruby(seg["text"], seg.get("reading") or ""),
        "options": seg.get("options") or [],
        "approx": bool(seg.get("approx")),
    }
