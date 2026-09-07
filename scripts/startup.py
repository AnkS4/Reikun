#!/usr/bin/env python3
"""Docker entrypoint + Prefect ingestion flow.

Flow: wait for Qdrant → decide what work is needed → (download → build →)
ingest → launch Streamlit. Runs in ephemeral mode — no Prefect server needed.

Each data stage wraps an existing script's entry point, so every step stays
independently runnable for debugging:
    uv run python scripts/download_data.py
    uv run python scripts/build_chunks.py
    uv run python scripts/ingest.py

Usage:
    python scripts/startup.py                # full startup (container default)
    python scripts/startup.py --ingest-only  # run the flow, don't launch Streamlit
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prefect import flow, task  # noqa: E402

from app.config import COLLECTION, PROC_DIR, qdrant_client  # noqa: E402
from scripts import build_chunks, download_data, ingest  # noqa: E402


@task(name="wait-for-qdrant", retries=30, retry_delay_seconds=2)
def wait_for_qdrant() -> None:
    """Fail until Qdrant answers — retries give the container time to boot."""
    qdrant_client(timeout=2).get_collections()


@task(name="check-state")
def check_state() -> str:
    """'full' (no processed data), 'ingest' (data but empty collection), or 'ready'."""
    if not (PROC_DIR / "chunks.json").exists():
        return "full"
    try:
        client = qdrant_client()
        if not (client.collection_exists(COLLECTION) and client.count(COLLECTION).count > 0):
            return "ingest"
    except Exception:
        return "ingest"  # can't tell → try; load() retries if Qdrant hiccups
    return "ready"


@task(name="download-data", retries=2, retry_delay_seconds=30,
      description="Fetch JMdict/KANJIDIC2/KanjiVG release assets into data/raw and data/kanjivg.")
def download() -> None:
    download_data.main()


@task(name="build-chunks", retries=0,  # deterministic parse over local files — retrying won't help
      description="Parse raw JSON into data/processed/{chunks,kanji_table}.json.")
def build() -> None:
    build_chunks.main()


@task(name="ingest-qdrant", retries=2, retry_delay_seconds=60,
      description="Embed chunks and (re)create the Qdrant collection. Safe to retry: "
                  "ingest drops and recreates the collection on every run.")
def load() -> None:
    ingest.run()


@flow(name="reikun-ingest", log_prints=True)
def ingest_pipeline() -> None:
    wait_for_qdrant()
    state = check_state()
    if state == "ready":
        print("Data already ingested — nothing to do.")
        return
    if state == "full":
        download()
        build()
    load()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ingest-only", action="store_true", help="run the pipeline, don't launch Streamlit")
    args = parser.parse_args()

    print("Starting Reikun …")
    try:
        ingest_pipeline()
    except Exception as exc:  # prefect raises on a failed terminal state
        print(f"✗ Ingestion pipeline failed: {exc}")
        sys.exit(1)

    if args.ingest_only:
        return
    print("Launching Streamlit …")
    subprocess.run(["streamlit", "run", "app/streamlit_app.py"], check=False)


if __name__ == "__main__":
    main()
