"""The SPA keeps committed byte-identical copies of the shared root i18n/*.json
tables (web-only Docker build context). Lite reads the root copies. If one side
is edited without the other, the two frontends silently disagree — this guards it."""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LOCALES = ["en", "es", "hi", "ja", "mr"]


@pytest.mark.parametrize("locale", LOCALES)
def test_spa_i18n_copy_matches_shared_root(locale):
    root = REPO / "i18n" / f"{locale}.json"
    spa = REPO / "web" / "src" / "lib" / "i18n" / f"{locale}.json"
    assert spa.read_bytes() == root.read_bytes(), (
        f"{locale}: web/src/lib/i18n/{locale}.json has drifted from i18n/{locale}.json — "
        "mirror the edit to both (they are separate build inputs)."
    )
