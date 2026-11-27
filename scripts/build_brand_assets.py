"""Generate Reikun's Signal and Graphite artwork from the approved Penpot master.

Run as a maintenance task, not during the web build. See assets/README.md.
"""

import subprocess
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONTS = ROOT / "web/static/fonts/files"

# Board 11, 11.1A / Signal and 11.1C / Graphite. Same paths, normalized
# from the 85 px primary master to a 100-unit square, in Penpot paint order.
PATHS = {
    "stem": (
        "M6.8 2.381H15.761C17.19 2.381 17.904 3.121 17.904 4.6V95.4"
        "C17.904 96.879 17.19 97.619 15.761 97.619H6.8"
        "C5.314 97.619 4.571 96.879 4.571 95.4V4.6C4.571 3.121 5.314 2.381 6.8 2.381Z"
    ),
    "foot": (
        "M54.5 51.5L65.3 43.2L95.2 93.1C96.934 96.113 96.099 97.619 92.7 97.619"
        "H83.901C82.633 97.619 81.5 96.879 80.5 95.4Z"
    ),
    "sun": (
        "M47.429 61.428C63.734 61.428 76.952 48.21 76.952 31.905"
        "C76.952 15.599 63.734 2.381 47.429 2.381C31.122 2.381 17.906 15.599 17.906 31.905"
        "C17.906 48.21 31.122 61.428 47.429 61.428Z"
    ),
}
JAPAN_RED = "#BC002D"  # Japanese flag red; the Signal sun stays consistent in every palette.
SIGNAL = ("#202322", "#606A65", JAPAN_RED)
# Dark variant keeps the SAME flag red; only the ink/foot flip for contrast.
SIGNAL_DARK = ("#F1F2EC", "#ACB6B0", JAPAN_RED)
# Spanish edition: the sun takes the Spanish flag's gold — the flag's dominant
# color, distinct from the Japanese red, and it reads on both light and dark.
SPANISH = ("#202322", "#606A65", "#F1BF00")
SPANISH_DARK = ("#F1F2EC", "#ACB6B0", "#F1BF00")
GRAPHITE = (SIGNAL[0], SIGNAL[0], SIGNAL[1])
GRAPHITE_DARK = (SIGNAL_DARK[0], SIGNAL_DARK[0], SIGNAL_DARK[1])
PAPER = "#FBFAF6"
NIGHT = "#171A19"
type Palette = tuple[str, str, str]


def mark(palette: Palette, x: float = 0, y: float = 0, size: float = 100) -> str:
    layers = "\n".join(
        f'<path class="{name}" fill="{color}" d="{d}"/>'
        for (name, d), color in zip(PATHS.items(), palette, strict=True)
    )
    return f'<g transform="translate({x:g} {y:g}) scale({size / 100:g})">\n{layers}\n</g>'


def svg(title: str, w: int, h: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">\n<title>{escape(title)}</title>\n{body}\n</svg>\n'
    )


def tile(palette: Palette, bg: str, size: int) -> str:
    margin = (100 - size) / 2
    return svg(
        "Reikun app icon",
        100,
        100,
        f'<rect width="100" height="100" fill="{bg}"/>\n' + mark(palette, margin, margin, size),
    )


def write(name: str, artwork: str, **pngs: int) -> None:
    target = ASSETS / name
    target.write_text(artwork, encoding="utf-8")
    for filename, width in pngs.items():
        subprocess.run(
            ["rsvg-convert", "--width", str(width), "-o", target.with_name(filename), target],
            check=True,
        )


@cache
def plex_paths(value: str, face: str) -> tuple[str, float, int]:
    """Use the shipped Plex outlines so PNGs and standalone SVGs agree on every host."""
    source = next(FONTS.glob(f"ibm-plex-{face}-????????.woff2"))
    with TTFont(source) as font:
        glyphs = font.getGlyphSet()
        cmap = font.getBestCmap()
        advance = 0
        paths = []
        for char in value:
            glyph = glyphs[cmap[ord(char)]]
            pen = SVGPathPen(glyphs)
            glyph.draw(pen)
            if data := pen.getCommands():
                paths.append(f'<path transform="translate({advance:g})" d="{data}"/>')
            advance += glyph.width
        return "".join(paths), advance, font["head"].unitsPerEm


def lettering(
    value: str,
    x: float,
    baseline: float,
    size: int,
    color: str,
    face: str = "sans-w600-latin",
    *,
    center: bool = False,
) -> str:
    paths, advance, em = plex_paths(value, face)
    scale = size / em
    if center:
        x -= advance * scale / 2
    return f'<g fill="{color}" transform="translate({x:g} {baseline:g}) scale({scale:g} {-scale:g})">{paths}</g>'


