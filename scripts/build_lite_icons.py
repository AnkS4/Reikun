#!/usr/bin/env python3
"""Build the Lite control-icon font (app/static/lite-icons.woff2).

The eleven glyphs are the Tabler icons (MIT) the SPA ships (sun, moon,
layout-dashboard, languages, database) plus the browse-tile icons (pen-line,
school, award, import, book-open-text, kana), traced from their 24x24 stroke
SVG paths: each path is
stroked (width 1.5, round caps/joins — matching the SPA's stroke attributes),
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
    # sun — top-right chrome: theme light (tabler:sun, MIT)
    "F5A2": (
        "M8 12a4 4 0 1 0 8 0a4 4 0 1 0-8 0m-5 0h1m8-9v1m8 8h1m-9 8v1M5.6 5.6l.7.7m12.1-.7l-.7.7m0 "
        "11.4l.7.7m-12.1-.7l-.7.7",
    ),
    # moon — top-right chrome: theme dark (tabler:moon, MIT)
    "F497": (
        "M12 3h.393a7.5 7.5 0 0 0 7.92 12.446A9 9 0 1 1 12 2.992z",
    ),
    # layout-dashboard — top-right corner: switch to the full version (tabler:layout-dashboard, MIT)
    "F3F9": (
        "M5 4h4a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1m0 12h4a1 1 0 0 1 1 "
        "1v2a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1m10-4h4a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-4a1 "
        "1 0 0 1-1-1v-6a1 1 0 0 1 1-1m0-8h4a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5a1 1 0 0 "
        "1 1-1",
    ),
    # languages — top-right chrome: language menu trigger (tabler:language, MIT)
    "F658": (
        "M9 6.371C9 10.789 6.761 13 4 13m0-6.629h7",
        "M5 9c0 2.144 2.252 3.908 6 4m1 7l4-9l4 9m-.9-2h-6.2M6.694 3l.793.582",
    ),
    # database — top-right chrome: dictionary status (tabler:database, MIT)
    "F8C4": (
        "M4 6a8 3 0 1 0 16 0A8 3 0 1 0 4 6",
        "M4 6v6a8 3 0 0 0 16 0V6",
        "M4 12v6a8 3 0 0 0 16 0v-6",
    ),
    # kana — browse tile: kana chart (tabler:alphabet-japanese, MIT)
    "F106": (
        "M6 6h10m-6-2c0 6.784.8 11.1 1.5 12.5",
        "M14.25 10.75c0 3.429-2.75 6.75-4.812 6.75S6 16.25 6 14.5C6 12 7.375 10 10.125 10S17 10.855 "
        "17 14.286q0 3.428-2.75 4.714",
    ),
    # pen-line — browse tile: kanji by stroke count (tabler:pencil, MIT)
    "F101": (
        "M4 20h4L18.5 9.5a2.828 2.828 0 1 0-4-4L4 16zm9.5-13.5l4 4",
    ),
    # school — browse tile: kanji by school grade (tabler:school, MIT)
    "F102": (
        "M22 9L12 5L2 9l10 4zv6",
        "M6 10.6V16a6 3 0 0 0 12 0v-5.4",
    ),
    # award — browse tile: kanji by JLPT level (tabler:award, MIT)
    "F103": (
        "M6 9a6 6 0 1 0 12 0A6 6 0 1 0 6 9",
        "m12 15l3.4 5.89l1.598-3.233l3.598.232l-3.4-5.889M6.802 12l-3.4 5.89L7 17.657l1.598 "
        "3.232l3.4-5.889",
    ),
    # import — browse tile: borrowed words (tabler:download, MIT)
    "F104": (
        "M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2M7 11l5 5l5-5m-5-7v12",
    ),
    # book-open-text — browse tile: grouped kanji (strokes / grade / JLPT) (tabler:book-2, MIT)
    "F107": (
        "M19 4v16H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
        "M19 16H7a2 2 0 0 0-2 2M9 8h6",
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
