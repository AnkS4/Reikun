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
    python scripts/ingest.py --update --reuse-vectors   # payload-only refresh — minutes, no re-embed
    python scripts/ingest.py --seed-from URL  # fresh build here from another instance's vectors
    python scripts/ingest.py --common         # ~37k common/with-examples subset (quick test)
    python scripts/ingest.py --limit 1000     # first 1000 for quick testing
    python scripts/ingest.py --common --freq-band 48  # widen the subset's nf-band cutoff
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from itertools import batched
from pathlib import Path

from qdrant_client import QdrantClient
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

from app.config import (
    COLLECTION,
    DENSE_VECTOR,
    PROC_DIR,
    QDRANT_TIMEOUT,
    QDRANT_URL,
    SPARSE_VECTOR,
    qdrant_client,
)
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


_INDEX_FIELDS = ("kanji_form", "reading", "gloss_keys", "primary_gloss_keys",
                 "head_gloss_keys", "kanji_forms", "readings", "infl_forms")

# wf_score/commonness feed the FormulaQuery mult expressions — strict mode
# (Qdrant Cloud default) requires an index on every filtered/formula field.
_FORMULA_FIELDS = ("wf_score", "commonness")


def _ensure_indexes(client) -> None:
    for field in (*_INDEX_FIELDS, *_FORMULA_FIELDS):
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.KEYWORD
                                    if field in _INDEX_FIELDS else PayloadSchemaType.FLOAT)


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
    # (斑馬, シマウマ …); infl_forms holds the inflected forms
    # (走った, 走りません) so typing a conjugation exact-matches its entry.
    for field in _INDEX_FIELDS:
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.KEYWORD)
    # wf_score/commonness feed the FormulaQuery mult expressions — strict mode
    # (Qdrant Cloud default) requires an index on every filtered/formula field.
    for field in _FORMULA_FIELDS:
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.FLOAT)


def chunk_sig(chunk: dict) -> str:
    """Content fingerprint over everything that lands in the point (payload
    fields + the text the vectors embed) — --update diffs on it, so upstream
    edits to an existing entry get re-upserted, not just added/deleted."""
    blob = json.dumps(chunk, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode()).hexdigest()[:16]


def _payload(chunk: dict, sig: str) -> dict:
    return {
        "kanji_form": chunk.get("kanji_form"),
        "reading": chunk["reading"],
        "meanings": chunk["meanings"],
        "gloss_keys": chunk["gloss_keys"],
        "primary_gloss_keys": chunk.get("primary_gloss_keys", []),
        # First gloss of the first sense — the headline translation, used by
        # the HEAD_BONUS term of the en_word formula (see app/retrieval.py).
        "head_gloss_keys": chunk.get("head_gloss_keys", []),
        "example_sentences": chunk["example_sentences"],
        "is_common": chunk.get("is_common", False),
        "commonness": chunk.get("commonness", 0.0),
        "wf_score": chunk.get("wf_score", 0.0),
        "text": chunk["text"],
        # All variant forms — keyword-indexed for exact match on alternates.
        "kanji_forms": chunk.get("kanji_forms", []),
        "readings": chunk.get("readings", []),
        # Conjugation table (verb/adjective entries — never in sparse_text, so
        # vectors don't depend on it): inflected_forms are the render rows for
        # word cards; infl_forms flat strings let a typed inflection (走った)
        # exact-match the entry via the infl_forms keyword index.
        "inflected_forms": chunk.get("inflected_forms", []),
        "infl_forms": chunk.get("infl_forms", []),
        "freq_band": chunk.get("freq_band"),
        "related": chunk.get("related", []),
        "lsource": chunk.get("lsource", []),
        "reading_restrictions": chunk.get("reading_restrictions", {}),
        "notes": chunk.get("notes", []),
        # Content signature — lets --update re-upsert entries whose
        # upstream data changed, not just added/vanished ids.
        "sig": sig if sig is not None else chunk_sig(chunk),
    }


def to_point(chunk: dict, dense, sparse, sig: str | None = None) -> PointStruct:
    return PointStruct(
        id=int(chunk["id"]),
        vector={
            DENSE_VECTOR: dense.tolist(),
            SPARSE_VECTOR: SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
        },
        payload=_payload(chunk, sig if sig is not None else chunk_sig(chunk)),
    )


def to_point_reused(chunk: dict, dense, sparse, sig: str | None = None) -> PointStruct:
    """to_point for vectors scrolled back from a live collection (a
    --reuse-vectors upload) — no numpy round-trip, the stored vectors go
    straight onto the rebuilt point with the new payload."""
    return PointStruct(
        id=int(chunk["id"]),
        vector={DENSE_VECTOR: dense, SPARSE_VECTOR: sparse},
        payload=_payload(chunk, sig if sig is not None else chunk_sig(chunk)),
    )


