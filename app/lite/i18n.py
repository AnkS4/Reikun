"""Chrome strings for the Lite UI (en/ja).

Strings live in the shared ``i18n/*.json`` files at the repo root — the same
source the SvelteKit SPA imports — so both surfaces stay in sync. Keys used
only by Lite are prefixed ``lite_``; keys whose text intentionally differs
between surfaces were renamed on the Lite side (e.g. ``lite_noConjData``).
"""

import json
from pathlib import Path

# app/lite/i18n.py -> repo root locally, /app in the container image
# (Dockerfile copies i18n/ next to app/).
_I18N_DIR = Path(__file__).resolve().parents[2] / "i18n"


def _load(lang: str) -> dict[str, str]:
    return json.loads((_I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


_I18N: dict[str, dict[str, str]] = {lang: _load(lang) for lang in ("en", "ja")}


def _t(lang: str, key: str, **vars: object) -> str:
    """Translate a chrome string; interpolation is ``{name}``. A plain
    ``str.replace`` keeps user text literal (no replacement-pattern expansion
    like JavaScript's ``$&``)."""
    out = _I18N.get(lang, _I18N["en"]).get(key) or _I18N["en"][key]
    for name, value in vars.items():
        out = out.replace("{" + name + "}", str(value))
    return out
