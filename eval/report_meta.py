"""Provenance stamp shared by every report writer.

A report in `eval/reports/` should answer three questions on sight: when was
it generated, from which app version, and from which commit — plus the
configuration the run used. Every writer in `eval/` stamps its output with
`report_meta()` so those facts travel with the file instead of living only
in the author's head.
"""

import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def app_version() -> str:
    """Release version from pyproject.toml (same source the OpenAPI export uses)."""
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def git_commit() -> str:
    """Short SHA, plus '+dirty' when the worktree differs from it."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


def report_meta(**extra) -> dict:
    """Stamp: generation time, app version, commit — plus any run specifics."""
    meta = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "version": app_version(),
        "commit": git_commit(),
    }
    meta.update(extra)
    return meta


def stamp_line(meta: dict) -> str:
    """One-line provenance banner for a markdown report."""
    return " · ".join(f"{k}={v}" for k, v in meta.items())
