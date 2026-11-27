#!/usr/bin/env python3
"""Filter a wiktextract JSONL dump down to one language.

kaikki's raw en-Wiktionary extract (raw-wiktextract-data.jsonl.gz) holds every
language's entries; the Spanish pack needs the `lang_code == "es"` slice (the
English-glossed Spanish entries). Streams line by line — constant memory,
~24.8 GB decompressed passes through in a few minutes.

Usage:
    uv run python scripts/filter_lang.py --lang es \
        data/raw/en/raw-wiktextract-data.jsonl.gz \
        data/raw/en/raw-wiktextract-es.jsonl.gz
"""
import argparse
import gzip
import json
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--lang", default="es")
    args = parser.parse_args()

    t0 = time.time()
    total = kept = 0
    with gzip.open(args.src, "rt", encoding="utf-8") as f, \
            gzip.open(args.dst, "wt", encoding="utf-8") as out:
        for line in f:
            total += 1
            # Cheap pre-check before json.loads: the lang_code field appears
            # early in each object; a miss skips the parse entirely.
            if f'"lang_code":"{args.lang}"' not in line and f'"lang_code": "{args.lang}"' not in line:
                continue
            entry = json.loads(line)
            if entry.get("lang_code") == args.lang:
                out.write(line)
                kept += 1
            if total % 2_000_000 == 0:
                print(f"  {total:,} lines, {kept:,} kept ({time.time() - t0:.0f}s)", flush=True)
    print(f"done: {kept:,} / {total:,} lines kept in {time.time() - t0:.0f}s -> {args.dst}")


if __name__ == "__main__":
    main()
