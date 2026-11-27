"""Static etymology-link families for the Spanish pack.

Built offline by `scripts/build_es_families.py` from the existing Wiktionary
extract; the API only reads the small JSON artifact, so no extraction or
vector work happens at request time. Missing artifact (local dev before the
build step) simply yields an empty list.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("reikun.es_families")
_PATH = Path(__file__).resolve().parent.parent / "data/processed/es/families.json"


@lru_cache(maxsize=1)
def es_families() -> list[dict]:
    try:
        payload = json.loads(_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Spanish word families not built: %s", _PATH)
        return []
    except (ValueError, OSError):
        logger.exception("Could not read Spanish word families")
        return []
    return [
        {
            "word": family["word"],
            "members": [
                {"word": member["word"], "gloss": member.get("gloss", "")}
                for member in family.get("members", [])
            ],
        }
        for family in payload.get("families", [])
    ]
