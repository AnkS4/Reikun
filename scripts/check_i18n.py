#!/usr/bin/env python3
"""Validate the shared UI string tables in i18n/.

Every surface reads these files — the SvelteKit SPA imports them as JSON and
the Lite UI loads them in app/lite/i18n.py — so this is the single place key
parity is enforced. en.json is the reference table; every other
``*.json`` in the directory is checked against it:

- all locale files must have identical key sets
- every ``{placeholder}`` in one locale must appear in the others
- no empty strings
- markup (``<b>``, ``<span …>``) is only allowed in ``lite_``-prefixed keys:
  Lite strings embed HTML, SPA strings are plain text

For human review or a translation pass, export a TSV (en + one column per
locale, in filename order):

    uv run python scripts/check_i18n.py --tsv /tmp/i18n_review.tsv
"""

import argparse
import json
import re
import sys
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parents[1] / "i18n"
REFERENCE = "en"
PLACEHOLDER = re.compile(r"\{(\w+)\}")
MARKUP = re.compile(r"<[a-zA-Z/!]")
# Searched-for caption is split around the query; English puts nothing after it.
ALLOW_EMPTY = {"searchedForAfter"}


def locales() -> list[str]:
    langs = sorted(p.stem for p in I18N_DIR.glob("*.json"))
    if REFERENCE not in langs:
        sys.exit(f"error: {REFERENCE}.json missing from {I18N_DIR}")
    return langs


def load(langs: list[str]) -> dict[str, dict[str, str]]:
    return {
        lang: json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
        for lang in langs
    }


def check(tables: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    en = tables[REFERENCE]
    others = {lang: t for lang, t in tables.items() if lang != REFERENCE}

    for lang, table in others.items():
        only_ref = sorted(set(en) - set(table))
        only_loc = sorted(set(table) - set(en))
        errors += [f"{key}: in {REFERENCE}.json but missing from {lang}.json"
                   for key in only_ref]
        errors += [f"{key}: in {lang}.json but missing from {REFERENCE}.json"
                   for key in only_loc]

    for key in sorted(set(en)):
        en_ph = set(PLACEHOLDER.findall(en[key]))
        for lang, table in others.items():
            if key not in table:
                continue
            loc_ph = set(PLACEHOLDER.findall(table[key]))
            if en_ph != loc_ph:
                errors.append(
                    f"{key}: placeholders differ — {REFERENCE} {sorted(en_ph)} "
                    f"vs {lang} {sorted(loc_ph)}"
                )
        for lang, table in tables.items():
            if key not in table:
                continue
            value = table[key]
            if not value.strip() and key not in ALLOW_EMPTY:
                errors.append(f"{key}: empty {lang} string")
            if MARKUP.search(value) and not key.startswith("lite_"):
                errors.append(
                    f"{key}: markup in a shared key — Lite-only strings must be "
                    f"prefixed 'lite_' ({lang}: {value!r})"
                )
    return errors


def export_tsv(tables: dict[str, dict[str, str]], langs: list[str], path: Path) -> None:
    def cell(s: str) -> str:
        return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")

    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("key\t" + "\t".join(langs) + "\n")
        for key in tables[REFERENCE]:
            fh.write(f"{key}\t" + "\t".join(
                cell(tables[lang].get(key, "")) for lang in langs) + "\n")
    print(f"wrote {path} ({len(tables[REFERENCE])} rows x {len(langs)} locales)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tsv", type=Path, metavar="PATH",
                        help="also write a key + one column per locale TSV")
    args = parser.parse_args()

    langs = locales()
    tables = load(langs)
    errors = check(tables)
    if args.tsv:
        export_tsv(tables, langs, args.tsv)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"{len(errors)} problem(s) in i18n/", file=sys.stderr)
        return 1
    print(f"i18n OK — {len(tables[REFERENCE])} keys x {len(langs)} locales")
    return 0


if __name__ == "__main__":
    sys.exit(main())
