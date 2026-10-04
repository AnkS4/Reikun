#!/usr/bin/env python3
"""Docker entrypoint + ingestion pipeline.

The serving container only serves: uvicorn runs app.api:app. Ingestion is a
separate job/command (the flags below), not part of every boot.

Pipeline: wait for Qdrant → decide what work is needed → (download → build →)
ingest → launch the API. Each data stage wraps an existing script's entry
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
    reikun                                 # console script (container CMD): serve the API
    python scripts/startup.py              # boot the API (ingestion is opt-in)
    python scripts/startup.py --ingest     # run the pipeline, then serve (env: INGEST_VIA_DOCKER=1)
    python scripts/startup.py --ingest-only  # run the pipeline, don't launch the API
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qdrant_client import QdrantClient  # noqa: E402

from app.config import CHUNKS_SCHEMA, COLLECTION, PROC_DIR, QDRANT_API_KEY, QDRANT_URL, qdrant_client  # noqa: E402
from scripts import download_edrdg, download_kanjivg, ingest  # noqa: E402

log = logging.getLogger(__name__)


def wait_for_qdrant(retries: int = 30, delay_s: float = 2.0) -> None:
    """Fail until Qdrant answers — retries give the container time to boot.

    Uses a throwaway short-timeout client: the shared `qdrant_client()` is
    cached per process, and ingest needs its full timeout for bulk uploads."""
    probe = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=2)
    for attempt in range(1, retries + 1):
        try:
            probe.get_collections()
            return
        except Exception as exc:
            if attempt == retries:
                raise
            log.info("Waiting for Qdrant (%d/%d): %s", attempt, retries, exc)
            time.sleep(delay_s)


def check_state() -> str:
    """'full' (no processed data), 'ingest' (current chunks, empty collection),
    'build' (populated but a runtime artifact is missing), or 'ready'.

    Qdrant is checked first: on hosts with ephemeral disks (e.g. Render) the
    container filesystem is wiped on each deploy, but a populated collection in
    Qdrant Cloud means ingestion can be skipped entirely. The app only needs
    kanji_table.json at runtime; it is baked into the image from the repo.
    """
    try:
        client = qdrant_client()
        count = client.count(COLLECTION).count if client.collection_exists(COLLECTION) else 0
    except Exception as exc:
        log.warning("check-state: Qdrant check failed, treating as needs-ingest (%s)", exc)
        count = 0
    if count:
        # Prefer ingest.meta.json's stamped post-run count — an intentional
        # --common/--limit subset is legitimately smaller than the corpus, so
        # comparing against chunks.meta.json's full entries would misfire on
        # every boot. The chunks sidecar is the fallback for collections that
        # predate the stamp.
        expected = (_meta_json("ingest.meta.json") or {}).get("points") \
            or (_meta_json("chunks.meta.json") or {}).get("entries")
        if expected and count < expected:
            # A mid-upload crash leaves a partial collection that would serve
            # silently truncated results. Warn-only rather than self-heal:
            # we can't distinguish a crash from a deliberately small scope.
            log.warning("Collection looks partial — %s points < %s entries; "
                        "a full --ingest rebuilds it.", f"{count:,}", f"{expected:,}")
        return "ready" if (PROC_DIR / "kanji_table.json").exists() else "build"
    return "ingest" if _chunks_current() else "full"


def _meta_json(name: str) -> dict | None:
    """A data/processed/*.meta.json sidecar — absent on pre-stamping builds,
    unparseable on a truncated write."""
    try:
        return json.loads((PROC_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _chunks_current() -> bool:
    """chunks.json exists AND its sidecar says the current schema wrote it.

    Existence alone is not enough — a pre-v2 file crash-looped ingest on
    KeyError ('gloss_keys'), restarting until restart: on-failure gave up
    (Issues.md D5). Missing/unparseable sidecar → rebuild instead."""
    meta = _meta_json("chunks.meta.json")
    return ingest.CHUNKS_PATH.exists() and meta is not None and meta.get("schema") == CHUNKS_SCHEMA


def _retry(call, *, retries: int, delay_s: float, name: str):
    """Run `call()` with retries — used for the network-bound stages."""
    for attempt in range(1, retries + 1):
        try:
            return call()
        except Exception:
            if attempt == retries:
                raise
            log.warning("%s failed (attempt %d/%d) — retrying in %.0fs", name, attempt, retries, delay_s)
            time.sleep(delay_s)


# Persisted so a run of soft-failed refreshes is inspectable (and could feed a
# dashboard tile) — WARNING logs alone get missed over time.
REFRESH_STATUS = PROC_DIR / "refresh_status.json"


def _refresh_status(outcome: str, detail: str = "") -> None:
    try:
        REFRESH_STATUS.write_text(json.dumps({
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "outcome": outcome, "detail": detail,
        }, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _refresh_in_place() -> None:
    """Top-up path for a populated collection: rsync refreshes the EDRDG XML
    (delta — near-instant when unchanged), and only an upstream change
    rebuilds chunks and upserts the new entry ids. Soft-fails throughout:
    the lean runtime image has no rsync/dev deps, so it just logs and keeps
    serving what it already has."""
    try:
        download_edrdg.check_rsync_available()
    except RuntimeError as exc:
        log.info("Refresh skipped — %s", exc)
        _refresh_status("skipped", str(exc))
        return
    try:
        changed = _retry(download_edrdg.main, retries=2, delay_s=30, name="download-edrdg")
    except Exception as exc:
        log.warning("EDRDG refresh failed (%s) — serving existing data.", exc)
        _refresh_status("failed", str(exc))
        return
    if not changed:
        log.info("Upstream unchanged — collection already current.")
        _refresh_status("unchanged")
        return
    try:
        from scripts import build_chunks  # wordfreq is a dev dep — absent in lean images
        if not build_chunks.outputs_current():
            build_chunks.main()
        _retry(partial(ingest.run, update=True), retries=2, delay_s=60, name="ingest-update")
    except Exception as exc:
        log.warning("Refresh update failed (%s) — serving existing data.", exc)
        _refresh_status("failed", str(exc))
        return
    _refresh_status("updated")


def ingest_pipeline() -> None:
    wait_for_qdrant()
    state = check_state()
    if state == "ready":
        _refresh_in_place()
        return
    if state == "build":
        # Populated collection but a runtime artifact (kanji_table.json) is
        # missing — rebuild just the outputs; the collection is healthy, so
        # never run an ingest against it. A wiped ephemeral disk takes
        # data/raw/ too — re-fetch it first so this path self-heals instead
        # of degrading until the next full ingest.
        try:
            from scripts import build_chunks
            missing = [x for x in (build_chunks.JMDICT_XML, build_chunks.KANJIDIC_XML)
                       if not (build_chunks.RAW_DIR / x).exists()]
            if missing:
                log.info("Raw XML missing (%s) — re-fetching from EDRDG …", ", ".join(missing))
                try:
                    download_edrdg.main()
                except Exception as exc:
                    log.warning("EDRDG re-fetch failed (%s)", exc)
            build_chunks.main()
        except Exception as exc:
            log.warning("Couldn't rebuild runtime artifacts (%s) — serving anyway; kanji lookups will fail.", exc)
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
    parser.add_argument("--ingest-only", action="store_true", help="run the pipeline, don't launch the API")
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

    port = os.getenv("PORT", "8000")
    log.info("Launching the API (uvicorn app.api:app) on 0.0.0.0:%s …", port)
    # exec, don't spawn: uvicorn replaces this process (PID 1 in Docker), so
    # `docker stop`'s SIGTERM reaches it directly and it shuts down cleanly
    # instead of being orphaned until the SIGKILL timeout.
    # One worker: embedding/Sudachi are per-process — N workers would load N
    # copies of the models. FastAPI runs the plain-def endpoints on its
    # threadpool, so a single process still serves concurrent requests; the
    # platform scales by adding instances (Plan.md Phase-1 note).
    os.execvp("uvicorn", [
        "uvicorn", "app.api:app",
        "--host", "0.0.0.0",
        "--port", port,
    ])


if __name__ == "__main__":
    main()
