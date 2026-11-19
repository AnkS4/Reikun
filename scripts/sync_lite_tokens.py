#!/usr/bin/env python3
"""Regenerate the design-token block of ``app/static/lite.css`` from
``web/src/app.css`` (the SPA's :root), so the two surfaces can never drift.

The hand-maintained lite palette (bg/text/borders/conj…) is deliberately
NOT synced — lite ships its own mono palette. Only the shared *scale*
tokens are: type sizes, radii, spacing, the z-index ladder, motion durations
and the font stacks, which lite mirrors verbatim.

Usage:
    python scripts/sync_lite_tokens.py          # rewrite the block in place
    python scripts/sync_lite_tokens.py --check  # exit 1 if out of sync

The generated block is delimited by marker comments; everything else in
lite.css is hand-maintained. ``tests/test_lite_tokens.py`` runs --check.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP_CSS = REPO / "web" / "src" / "app.css"
LITE_CSS = REPO / "app" / "static" / "lite.css"

# The shared scale/font tokens, in the order lite declares them.
TOKENS = [
    "--font",
    "--font-display",
    "--font-japanese",
    "--font-devanagari",
    "--font-mono",
    "--radius-xs",
    "--radius-sm",
    "--radius-md",
    "--radius-lg",
    "--radius-xl",
    "--radius-pill",
    "--fs-2xs",
    "--fs-xs",
    "--fs-sm",
    "--fs-md",
    "--fs-base",
    "--fs-body",
    "--fs-lg",
    "--fs-xl",
    "--fs-2xl",
    "--space-1",
    "--space-2",
    "--space-3",
    "--space-4",
    "--space-5",
    "--space-6",
    "--space-7",
    "--space-8",
    "--z-search",
    "--z-floating",
    "--z-header",
    "--z-skip",
    "--dur-fast",
    "--dur-base",
    "--dur-slow",
]

START = "/* >>> generated from web/src/app.css (scripts/sync_lite_tokens.py) — do not edit */"
END = "/* <<< generated from web/src/app.css */"

_DECLARATION = re.compile(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);")


def _normalize(value: str) -> str:
    # Collapse the SPA's tab/newline formatting into lite's single spaces.
    return re.sub(r"\s+", " ", value).strip()


def _first_root_block(css: str) -> str:
    start = css.index(":root {")
    end = css.index("\n}", start)
    return css[start:end]


def _declarations(css: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _DECLARATION.finditer(_first_root_block(css)):
        # Last write wins, mirroring the CSS cascade inside :root and
        # ignoring the themed overrides, which redeclare different names.
        out[m.group(1)] = _normalize(m.group(2))
    return out


def render_block(decls: dict[str, str]) -> str:
    body = "".join(f"{token}:{decls[token]};" for token in TOKENS)
    return f"{START}\n:root{{{body}}}\n{END}"


def _current_region(css: str) -> tuple[int, int]:
    start = css.index(START)
    end = css.index(END, start) + len(END)
    return start, end


def main() -> int:
    check = "--check" in sys.argv
    decls = _declarations(APP_CSS.read_text(encoding="utf-8"))
    missing = [t for t in TOKENS if t not in decls]
    if missing:
        print(f"app.css is missing tokens: {', '.join(missing)}", file=sys.stderr)
        return 2
    block = render_block(decls)

    css = LITE_CSS.read_text(encoding="utf-8")
    if START not in css:
        print("lite.css has no generated-token markers — run the sync once to install them", file=sys.stderr)
        return 2
    start, end = _current_region(css)
    new_css = css[:start] + block + css[end:]

    if check:
        if new_css == css:
            print("lite.css token block is in sync with app.css")
            return 0
        print("lite.css token block is STALE — run scripts/sync_lite_tokens.py", file=sys.stderr)
        return 1
    LITE_CSS.write_text(new_css, encoding="utf-8")
    print("lite.css token block regenerated from app.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
