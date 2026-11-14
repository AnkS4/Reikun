"""Etymology display data for JMdict ``lsource`` payloads.

``lsource`` entries arrive as ``{"lang": <JMdict code>, "text": <form>}`` —
ISO-639-2/B-ish codes (fre, ger, dut…) plus ISO-639-3 tail codes. This module
is the single place that turns a code into what a reader sees:

- ``label``  — the English phrase ("From Portuguese"); deliberately NOT in the
               i18n tables, like the JMdict glosses themselves.
- ``tag``    — a BCP-47 ``lang`` attribute value for the source form, so
               screen readers and font selection treat it as its real language.
               ``None`` when the code has no usable subtag.

Phase-2 payload fields (``type``="part", ``wasei``) are honoured when present
so the labels extend without a second pass here.
"""

# JMdict lang code → English display name. Covers every code observed in the
# 2026-11-13 build (~80); unknown codes fall back to the raw code.
LANG_NAMES = {
    "afr": "Afrikaans", "ain": "Ainu", "alb": "Albanian", "alg": "Algonquian",
    "amh": "Amharic", "ara": "Arabic", "arm": "Armenian", "arn": "Mapudungun",
    "aze": "Azerbaijani", "ben": "Bengali", "bnt": "Bantu", "bre": "Breton",
    "bul": "Bulgarian", "bur": "Burmese", "chi": "Chinese", "cze": "Czech",
    "dan": "Danish", "div": "Dhivehi", "dut": "Dutch", "eng": "English",
    "epo": "Esperanto", "est": "Estonian", "fil": "Filipino", "fin": "Finnish",
    "fre": "French", "geo": "Georgian", "ger": "German", "glg": "Galician",
    "grc": "Ancient Greek", "gre": "Greek", "haw": "Hawaiian", "heb": "Hebrew",
    "hin": "Hindi", "hun": "Hungarian", "ice": "Icelandic", "ind": "Indonesian",
    "ita": "Italian", "kaz": "Kazakh", "khm": "Khmer", "kir": "Kyrgyz",
    "kor": "Korean", "kur": "Kurdish", "lao": "Lao", "lat": "Latin",
    "lit": "Lithuanian", "mal": "Malayalam", "mao": "Maori", "may": "Malay",
    "mlg": "Malagasy", "mnc": "Manchu", "mon": "Mongolian", "nep": "Nepali",
    "nor": "Norwegian", "per": "Persian", "pol": "Polish", "por": "Portuguese",
    "rum": "Romanian", "rus": "Russian", "san": "Sanskrit", "scr": "Croatian",
    "slv": "Slovenian", "smo": "Samoan", "som": "Somali", "sot": "Southern Sotho",
    "spa": "Spanish", "swa": "Swahili", "swe": "Swedish", "tah": "Tahitian",
    "tam": "Tamil", "tgk": "Tajik", "tgl": "Tagalog", "tha": "Thai",
    "tib": "Tibetan", "tuk": "Turkmen", "tur": "Turkish", "ukr": "Ukrainian",
    "urd": "Urdu", "uzb": "Uzbek", "vie": "Vietnamese", "yid": "Yiddish",
}

# JMdict code → BCP-47 language tag for the `lang` attribute. Bibliographic
# ISO-639-2 codes (fre/ger/dut…) are mapped to their alpha-2/terminologic
# equivalents; ISO-639-3 codes (ain, grc, epo…) are already valid subtags.
LANG_TAGS = {
    "afr": "af", "ain": "ain", "alb": "sq", "alg": "alg", "amh": "am",
    "ara": "ar", "arm": "hy", "arn": "arn", "aze": "az", "ben": "bn",
    "bnt": "bnt", "bre": "br", "bul": "bg", "bur": "my", "chi": "zh",
    "cze": "cs", "dan": "da", "div": "dv", "dut": "nl", "eng": "en",
    "epo": "eo", "est": "et", "fil": "fil", "fin": "fi", "fre": "fr",
    "geo": "ka", "ger": "de", "glg": "gl", "grc": "grc", "gre": "el",
    "haw": "haw", "heb": "he", "hin": "hi", "hun": "hu", "ice": "is",
    "ind": "id", "ita": "it", "kaz": "kk", "khm": "km", "kir": "ky",
    "kor": "ko", "kur": "ku", "lao": "lo", "lat": "la", "lit": "lt",
    "mal": "ml", "mao": "mi", "may": "ms", "mlg": "mg", "mnc": "mnc",
    "mon": "mn", "nep": "ne", "nor": "no", "per": "fa", "pol": "pl",
    "por": "pt", "rum": "ro", "rus": "ru", "san": "sa", "scr": "hr",
    "slv": "sl", "smo": "sm", "som": "so", "sot": "st", "spa": "es",
    "swa": "sw", "swe": "sv", "tah": "ty", "tam": "ta", "tgk": "tg",
    "tgl": "tl", "tha": "th", "tib": "bo", "tuk": "tk", "tur": "tr",
    "ukr": "uk", "urd": "ur", "uzb": "uz", "vie": "vi", "yid": "yi",
}


def lang_name(code: str) -> str:
    """English display name for a JMdict lang code; the raw code when unknown."""
    return LANG_NAMES.get(code, code)


def _label(item: dict) -> str:
    """The English etymology phrase for one lsource item."""
    if item.get("wasei"):
        return "Wasei-eigo (Japanese-made English)"
    name = lang_name(item.get("lang") or "")
    if item.get("type") == "part":
        return f"Partly from {name}"
    return f"From {name}"


def enrich_lsource(raw: list[dict] | None) -> list[dict]:
    """Payload ``lsource`` ([{lang, text}]) → display-ready dicts carrying the
    English ``label`` and BCP-47 ``tag``. Unknown/missing codes degrade to the
    raw code / no tag rather than dropping the entry."""
    out = []
    for item in raw or []:
        lang = item.get("lang") or ""
        tag = LANG_TAGS.get(lang)
        if tag is None and len(lang) == 3 and lang.isalpha():
            tag = lang  # ISO-639-3 codes are valid BCP-47 subtags
        enriched = {
            "lang": lang,
            "text": item.get("text") or "",
            "label": _label(item),
            "tag": tag,
        }
        # Pass the phase-2 fields through so re-enriching an already-enriched
        # list (the loanwords index enriches at build; lite cards enrich again
        # at render) stays idempotent — without them _label() degrades
        # "Wasei-eigo"/"Partly from" back to a plain "From …".
        for key in ("wasei", "type"):
            if item.get(key):
                enriched[key] = item[key]
        out.append(enriched)
    return out
