#!/usr/bin/env python3
"""Write the API's OpenAPI schema to docs/api/openapi.json.

Committed so the frontend's TypeScript types can be regenerated without
booting the app:

    uv run python scripts/dump_openapi.py
    npx openapi-typescript docs/api/openapi.json -o web/src/lib/openapi.d.ts

(npx fetches openapi-typescript on first run — needs Node, not Python deps.)
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import app  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI {schema['info']['version']} → {OUT.relative_to(OUT.parents[2])} "
          f"({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
