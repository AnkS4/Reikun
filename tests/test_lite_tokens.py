"""Parity gate: app/static/lite.css's generated token block must match
web/src/app.css (single source). Regenerate with
``python scripts/sync_lite_tokens.py``."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_lite_tokens_in_sync() -> None:
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "sync_lite_tokens.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