def main() -> None:
    for suffix, palette, title in (
        ("", SIGNAL, "Reikun Signal"),
        ("-dark", SIGNAL_DARK, "Reikun Signal"),
        ("-es", SPANISH, "Reikun Signal (Spanish)"),
        ("-es-dark", SPANISH_DARK, "Reikun Signal (Spanish)"),
        ("-graphite", GRAPHITE, "Reikun Graphite"),
        ("-graphite-dark", GRAPHITE_DARK, "Reikun Graphite"),
    ):
        name = "emblem" + suffix
        artwork = svg(title, 100, 100, mark(palette))
        write(f"emblems/{name}.svg", artwork, **{f"{name}.png": 496})

    dark_rules = "".join(f".{k}{{fill:{v}}}" for k, v in zip(PATHS, SIGNAL_DARK, strict=True))
    adaptive = "<style>@media (prefers-color-scheme:dark){" + dark_rules + "}</style>\n"
    write(
        "favicons/favicon.svg",
        svg("Reikun", 100, 100, adaptive + mark(SIGNAL)),
        **{f"favicon-{size}.png": size for size in (16, 32, 48)},
    )
    es_rules = "".join(f".{k}{{fill:{v}}}" for k, v in zip(PATHS, SPANISH_DARK, strict=True))
    es_adaptive = "<style>@media (prefers-color-scheme:dark){" + es_rules + "}</style>\n"
    write(
        "favicons/favicon-es.svg",
        svg("Reikun", 100, 100, es_adaptive + mark(SPANISH)),
        **{f"favicon-es-{size}.png": size for size in (16, 32, 48)},
    )
    # Full-bleed squares let the platform apply its own corner or circle mask.
    write("icons/icon-light.svg", tile(SIGNAL, PAPER, 70), **{"apple-touch-icon.png": 180})
    write("icons/icon-dark.svg", tile(SIGNAL_DARK, NIGHT, 70))
    write("icons/icon-graphite.svg", tile(GRAPHITE, PAPER, 70))
    write("icons/icon-es-light.svg", tile(SPANISH, PAPER, 70), **{"apple-touch-icon-es.png": 180})
    write("icons/icon-es-dark.svg", tile(SPANISH_DARK, NIGHT, 70))
    # A centered 56% square fits inside the manifest's 80%-diameter safe circle.
    write("icons/icon-maskable.svg", tile(SIGNAL, PAPER, 56), **{"icon-192.png": 192, "icon-512.png": 512})
    write("icons/icon-es-maskable.svg", tile(SPANISH, PAPER, 56), **{"icon-es-192.png": 192, "icon-es-512.png": 512})

    for suffix, palette in (("", SIGNAL), ("-es", SPANISH), ("-graphite", GRAPHITE)):
        for layout in ("horizontal", "stacked"):
            name = f"logo-{layout}{suffix}"
            if layout == "horizontal":
                w, h = 560, 180
                body = mark(palette, 24, 23, 134) + lettering("Reikun", 187, 127, 108, SIGNAL[0])
            else:
                w, h = 352, 330
                body = mark(palette, 82, 24, 188) + lettering("Reikun", 176, 292, 77, SIGNAL[0], center=True)
            write(f"logos/{name}.svg", svg("Reikun", w, h, body), **{f"{name}.png": w * 2})

    card = "\n".join(
        [
            f'<rect width="1200" height="630" fill="{PAPER}"/>',
            lettering("OPEN JAPANESE LEARNING", 78, 91, 24, SIGNAL[1], "mono-w500-latin"),
            mark(SIGNAL, 73, 169, 149),
            lettering("Reikun", 255, 295, 138, SIGNAL[0]),
            lettering("例訓", 705, 292, 74, SIGNAL[1], "sans-jp-w400-japanese"),
            lettering("Semantic Japanese Dictionary & Reading Assistant", 78, 407, 40, SIGNAL[0]),
            lettering(
                "Word meanings, furigana, kanji and grammar in context.", 78, 468, 31, SIGNAL[1], "sans-w400-latin"
            ),
            '<path d="M78 522H1122" stroke="#D6DAD2" stroke-width="2"/>',
            lettering("reikun.app", 78, 574, 26, SIGNAL[1], "mono-w500-latin"),
        ]
    )
    write(
        "images/og-image.svg",
        svg("Reikun (例訓) — Semantic Japanese Dictionary & Reading Assistant", 1200, 630, card),
        **{"og-image.png": 1200},
    )

    es_card = "\n".join(
        [
            f'<rect width="1200" height="630" fill="{PAPER}"/>',
            lettering("OPEN LANGUAGE LEARNING", 78, 91, 24, SIGNAL[1], "mono-w500-latin"),
            mark(SPANISH, 73, 169, 149),
            lettering("Reikun", 255, 295, 138, SIGNAL[0]),
            lettering("The open Spanish dictionary", 78, 407, 40, SIGNAL[0]),
            lettering(
                "Word meanings, pronunciation, conjugations and grammar in context.",
                78,
                468,
                31,
                SIGNAL[1],
                "sans-w400-latin",
            ),
            '<path d="M78 522H1122" stroke="#D6DAD2" stroke-width="2"/>',
            lettering("es.reikun.app", 78, 574, 26, SIGNAL[1], "mono-w500-latin"),
        ]
    )
    write(
        "images/og-image-es.svg",
        svg("Reikun — The open Spanish dictionary", 1200, 630, es_card),
        **{"og-image-es.png": 1200},
    )


if __name__ == "__main__":
    main()
