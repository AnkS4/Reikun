#!/usr/bin/env python3
"""
Embed word+example chunks and load them into Qdrant.

Each point carries two named vectors so hybrid search can run server-side:
    dense  - 384-d cosine vector (semantic meaning)
    bm25   - sparse BM25 vector (exact/lexical text match, IDF-weighted by Qdrant)
plus keyword payload indexes on kanji_form / reading / meanings for the
exact-match arm.

Reads:   data/processed/chunks.json
Writes:  Qdrant collection 'jmdict_chunks' (or QDRANT_COLLECTION from .env)

Usage:
    python scripts/ingest.py                  # all ~219k JMdict entries (~1 hr)
    python scripts/ingest.py --update         # top-up: upsert new/edited ids, delete vanished
    python scripts/ingest.py --common         # ~37k common/with-examples subset (quick test)
    python scripts/ingest.py --limit 1000     # first 1000 for quick testing
    python scripts/ingest.py --common --freq-band 48  # widen the subset's nf-band cutoff
"""

import argparse
import hashlib
import json
import logging
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from itertools import batched
from pathlib import Path

from qdrant_client.models import (
    Distance,
    Modifier,
    OptimizersConfigDiff,
    PayloadSchemaType,
    PayloadSelectorInclude,
    PointIdsList,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import COLLECTION, DENSE_VECTOR, PROC_DIR, QDRANT_URL, SPARSE_VECTOR, qdrant_client
from app.embedder import VECTOR_DIM, embed_documents

log = logging.getLogger(__name__)

BATCH_SIZE = 256
CHUNKS_PATH = PROC_DIR / "chunks.json"
# Qdrant's default indexing_threshold (KB of vectors per segment before HNSW
# is built). Set to 0 for the bulk upload so segments aren't re-indexed as
# they fill, then restored — the documented fast path for bulk loads.
INDEXING_THRESHOLD_KB = 20_000
# The --common subset filter: entries with example sentences, a common flag, or
# an nf band at or under this cutoff (nfNN ≈ each band = 500 words, so 24 ≈ top
# ~12k by frequency). Rare markerless entries like 縞馬 are outside it — they
# only land in a default (all-entries) ingest.
FREQ_BAND_MAX = 24


def load_chunks(
    common_only: bool = False,
    limit: int | None = None,
    freq_band_max: int = FREQ_BAND_MAX,
) -> list[dict]:
    """Load processed chunks — all of them, or the --common subset."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing: {CHUNKS_PATH}\nRun  python scripts/build_chunks.py  first.")
    chunks: list[dict] = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if common_only:
        chunks = [
            c
            for c in chunks
            if c.get("example_sentences")
            or c.get("is_common")
            or (c.get("freq_band") or 999) <= freq_band_max
        ]
    return chunks[:limit] if limit else chunks


def _point_sigs(client) -> dict[int, str | None]:
    """id → stored chunk signature — None on points ingested before sigs
    existed. Scrolls with only the one sig payload field, so ~220k rows is a
    few cheap pages instead of a full payload transfer."""
    sigs: dict[int, str | None] = {}
    offset = None
    while True:
        page, offset = client.scroll(
            COLLECTION, limit=10_000, offset=offset,
            with_payload=PayloadSelectorInclude(include=["sig"]), with_vectors=False,
        )
        sigs.update({int(p.id): (p.payload or {}).get("sig") for p in page})
        if offset is None:
            return sigs


def recreate_collection(client) -> None:
    if client.collection_exists(COLLECTION):
        log.info("  Dropping existing collection '%s' …", COLLECTION)
        client.delete_collection(COLLECTION)

    log.info("  Creating collection '%s' (dense %d-d cosine + sparse BM25) …", COLLECTION, VECTOR_DIM)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={DENSE_VECTOR: VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE_VECTOR: SparseVectorParams(modifier=Modifier.IDF)},
        optimizers_config=OptimizersConfigDiff(indexing_threshold=0),  # see INDEXING_THRESHOLD_KB
    )
    # gloss_keys (normalised meanings) drives the exact-match arm for English
    # queries; kanji_form/reading cover Japanese input; kanji_forms/readings
    # hold every variant form so exact match also fires on alternates
    # (斑馬, シマウマ …).
    for field in ("kanji_form", "reading", "gloss_keys", "primary_gloss_keys",
                  "kanji_forms", "readings"):
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.KEYWORD)
    # wf_score/commonness feed the FormulaQuery mult expressions — strict mode
    # (Qdrant Cloud default) requires an index on every filtered/formula field.
    for field in ("wf_score", "commonness"):
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.FLOAT)


def chunk_sig(chunk: dict) -> str:
    """Content fingerprint over everything that lands in the point (payload
    fields + the text the vectors embed) — --update diffs on it, so upstream
    edits to an existing entry get re-upserted, not just added/deleted."""
    blob = json.dumps(chunk, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def to_point(chunk: dict, dense, sparse, sig: str | None = None) -> PointStruct:
    return PointStruct(
        id=int(chunk["id"]),
        vector={
            DENSE_VECTOR: dense.tolist(),
            SPARSE_VECTOR: SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
        },
        payload={
            "kanji_form": chunk.get("kanji_form"),
            "reading": chunk["reading"],
            "meanings": chunk["meanings"],
            "gloss_keys": chunk["gloss_keys"],
            "primary_gloss_keys": chunk.get("primary_gloss_keys", []),
            "example_sentences": chunk["example_sentences"],
            "is_common": chunk.get("is_common", False),
            "commonness": chunk.get("commonness", 0.0),
            "wf_score": chunk.get("wf_score", 0.0),
            "text": chunk["text"],
            # All variant forms — keyword-indexed for exact match on alternates.
            "kanji_forms": chunk.get("kanji_forms", []),
            "readings": chunk.get("readings", []),
            "freq_band": chunk.get("freq_band"),
            "related": chunk.get("related", []),
            "lsource": chunk.get("lsource", []),
            "reading_restrictions": chunk.get("reading_restrictions", {}),
            "notes": chunk.get("notes", []),
            # Content signature — lets --update re-upsert entries whose
            # upstream data changed, not just added/vanished ids.
            "sig": sig if sig is not None else chunk_sig(chunk),
        },
    )


def run(
    common_only: bool = False,
    limit: int | None = None,
    freq_band_max: int = FREQ_BAND_MAX,
    update: bool = False,
) -> None:
    """Programmatic entry point (used by scripts/startup.py); `main()` is the CLI wrapper.

    `update` tops up a populated collection instead of rebuilding it: diffs on
    point ids (JMdict ent_seq — stable across rebuilds) plus per-chunk content
    sigs, so new entries embed+upsert, upstream edits to existing entries
    re-upsert, and vanished ids get deleted. Points ingested before sigs
    existed all read as changed — the first --update on such a collection
    re-embeds in place once (no drop, no downtime) to install them."""
    chunks = load_chunks(common_only, limit, freq_band_max)
    log.info("Loaded %s chunks from %s", f"{len(chunks):,}", CHUNKS_PATH.name)

    log.info("Connecting to Qdrant at %s …", QDRANT_URL)
    client = qdrant_client()

    stale: list[int] = []
    fresh_sigs: dict[int, str] = {}
    if update and client.collection_exists(COLLECTION):
        have = _point_sigs(client)
        fresh = {int(c["id"]) for c in chunks}
        new_ids = fresh - set(have)
        # Only a full-corpus update may reconcile deletes — under a --common /
        # --limit subset every out-of-subset id would read as "vanished".
        if not common_only and limit is None:
            stale = sorted(set(have) - fresh)
        # Sig computed once during the diff and stashed for to_point — a
        # json.dumps+sha1 over the whole chunk dict is the update path's one
        # non-trivial per-entry cost, so changed entries shouldn't pay twice.
        todo = []
        for c in chunks:
            cid = int(c["id"])
            if cid in new_ids:
                todo.append(c)
            elif have[cid] != (sig := chunk_sig(c)):
                fresh_sigs[cid] = sig
                todo.append(c)
        log.info("  Update: %s new + %s changed → %s upserts, %s vanished",
                 f"{len(new_ids):,}", f"{len(todo) - len(new_ids):,}",
                 f"{len(todo):,}", f"{len(stale):,}")
    else:
        recreate_collection(client)
        todo = chunks

    total = len(todo)
    if not total:
        log.info("Nothing new — collection already matches chunks.json.")
    else:
        try:
            log.info("Embedding + uploading (batch=%d) …", BATCH_SIZE)
            step = max(1, total // BATCH_SIZE // 10) * BATCH_SIZE  # ~10 progress logs
            done = 0
            # One upsert in flight while the next batch embeds: the CPU-bound embed
            # and the network-bound upload no longer serialise. A single worker
            # bounds memory to one pending batch of points.
            pending: tuple[Future, int] | None = None  # (upsert future, batch length)

            def _await(p: tuple[Future, int]) -> int:
                p[0].result()  # surfaces upload errors before queuing more
                return p[1]

            with ThreadPoolExecutor(max_workers=1) as pool:
                for batch in batched(todo, BATCH_SIZE, strict=False):
                    vectors = embed_documents(
                        # Dense: glosses only — the dense model only ever sees English
                        # queries (the `ja` route skips it), so headword/reading add
                        # noise, not signal.
                        (", ".join(c["meanings"]) for c in batch),
                        batch_size=BATCH_SIZE,
                        # Sparse: all variant forms + readings + glosses — BM25 must index
                        # every headword variant or the BM25-only Japanese route misses
                        # alternate forms (しまうま → 縞馬, 斑馬 → 縞馬).
                        sparse_texts=(c.get("sparse_text") or c["text"] for c in batch),
                    )
                    points = [to_point(c, d, s, fresh_sigs.get(int(c["id"])))
                              for c, (d, s) in zip(batch, vectors, strict=True)]
                    if pending is not None:
                        done += _await(pending)
                        if done % step < BATCH_SIZE:
                            log.info("  %d%%  (%s / %s)", done * 100 // total, f"{done:,}", f"{total:,}")
                    pending = (pool.submit(client.upsert, COLLECTION, points=points), len(batch))
                if pending is not None:
                    done += _await(pending)
            log.info("  100%%  (%s / %s)", f"{done:,}", f"{total:,}")
        except BaseException:
            # A full ingest that dies mid-upload leaves a partial collection —
            # with indexing_threshold=0 AND count>0, check_state() would call it
            # "ready" and serve silently truncated results. Drop it so the next
            # boot re-ingests cleanly. Update mode is exempt: upserts keep the
            # collection consistent at every point.
            if not update and client.collection_exists(COLLECTION):
                log.error("Ingest died mid-upload — dropping partial collection so it can't serve truncated data")
                client.delete_collection(COLLECTION)
            raise

    if stale:
        client.delete(COLLECTION, points_selector=PointIdsList(points=stale))
        log.info("  Removed %s points for entries that left JMdict.", f"{len(stale):,}")

    if not update:
        # Bulk-load only: indexing was disabled for the upload. Update mode
        # touches a small delta — the live index handles it fine.
        log.info("  Re-enabling HNSW indexing (threshold %d KB) …", INDEXING_THRESHOLD_KB)
        client.update_collection(
            COLLECTION, optimizers_config=OptimizersConfigDiff(indexing_threshold=INDEXING_THRESHOLD_KB)
        )

    count = client.count(COLLECTION).count
    log.info("Ingest complete. Collection '%s' → %s points (HNSW builds in the background).", COLLECTION, f"{count:,}")
    # Stamp what a healthy collection looks like — check_state() compares the
    # live point count against this rather than chunks.meta.json's full-corpus
    # entries, so an intentional --common/--limit subset isn't "partial" forever.
    try:
        (PROC_DIR / "ingest.meta.json").write_text(json.dumps({
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "points": count,
            "scope": "update" if update else ("subset" if common_only or limit else "full"),
        }, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Ingest JMdict chunks into Qdrant.")
    parser.add_argument(
        "--common", action="store_true",
        help="ingest only the common/with-examples/nf-band subset (~37k) instead of all ~219k — quick testing",
    )
    parser.add_argument("--limit", type=int, default=None, help="cap the number of entries (testing)")
    parser.add_argument(
        "--update", action="store_true",
        help="top up a populated collection — upsert new + content-changed ids, delete vanished "
             "ones, no drop/recreate (first run on a pre-signature collection re-embeds once)",
    )
    parser.add_argument(
        "--freq-band", type=int, default=FREQ_BAND_MAX, metavar="N",
        help=f"with --common, also include entries with an nf band ≤ N (default {FREQ_BAND_MAX} ≈ top ~12k)",
    )
    args = parser.parse_args()
    run(args.common, args.limit, args.freq_band, update=args.update)


if __name__ == "__main__":
    main()
