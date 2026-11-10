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
_LITE_CSS_HASH = hashlib.sha256(_LITE_CSS_TEXT.encode("utf-8")).hexdigest()[:12]
_LITE_CSS_URL = f"/lite/static/lite.css?v={_LITE_CSS_HASH}"
