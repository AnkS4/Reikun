# Reikun brand assets

**Signal** (Penpot 11.1A) is the primary mark. **Graphite** (11.1C) is the neutral alternative. Both use the same flat-ended stem, diagonal foot, and solid disc.

| Mark | On light backgrounds | On dark backgrounds |
| --- | --- | --- |
| Signal | [SVG](emblems/emblem.svg) · [PNG](emblems/emblem.png) | [SVG](emblems/emblem-dark.svg) |
| Graphite | [SVG](emblems/emblem-graphite.svg) · [PNG](emblems/emblem-graphite.png) | [SVG](emblems/emblem-graphite-dark.svg) |

The emblems and [IBM Plex Sans lockups](logos/) have transparent backgrounds. The
[app icons](icons/) have opaque backgrounds so platforms can crop them; the 192
and 512 px PNGs leave room for an OS mask. The [favicon](favicons/favicon.svg)
adapts to light and dark browser chrome, with PNG fallbacks at 16, 32 and 48 px.
Use the [Signal social preview](images/og-image.png) for link sharing.

## Regeneration

From the repository root:

```sh
python3 scripts/build_brand_assets.py
node web/tools/sync-assets.mjs
```

The first step uses Python 3.12+, FontTools with Brotli, and `rsvg-convert`
(librsvg). The glyph outlines come from the committed IBM Plex WOFF2 files:
no font download or system-installed Plex face is needed. The web build only
copies files; it does not run the renderer.
