#!/usr/bin/env python3
"""Write the API's OpenAPI schema to docs/api/openapi.json.

Committed so the frontend's TypeScript types can be regenerated without
booting the app:

    uv run python scripts/dump_openapi.py
    cd web && npm run gen:api

Both outputs are committed, and CI fails if either drifts from the live app
(.github/workflows/ci.yml). The generator version is pinned inside
web/package.json's `gen:api` script — npx rather than a devDependency because
openapi-typescript@7 peer-depends on typescript@^5 and this project is on TS 6.
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
