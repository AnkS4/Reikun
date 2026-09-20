#!/usr/bin/env python3
"""Docker entrypoint + ingestion pipeline.

Pipeline: wait for Qdrant → decide what work is needed → (download → build →)
ingest → launch Streamlit. Each data stage wraps an existing script's entry
point, so every step stays independently runnable for debugging:
    uv run python scripts/download_edrdg.py      # JMdict NG + KANJIDIC2 XML
    uv run python scripts/download_kanjivg.py    # KanjiVG stroke-order SVGs
    uv run python scripts/build_chunks.py
    uv run python scripts/ingest.py

Plain Python, no orchestrator: a four-step linear pipeline doesn't need one,
and on memory-tight hosts (Render's free tier) a workflow engine's ~150–350
MB overhead plus a cloud dependency is the difference between fitting and
timing out.

Usage:
    reikun                                 # console script (container CMD)
    python scripts/startup.py              # boot the app (ingestion is opt-in)
    python scripts/startup.py --ingest     # run the pipeline, then Streamlit (env: INGEST_VIA_DOCKER=1)
    python scripts/startup.py --ingest-only  # run the pipeline, don't launch Streamlit
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import COLLECTION, PROC_DIR, qdrant_client  # noqa: E402
from scripts import download_edrdg, download_kanjivg, ingest  # noqa: E402

log = logging.getLogger(__name__)


def wait_for_qdrant(retries: int = 30, delay_s: float = 2.0) -> None:
    """Fail until Qdrant answers — retries give the container time to boot."""
    for attempt in range(1, retries + 1):
        try:
            qdrant_client(timeout=2).get_collections()
            return
        except Exception as exc:
            if attempt == retries:
                raise
            log.info("Waiting for Qdrant (%d/%d): %s", attempt, retries, exc)
            time.sleep(delay_s)


def check_state() -> str:
    """'full' (no processed data), 'ingest' (chunks but empty collection), or 'ready'.

    Qdrant is checked first: on hosts with ephemeral disks (e.g. Render) the
    container filesystem is wiped on each deploy, but a populated collection in
    Qdrant Cloud means ingestion can be skipped entirely. The app only needs
    kanji_table.json at runtime; it is baked into the image from the repo.
    """
    try:
        client = qdrant_client()
        populated = client.collection_exists(COLLECTION) and client.count(COLLECTION).count > 0
    except Exception as exc:
        log.warning("check-state: Qdrant check failed, treating as needs-ingest (%s)", exc)
        populated = False
    if populated and (PROC_DIR / "kanji_table.json").exists():
        return "ready"
    if (PROC_DIR / "chunks.json").exists():
        return "ingest"
    return "full"


def _retry(call, *, retries: int, delay_s: float, name: str) -> None:
    """Run `call()` with retries — used for the network-bound stages."""
    for attempt in range(1, retries + 1):
        try:
            call()
            return
        except Exception:
            if attempt == retries:
                raise
            log.warning("%s failed (attempt %d/%d) — retrying in %.0fs", name, attempt, retries, delay_s)
            time.sleep(delay_s)


def ingest_pipeline() -> None:
    wait_for_qdrant()
    state = check_state()
    if state == "ready":
        log.info("Data already ingested — nothing to do.")
        return
    if state == "full":
        # build_chunks needs wordfreq — a dev-group dep absent from the
        # runtime image, so in-container rebuilds only work where dev deps
        # are installed (otherwise run the pipeline off-host and restart).
        from scripts import build_chunks

        # downloads are network-bound → retry; build is a deterministic local
        # parse → retrying wouldn't help.
        _retry(download_edrdg.main, retries=2, delay_s=30, name="download-edrdg")
        _retry(download_kanjivg.main, retries=2, delay_s=30, name="download-kanjivg")
        build_chunks.main()
    # ingest drops and recreates the collection on every run, so it's safe to retry.
    _retry(ingest.run, retries=2, delay_s=60, name="ingest-qdrant")


def _env_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--ingest", action="store_true",
        help="check/populate Qdrant before launching (env: INGEST_VIA_DOCKER=1)",
    )
    parser.add_argument("--ingest-only", action="store_true", help="run the pipeline, don't launch Streamlit")
    args = parser.parse_args()

    log.info("Starting Reikun …")

    if args.ingest or args.ingest_only or _env_truthy(os.getenv("INGEST_VIA_DOCKER")):
        try:
            ingest_pipeline()
        except Exception:
            log.exception("Ingestion pipeline failed")
            sys.exit(1)
    else:
        log.info("Ingestion off (set INGEST_VIA_DOCKER=1 or --ingest to enable) — booting straight to the app.")

    if args.ingest_only:
        return

    port = os.getenv("PORT", "8501")
    log.info("Launching Streamlit + API (mounted at /api) on 0.0.0.0:%s …", port)
    # exec, don't spawn: Streamlit replaces this process (PID 1 in Docker), so
    # `docker stop`'s SIGTERM reaches it directly and it shuts down cleanly
    # instead of being orphaned until the SIGKILL timeout.
    os.execvp("streamlit", [
        "streamlit", "run", str(Path(__file__).resolve().parents[1] / "app" / "asgi_app.py"),
        "--server.address", "0.0.0.0",
        "--server.port", port,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    main()
