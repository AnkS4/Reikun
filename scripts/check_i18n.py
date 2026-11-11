#!/usr/bin/env python3
"""Validate the shared UI string tables in i18n/.

Both surfaces read these files — the SvelteKit SPA imports them as JSON and
the Lite UI loads them in app/lite/i18n.py — so this is the single place key
parity is enforced:

- en.json and ja.json must have identical key sets
- every ``{placeholder}`` in one locale must appear in the other
- no empty strings
- markup (``<b>``, ``<span …>``) is only allowed in ``lite_``-prefixed keys:
  Lite strings embed HTML, SPA strings are plain text

For human review or a DeepL/LibreTranslate pass, export a three-column TSV:

    uv run python scripts/check_i18n.py --tsv /tmp/i18n_review.tsv
"""

import argparse
import json
import re
import sys
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parents[1] / "i18n"
LOCALES = ("en", "ja")
PLACEHOLDER = re.compile(r"\{(\w+)\}")
MARKUP = re.compile(r"<[a-zA-Z/!]")
# Searched-for caption is split around the query; English puts nothing after it.
ALLOW_EMPTY = {"searchedForAfter"}


def load() -> dict[str, dict[str, str]]:
    return {
        lang: json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        for lang in LOCALES
    }


def check(tables: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    en, ja = tables["en"], tables["ja"]

    only_en = sorted(set(en) - set(ja))
    only_ja = sorted(set(ja) - set(en))
    errors += [f"{key}: in en.json but missing from ja.json" for key in only_en]
    errors += [f"{key}: in ja.json but missing from en.json" for key in only_ja]

    for key in sorted(set(en) & set(ja)):
        en_ph = set(PLACEHOLDER.findall(en[key]))
        ja_ph = set(PLACEHOLDER.findall(ja[key]))
        if en_ph != ja_ph:
            errors.append(
                f"{key}: placeholders differ — en {sorted(en_ph)} vs ja {sorted(ja_ph)}"
            )
        for lang, table in (("en", en), ("ja", ja)):
            value = table[key]
            if not value.strip() and key not in ALLOW_EMPTY:
                errors.append(f"{key}: empty {lang} string")
            if MARKUP.search(value) and not key.startswith("lite_"):
                errors.append(
                    f"{key}: markup in a shared key — Lite-only strings must be "
                    f"prefixed 'lite_' ({lang}: {value!r})"
                )
    return errors


def export_tsv(tables: dict[str, dict[str, str]], path: Path) -> None:
    def cell(s: str) -> str:
        return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")

    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("key\ten\tja\n")
        for key in tables["en"]:
            fh.write(f"{key}\t{cell(tables['en'][key])}\t{cell(tables['ja'][key])}\n")
    print(f"wrote {path} ({len(tables['en'])} rows)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tsv", type=Path, metavar="PATH",
                        help="also write a key/en/ja TSV for review")
    args = parser.parse_args()

    tables = load()
    errors = check(tables)
    if args.tsv:
        export_tsv(tables, args.tsv)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"{len(errors)} problem(s) in i18n/", file=sys.stderr)
        return 1
    print(f"i18n OK — {len(tables['en'])} keys x {len(LOCALES)} locales")
    return 0


if __name__ == "__main__":
    sys.exit(main())
