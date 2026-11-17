#!/usr/bin/env python3
"""Subset one TTF/OTF to WOFF2 for a given unicode range.

Usage:
    python3 web/tools/_subset.py <input.ttf> <unicodes> <output.woff2>

`unicodes` is a comma-separated list of U+xxxx or U+xxxx-xxxx ranges.
Exits 2 when the font has no glyphs in the requested range (caller skips it).
"""
import sys

from fontTools import subset
from fontTools.subset import Subsetter
from fontTools.ttLib import TTFont


def parse_unicodes(s: str) -> list[int]:
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo.replace("U+", ""), 16), int(hi.replace("U+", ""), 16) + 1))
        else:
            out.append(int(part.replace("U+", ""), 16))
    return out


def main() -> int:
    src, unicodes, dst = sys.argv[1], parse_unicodes(sys.argv[2]), sys.argv[3]
    want = set(unicodes)
    tt = TTFont(src)
    covered = set(tt.getBestCmap().keys())
    if not (want & covered):
        return 2
    opts = subset.Options()
    opts.hinting = False          # TrueType hinting carries no value for woff2
    opts.layout_features = '*'    # keep GSUB/GPOS needed for Devanagari conjuncts
    opts.layout_scripts = '*'
    opts.name_IDs = ['*']
    opts.flavor = 'woff2'
    font = TTFont(src)
    subsetter = Subsetter(options=opts)
    subsetter.populate(unicodes=want)
    subsetter.subset(font)
    font.save(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