def _sparse_source(old_payload: dict) -> str:
    """Recompose the BM25 embed input from a stored payload — `sparse_text` is
    built from exactly these fields for points written by the current builder,
    so an equal recomposition proves the stored sparse vector is on-form."""
    forms = ((old_payload.get("kanji_forms") or []) + (old_payload.get("readings") or []))
    return f"{' '.join(forms)}: {', '.join(old_payload.get('meanings') or [])}"


def _reusable(old_payload: dict, chunk: dict) -> tuple[bool, str]:
    """Whether this chunk's dense/BM25 vectors may be transplanted from the
    stored point instead of re-embedded.

    Dense: the embed input is exactly the payload's `meanings` join, so
    payload==chunk means the stored dense vector is on-form.

    Sparse: BM25 embeds forms + meanings, but pre-0.8.0 payloads kept the
    variant lists in an older shape (primaries only in the singular fields),
    so the payload can't prove the stored sparse input byte-for-byte. A
    43-point wire test — random corpus sample plus the report words — verified
    the stored sparse vectors re-encode to the current `sparse_text` exactly,
    so legacy-shape points are accepted on the dense + display-text evidence.
    Points written by the current builder carry `inflected_forms` and must
    pass the strict recomposition, keeping form-sensitive updates correct.
    """
    if ", ".join(old_payload.get("meanings") or []) != ", ".join(chunk["meanings"]):
        return False, "meanings"
    if _sparse_source(old_payload) == (chunk.get("sparse_text") or chunk["text"]):
        return True, ""
    if "inflected_forms" in old_payload:
        return False, "form lists"
    if old_payload.get("text") != chunk["text"]:
        return False, "display text"
    return True, ""


