#!/usr/bin/env python3
"""Build the Lite control-icon font (app/static/lite-icons.woff2).

The twelve glyphs are the Lucide icons (ISC) the SPA ships (sun, moon,
layout-dashboard, languages, database) plus the browse-tile icons (pen-line,
school, award, import, book-open-text, chart-line, share), traced from their 24x24 stroke
SVG paths: each path is
stroked (width 2.0, round caps/joins — matching the SPA's stroke attributes),
the stroke outlines are unioned, converted to quadratic outlines and embedded
in a tiny TrueType-flavored woff2 at private-use codepoints. The font is
served at /lite/static/lite-icons.woff2 and referenced from lite.css (a real
file, not a data URI, since some hardened browsers drop data: fonts); it
renders even where svg.disabled blanks inline SVG (Tor/LibreWolf "Safest").

Regenerate after changing an icon:
    uv run --with skia-pathops --with fonttools --with brotli \
        python scripts/build_lite_icons.py

Requires: skia-pathops, fonttools, brotli (uv --with covers all three).
"""

from pathlib import Path

import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import parse_path

UPM = 1000
SCALE = UPM / 24.0
# SVG is y-down, font units are y-up: glyph drawing flips vertically around
# the em square (per-glyph x/y offsets are added on top in glyph_from_svg).

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "lite-icons.woff2"

# Lucide icon sources (24x24 viewBox, stroke-width 2, round caps/joins).
# Each tuple element is one original SVG path's `d`, verbatim — relative
# commands must NOT be merged into a single path string (each SVG <path>
# restarts its coordinate context at 0,0). circle/ellipse/rect primitives
# are pre-converted to equivalent absolute path data.
_ICONS = {
    # sun — top-right chrome: theme light (lucide:sun, ISC)
    "F5A2": (
        "M8.0,12.0a4.0,4.0 0 1 0 8.0,0a4.0,4.0 0 1 0 -8.0,0z",
        "M12 2v2",
        "M12 20v2",
        "m4.93 4.93 1.41 1.41",
        "m17.66 17.66 1.41 1.41",
        "M2 12h2",
        "M20 12h2",
        "m6.34 17.66-1.41 1.41",
        "m19.07 4.93-1.41 1.41",
    ),
    # moon — top-right chrome: theme dark (lucide:moon, ISC)
    "F497": (
        "M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 "
        "8.268c.344-.215.825-.004.803.401",
    ),
    # layout-dashboard — top-right corner: switch to the full version (lucide:layout-dashboard, ISC)
    "F3F9": (
        "M4.0,3.0h5.0a1.0,1.0 0 0 1 1.0,1.0v7.0a1.0,1.0 0 0 1 -1.0,1.0h-5.0a1.0,1.0 0 0 1 "
        "-1.0,-1.0v-7.0a1.0,1.0 0 0 1 1.0,-1.0z",
        "M15.0,3.0h5.0a1.0,1.0 0 0 1 1.0,1.0v3.0a1.0,1.0 0 0 1 -1.0,1.0h-5.0a1.0,1.0 0 0 1 "
        "-1.0,-1.0v-3.0a1.0,1.0 0 0 1 1.0,-1.0z",
        "M15.0,12.0h5.0a1.0,1.0 0 0 1 1.0,1.0v7.0a1.0,1.0 0 0 1 -1.0,1.0h-5.0a1.0,1.0 0 0 1 "
        "-1.0,-1.0v-7.0a1.0,1.0 0 0 1 1.0,-1.0z",
        "M4.0,16.0h5.0a1.0,1.0 0 0 1 1.0,1.0v3.0a1.0,1.0 0 0 1 -1.0,1.0h-5.0a1.0,1.0 0 0 1 "
        "-1.0,-1.0v-3.0a1.0,1.0 0 0 1 1.0,-1.0z",
    ),
    # languages — top-right chrome: language menu trigger (lucide:languages, ISC)
    "F658": (
        "m5 8 6 6",
        "m4 14 6-6 2-3",
        "M2 5h12",
        "M7 2h1",
        "m22 22-5-10-5 10",
        "M14 18h6",
    ),
    # database — top-right chrome: dictionary status (lucide:database, ISC)
    "F8C4": (
        "M3.0,5.0a9.0,3.0 0 1 0 18.0,0a9.0,3.0 0 1 0 -18.0,0z",
        "M3 5V19A9 3 0 0 0 21 19V5",
        "M3 12A9 3 0 0 0 21 12",
    ),
    # pen-line — browse tile: kanji by stroke count (lucide:pen-line, ISC)
    "F101": (
        "M13 21h8",
        "M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 "
        ".623.622l4.353-1.32a2 2 0 0 0 .83-.497z",
    ),
    # school — browse tile: kanji by school grade (lucide:school, ISC)
    "F102": (
        "M14 21v-3a2 2 0 0 0-4 0v3",
        "M18 4.933V21",
        "m4 6 7.106-3.79a2 2 0 0 1 1.788 0L20 6",
        "m6 11-3.52 2.147a1 1 0 0 0-.48.854V19a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5a1 1 0 0 "
        "0-.48-.853L18 11",
        "M6 4.933V21",
        "M10.0,9.0a2.0,2.0 0 1 0 4.0,0a2.0,2.0 0 1 0 -4.0,0z",
    ),
    # award — browse tile: kanji by JLPT level (lucide:award, ISC)
    "F103": (
        "m15.477 12.89 1.515 8.526a.5.5 0 0 1-.81.47l-3.58-2.687a1 1 0 0 0-1.197 0l-3.586 "
        "2.686a.5.5 0 0 1-.81-.469l1.514-8.526",
        "M6.0,8.0a6.0,6.0 0 1 0 12.0,0a6.0,6.0 0 1 0 -12.0,0z",
    ),
    # import — browse tile: borrowed words (lucide:import, ISC)
    "F104": (
        "M12 3v12",
        "m8 11 4 4 4-4",
        "M8 5H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-4",
    ),
    # share — browse tile: Japanese-made English coinages; tray + up chevron,
    # the visual mirror of the loanwords tile's import glyph (lucide:share, ISC)
    "F109": (
        "M12 2v13",
        "m16 6-4-4-4 4",
        "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8",
    ),
    # chart-line — browse tile: kanji by frequency rank (lucide:chart-line, ISC)
    "F108": (
        "M3 3v16a2 2 0 0 0 2 2h16",
        "m19 9-5 5-4-4-3 3",
    ),
    # book-open-text — browse tile: grouped kanji (strokes / grade / JLPT) (lucide:book-open-text, ISC)
    "F107": (
        "M12 5v16",
        "M16 13h2",
        "M16 9h2",
        "M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 "
        "00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z",
        "M6 13h2",
        "M6 9h2",
    ),
}


