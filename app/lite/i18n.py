"""Chrome strings for the Lite UI.

Strings live in the shared ``i18n/*.json`` files at the repo root — the same
source the SvelteKit SPA imports — so both surfaces stay in sync. Keys used
only by Lite are prefixed ``lite_``; keys whose text intentionally differs
between surfaces were renamed on the Lite side (e.g. ``lite_noConjData``).
"""

import json
import re
from pathlib import Path

# app/lite/i18n.py -> repo root locally, /app in the container image
# (Dockerfile copies i18n/ next to app/).
_I18N_DIR = Path(__file__).resolve().parents[2] / "i18n"


def _load(lang: str) -> dict[str, str]:
    return json.loads((_I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


# Every i18n/<locale>.json ships a full table; "en" is the required fallback.
_LOCALES = tuple(
    sorted(p.stem for p in _I18N_DIR.glob("*.json"))
)
_I18N: dict[str, dict[str, str]] = {lang: _load(lang) for lang in _LOCALES}

_DEVANAGARI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def _fmt_count(n: int, lang: str) -> str:
    """Locale-aware number rendering: Devanagari digits for hi/mr (Indian
    grouping, matching Intl.NumberFormat with mr-IN/hi-IN), western grouping
    otherwise."""
    if lang in ("hi", "mr"):
        s = str(n)
        if len(s) <= 3:
            out = s
        else:
            head, tail, parts = s[:-3], s[-3:], []
            while head:
                parts.append(head[-2:])
                head = head[:-2]
            out = ",".join(reversed(parts)) + "," + tail
        return out.translate(_DEVANAGARI_DIGITS)
    return f"{n:,}"


def _t(lang: str, key: str, **vars: object) -> str:
    """Translate a chrome string; interpolation is ``{name}``. A plain
    ``str.replace`` keeps user text literal (no replacement-pattern expansion
    like JavaScript's ``$&``)."""
    out = _I18N.get(lang, _I18N["en"]).get(key) or _I18N["en"][key]
    if not vars:
        return out
    # Single pass: a substituted value containing "{other}" must not be
    # re-matched by a later variable's placeholder.
    pattern = re.compile("|".join(re.escape("{" + name + "}") for name in vars))

    def _sub(match: re.Match[str]) -> str:
        return str(vars[match.group(0)[1:-1]])

    return pattern.sub(_sub, out)
