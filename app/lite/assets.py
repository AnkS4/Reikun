"""Static asset helpers for the Lite UI.

The stylesheet is kept readable on disk (app/static/lite.css) and minified
here, once at import: comments and redundant whitespace are dropped, so the
browser downloads and parses as little CSS as possible. The hash in the URL is
taken from the minified text, so it changes exactly when the served bytes
change — the file can then be cached immutably.
"""

import hashlib
import re
from pathlib import Path

_LITE_CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "lite.css"
_LITE_CSS_SOURCE = _LITE_CSS_PATH.read_text(encoding="utf-8")

_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_WHITESPACE = re.compile(r"\s+")
_AROUND = re.compile(r"\s*([{};,])\s*")


def _minify(css: str) -> str:
    css = _COMMENT.sub("", css)
    css = _WHITESPACE.sub(" ", css)
    css = _AROUND.sub(r"\1", css)
    return css.replace(";}", "}").strip()


_LITE_CSS_TEXT = _minify(_LITE_CSS_SOURCE)

# The control/browse icon font is served as a real file, not inlined: some
# hardened browsers drop data: URI fonts, which left the glyphs as tofu. The
# stylesheet references it through a __FONT_HASH__ placeholder substituted
# here, so the font URL versions exactly like the CSS does. The CSS hash must
# be taken AFTER the substitution — otherwise a font regen leaves the
# year-immutable stylesheet URL unchanged and browsers keep the stale copy.
_LITE_FONT_PATH = Path(__file__).resolve().parent.parent / "static" / "lite-icons.woff2"
_LITE_FONT_BYTES = _LITE_FONT_PATH.read_bytes()
_LITE_FONT_HASH = hashlib.sha256(_LITE_FONT_BYTES).hexdigest()[:12]
_LITE_CSS_TEXT = _LITE_CSS_TEXT.replace("__FONT_HASH__", _LITE_FONT_HASH)
# If lite.css loses the __FONT_HASH__ placeholder, the icon @font-face would
# silently serve a literal __FONT_HASH__ URL and the glyphs would tofu-fail
# with no error anywhere — fail loudly at import instead.
assert "__FONT_HASH__" not in _LITE_CSS_TEXT, "app/static/lite.css lost its __FONT_HASH__ placeholder"
assert _LITE_CSS_TEXT.count(_LITE_FONT_HASH) == 1, "unexpected icon-font URL multiplicity in lite.css"
_LITE_CSS_HASH = hashlib.sha256(_LITE_CSS_TEXT.encode("utf-8")).hexdigest()[:12]
_LITE_CSS_URL = f"/lite/static/lite.css?v={_LITE_CSS_HASH}"
_LITE_FONT_URL = f"/lite/static/lite-icons.woff2?v={_LITE_FONT_HASH}"

# ── Self-hosted fonts (shared with the SPA mirror) ───────────────────────
# Lite serves the same IBM Plex WOFF2 subsets the SPA ships: the mirror is
# committed under web/static/fonts (repo) and COPYed into the image at the
# same relative path (Dockerfile), so the resolver is identical in both.
# If the files are missing the UI still works — the CSS falls back to the
# system stacks, which is the pre-Plex behaviour.
_WEB_FONTS_DIR = Path(__file__).resolve().parents[2] / "web" / "static" / "fonts"
_FONTS_CSS_PATH = _WEB_FONTS_DIR / "fonts.css"
_FONTS_FILES_DIR = _WEB_FONTS_DIR / "files"
try:
    _FONTS_CSS = _FONTS_CSS_PATH.read_bytes()
    _FONTS_CSS_HASH = hashlib.sha256(_FONTS_CSS).hexdigest()[:12]
    _FONTS_CSS_URL = f"/lite/fonts/fonts.css?v={_FONTS_CSS_HASH}"
    _FONTS_LINK = f'<link rel="stylesheet" href="{_FONTS_CSS_URL}">'
except OSError:
    _FONTS_CSS = b""
    _FONTS_CSS_HASH = ""
    _FONTS_CSS_URL = ""
    _FONTS_LINK = ""

_FONT_NAME_RE = re.compile(r"^[a-z0-9-]+\.woff2$")