def reuse_vectors_upload(client, todo: list[dict], fresh_sigs: dict[int, str], source=None) -> None:
    """--reuse-vectors: refresh payloads without re-embedding.

    The dense and BM25 vectors depend only on the embed inputs (meanings,
    variant forms) — none of them changed when new payload fields appeared
    (conjugation tables, gloss head-words, wf in the trie). So scroll the
    live vectors back, verify the embed inputs didn't drift by recomposing
    them from the stored payload, and re-upsert with the new payload dicts.
    Chunks whose stored point is missing or whose inputs drifted fall back to
    a fresh embed. ~minutes instead of the ~1 hr full re-embed.

    A snapshot upload was the alternative considered and rejected: snapshots
    transport existing vectors between instances, and these vectors only
    live on the Cloud cluster — snapshotting locally would mean embedding
    everything from scratch first, which is the cost this path avoids.

    `source` re-targets the read side for cross-instance seeding
    (--seed-from): scroll vectors from `source` (e.g. the Cloud cluster)
    while upserting into `client` (e.g. a local build destined for a
    snapshot push) — the checks are the same, so drift still re-embeds
    locally and the snapshot ships proven fingerprints plus current payloads.
    """
    log.info("Reusing server-side vectors (payload-only refresh, batch=%d) …", BATCH_SIZE)
    chunk_by_id = {int(c["id"]): c for c in todo}
    done = 0
    total = len(todo)
    step = max(1, total // BATCH_SIZE // 10) * BATCH_SIZE
    covered: set[int] = set()
    pending: tuple[Future, int] | None = None

    def _await(p: tuple[Future, int]) -> int:
        p[0].result()
        return p[1]

    with ThreadPoolExecutor(max_workers=1) as pool:
        offset = None
        scroll = source or client
        while True:
            page, offset = scroll.scroll(
                COLLECTION, limit=BATCH_SIZE, offset=offset,
                with_payload=PayloadSelectorInclude(
                    include=["meanings", "kanji_forms", "readings", "text", "inflected_forms"]),
                with_vectors=True,
            )
            points: list[PointStruct] = []
            drift: list[tuple[dict, str, str]] = []
            for hit in page:
                cid = int(hit.id)
                chunk = chunk_by_id.get(cid)
                if chunk is None:  # not part of this diff (unchanged or vanished)
                    continue
                covered.add(cid)
                old = hit.payload or {}
                vec = hit.vector or {}
                dense = vec.get(DENSE_VECTOR)
                sparse = vec.get(SPARSE_VECTOR)
                usable, why = _reusable(old, chunk)
                if dense is not None and sparse is not None and usable:
                    points.append(to_point_reused(chunk, dense, sparse, fresh_sigs.get(cid)))
                else:
                    drift.append((chunk, ", ".join(chunk["meanings"]),
                                  chunk.get("sparse_text") or chunk["text"], why))
            if drift:
                reasons = Counter(why for *_, why in drift)
                log.info("  %s drifted embed inputs in this batch — re-embedding (%s)",
                         f"{len(drift):,}",
                         ", ".join(f"{k} {v:,}" for k, v in sorted(reasons.items())))
                for chunk, (d, s) in zip(
                    (t[0] for t in drift),
                    embed_documents((t[1] for t in drift), batch_size=BATCH_SIZE,
                                    sparse_texts=(t[2] for t in drift)),
                    strict=True,
                ):
                    points.append(to_point(chunk, d, s, fresh_sigs.get(int(chunk["id"]))))
            if points:
                if pending is not None:
                    done += _await(pending)
                    if done % step < BATCH_SIZE:
                        log.info("  %d%%  (%s / %s)", done * 100 // total, f"{done:,}", f"{total:,}")
                pending = (pool.submit(client.upsert, COLLECTION, points=points), len(points))
            if offset is None:
                break
        if pending is not None:
            done += _await(pending)
    log.info("  100%%  (%s / %s)", f"{done:,}", f"{total:,}")

    missing = [chunk_by_id[cid] for cid in set(chunk_by_id) - covered]
    if missing:
        # Points the scroll never saw (between-batch inserts, mirror lag) —
        # too few to stream; embed them straight through.
        log.info("  %s ids unseen in the scroll — embedding fresh", f"{len(missing):,}")
        vectors = embed_documents(
            (", ".join(c["meanings"]) for c in missing), batch_size=BATCH_SIZE,
            sparse_texts=(c.get("sparse_text") or c["text"] for c in missing))
        client.upsert(COLLECTION, points=[
            to_point(c, d, s, fresh_sigs.get(int(c["id"]))) for c, (d, s) in zip(missing, vectors, strict=True)])


def run(
    common_only: bool = False,
    limit: int | None = None,
    freq_band_max: int = FREQ_BAND_MAX,
    update: bool = False,
    reuse_vectors: bool = False,
    seed_from: str | None = None,
) -> None:
    """Programmatic entry point (used by scripts/startup.py); `main()` is the CLI wrapper.

    `update` tops up a populated collection instead of rebuilding it: diffs on
    point ids (JMdict ent_seq — stable across rebuilds) plus per-chunk content
    sigs, so new entries embed+upsert, upstream edits to existing entries
    re-upsert, and vanished ids get deleted. Points ingested before sigs
    existed all read as changed — the first --update on such a collection
    re-embeds in place once (no drop, no downtime) to install them.

    `reuse_vectors` (--update only) skips the embed phase for entries whose
    embed inputs are byte-stable in the live collection — payload-only
    refresh. Correct whenever the change touched payload fields but not the
    fields the vectors encode (meanings / variant forms); the helper falls
    back to a fresh embed for any entry it can't verify.

    `seed_from` (URL of another instance) builds THIS instance's collection
    fresh by transplanting the source's stored vectors onto chunks.json
    payloads — fingerprint reuse across instances, no local embedding. The
    snapshot-push flow: seed a local Docker build this way, snapshot it,
    upload, and recover on the Cloud cluster — the cloud then never runs its
    own (hours-long) index build. Same drift checks apply, so anything
    unverified is embedded locally before the snapshot is taken."""
    chunks = load_chunks(common_only, limit, freq_band_max)
    log.info("Loaded %s chunks from %s", f"{len(chunks):,}", CHUNKS_PATH.name)

    log.info("Connecting to Qdrant at %s …", QDRANT_URL)
    client = qdrant_client()

    source_client = None
    if seed_from:
        if update:
            raise ValueError("--seed-from builds a FRESH collection; drop --update")
        source_client = QdrantClient(
            url=seed_from, api_key=os.environ.get("QDRANT_SOURCE_API_KEY") or None,
            timeout=QDRANT_TIMEOUT)
        log.info("  Seed source: %s — vectors transplanted, not recomputed.", seed_from)

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

    if update and client.collection_exists(COLLECTION):
        # A fresh --update may ship payload fields the live collection has no
        # index for yet (infl_forms ...) — create_payload_index is a no-op for
        # fields already indexed, so this runs unconditionally. Strict-mode
        # filtering/formula on an unindexed field is a 400, so this must land
        # BEFORE the first re-upserted point is queryable with it.
        _ensure_indexes(client)

    total = len(todo)
    if (seed_from or (reuse_vectors and update)) and todo:
        reuse_vectors_upload(client, todo, fresh_sigs, source=source_client)
    elif total:
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
    else:
        log.info("Nothing new — collection already matches chunks.json.")

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
    parser.add_argument(
        "--reuse-vectors", action="store_true",
        help="with --update, refresh payloads WITHOUT re-embedding — the stored "
             "dense/BM25 vectors are reused wherever the live embed inputs "
             "match chunks.json (minutes instead of ~1 hr after a payload-only "
             "change; anything drifted is re-embedded)",
    )
    parser.add_argument(
        "--seed-from", type=str, default=None, metavar="URL",
        help="build THIS instance's collection FRESH by transplanting stored vectors from "
             "another instance (e.g. the Cloud cluster) onto current chunks.json payloads — "
             "fingerprint reuse across instances, no local embedding; source key via "
             "QDRANT_SOURCE_API_KEY. Snapshot-push flow: seed a local Docker build, snapshot, "
             "upload, recover on the Cloud cluster.",
    )
    args = parser.parse_args()
    run(args.common, args.limit, args.freq_band, update=args.update,
        reuse_vectors=args.reuse_vectors, seed_from=args.seed_from)


if __name__ == "__main__":
    main()