def _stroked_paths(ds: tuple[str, ...]):
    """Stroke each Lucide subpath (24x24 space) into pathops outlines."""
    out = []
    for d in ds:
        path = pathops.Path()
        parse_path(d, path.getPen())
        path.stroke(2.0, pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
        path.convertConicsToQuads(0.1)
        out.append(path)
    return out


def glyph_from_svg(ds: tuple[str, ...]):
    """Return a glyf glyph for the icon, ink optically centred in the em.

    No union needed: every stroked outline is a closed contour wound the same
    direction, so overlaps add under nonzero fill rather than cancelling.
    The ink is recentred horizontally/vertically so it sits exactly where the
    SVG viewBox centres it — the SPA renders the same paths at a fixed size,
    and off-centre font metrics are what made the two look misaligned.
    """
    paths = _stroked_paths(ds)

    # Pass 1: measure ink bounds in 24-space to compute the centring offset.
    bounds_pen = BoundsPen(None)
    measure = TransformPen(bounds_pen, Transform(SCALE, 0, 0, -SCALE, 0, UPM))
    for path in paths:
        path.draw(measure)
    x0, y0, x1, y1 = bounds_pen.bounds
    dx = (UPM - (x1 - x0)) / 2 - x0
    dy = (UPM - (y1 - y0)) / 2 - y0

    # Pass 2: draw with the offset baked into the transform.
    tt = TTGlyphPen(None)
    xf = Transform(SCALE, 0, 0, -SCALE, dx, UPM + dy)
    for path in paths:
        path.draw(TransformPen(Cu2QuPen(tt, max_err=1.0), xf))
    return tt.glyph()


def main() -> None:
    glyph_order = [".notdef"]
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    cmap = {}
    metrics = {".notdef": (UPM, 0)}
    for i, (code, ds) in enumerate(_ICONS.items()):
        name = f"icon-{i:03d}"
        glyph_order.append(name)
        glyphs[name] = glyph_from_svg(ds)
        cmap[int(code, 16)] = name
        metrics[name] = (UPM, 0)

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=UPM, descent=0)
    fb.setupOS2()
    fb.setupPost()
    fb.setupNameTable(
        {
            "familyName": "reikun-icons",
            "styleName": "Regular",
            "uniqueFontIdentifier": "reikun-lite-icons",
            "fullName": "reikun lite icons",
            "psName": "reikun-icons",
        }
    )
    # Byte-reproducible builds: pin the head timestamps so the same source
    # always emits the same font (no churn for a no-op rebuild).
    fb.font["head"].created = 0
    fb.font["head"].modified = 0
    fb.font.flavor = "woff2"
    fb.save(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(_ICONS)} glyphs)")


if __name__ == "__main__":
    main()
