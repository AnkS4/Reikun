#!/usr/bin/env python3
"""Mirror the shared root i18n/*.json tables into the SPA's committed copies.

The web image builds from ``./web/`` as its context, so the SPA cannot read
the repository root — it ships byte-identical copies at
``web/src/lib/i18n/*.json``. The Lite UI reads the root copies instead.

**Rule: edit the ROOT tables only, then run this script.**

    uv run python scripts/sync_i18n.py           # mirror (idempotent)
    uv run python scripts/sync_i18n.py --check    # exit 1 on drift (pre-commit/CI)

``tests/test_i18n_parity.py`` enforces the same contract in pytest.
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "i18n"
SPA = REPO / "web" / "src" / "lib" / "i18n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if web/ copies drift from root")
    args = ap.parse_args()

    if not SPA.is_dir():
        sys.exit(f"error: {SPA} missing — run from a checkout with web/ built once")

    errors: list[str] = []
    root_files = sorted(ROOT.glob("*.json"))
    if not root_files:
        sys.exit("error: no *.json under i18n/")

    for rf in root_files:
        uf = SPA / rf.name
        if not uf.exists() or digest(rf) != digest(uf):
            if args.check:
                errors.append(f"drifted: web/src/lib/i18n/{rf.name}")
            else:
                shutil.copy2(rf, uf)
                print(f"synced {rf.name}")

    errors.extend(
        f"spare file (no root counterpart): web/src/lib/i18n/{uf.name}"
        for uf in sorted(SPA.glob("*.json"))
        if not (ROOT / uf.name).exists()
    )

    if errors:
        for e in errors:
            print(f"error: {e}")
        if args.check:
            sys.exit("web/src/lib/i18n is out of sync — run scripts/sync_i18n.py")
        return 1
    if args.check:
        print(f"ok: {len(root_files)} web copies match root tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
