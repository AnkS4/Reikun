#!/usr/bin/env python3
"""Build the Lite control-icon font (app/static/lite-icons.woff2).

The five glyphs are the SPA's Lucide icons (sun, moon, layout-dashboard,
languages, database), traced from their 24x24 stroke SVG paths: each path is
stroked (width 2, round caps/joins — matching the Lucide stroke attributes),
the stroke outlines are unioned, converted to quadratic outlines and embedded
in a tiny TrueType-flavored woff2 at private-use codepoints. The font is
inlined into lite.css as a data URI by an @font-face rule, so it ships inside
the cached stylesheet and renders even where svg.disabled blanks inline SVG
(Tor/LibreWolf "Safest").

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
    # sun
    "F5A2": (
        "M8 12a4 4 0 1 0 8 0 4 4 0 1 0-8 0",  # circle(12,12,4)
        "M12 2v2", "M12 20v2",
        "m4.93 4.93 1.41 1.41", "m17.66 17.66 1.41 1.41",
        "M2 12h2", "M20 12h2",
        "m6.34 17.66-1.41 1.41", "m19.07 4.93-1.41 1.41",
    ),
    # moon
    "F497": ("M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z",),
    # layout-dashboard: four rounded panels (rects pre-converted, rx=1)
    "F3F9": (
        "M4 3H9A1 1 0 0 1 10 4V11A1 1 0 0 1 9 12H4A1 1 0 0 1 3 11V4A1 1 0 0 1 4 3Z",
        "M15 3H20A1 1 0 0 1 21 4V7A1 1 0 0 1 20 8H15A1 1 0 0 1 14 7V4A1 1 0 0 1 15 3Z",
        "M15 12H20A1 1 0 0 1 21 13V20A1 1 0 0 1 20 21H15A1 1 0 0 1 14 20V13A1 1 0 0 1 15 12Z",
        "M4 16H9A1 1 0 0 1 10 17V20A1 1 0 0 1 9 21H4A1 1 0 0 1 3 20V17A1 1 0 0 1 4 16Z",
    ),
    # languages: the 文/A character pair (six original path elements)
    "F658": (
        "m5 8 6 6", "m4 14 6-6 2-3", "M2 5h12", "M7 2h1",
        "m22 22-5-10-5 10", "M14 18h6",
    ),
    # database: cylinder (ellipse pre-converted) with mid line
    "F8C4": (
        "M3 5a9 3 0 1 0 18 0 9 3 0 1 0-18 0",  # ellipse(12,5,9,3)
        "M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5",
        "M3 12c0 1.66 4 3 9 3s9-1.34 9-3",
    ),
    # pencil — browse tile: kanji by stroke count
    "F101": ("M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z",),
    # school (graduation cap) — browse tile: kanji by school grade
    "F102": (
        "M22 10 12 5 2 10l10 5 10-5z",
        "M6 12.5v4.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5v-4.5",
        "M22 10v6",
    ),
    # sparkles — browse tile: kanji by JLPT level
    "F103": (
        "m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21"
        "l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z",
        "M5 3v4", "M19 17v4", "M3 5h4", "M17 19h4",
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
    fb.font.flavor = "woff2"
    fb.save(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(_ICONS)} glyphs)")


if __name__ == "__main__":
    main()
