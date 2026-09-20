#!/usr/bin/env python3
"""
Embed word+example chunks and load them into Qdrant.

Each point carries two named vectors so hybrid search can run server-side:
    dense  – 384-d cosine vector (semantic meaning)
    bm25   – sparse BM25 vector (exact/lexical text match, IDF-weighted by Qdrant)
plus keyword payload indexes on kanji_form / reading / meanings for the
exact-match arm.

Reads:   data/processed/chunks.json
Writes:  Qdrant collection 'jmdict_chunks' (or QDRANT_COLLECTION from .env)

Usage:
    python scripts/ingest.py                  # all ~219k JMdict entries (~1 hr)
    python scripts/ingest.py --common         # ~37k common/with-examples subset (quick test)
    python scripts/ingest.py --limit 1000     # first 1000 for quick testing
    python scripts/ingest.py --common --freq-band 48  # widen the subset's nf-band cutoff
"""

import argparse
import json
import logging
import sys
from itertools import batched
from pathlib import Path

from qdrant_client.models import (
    Distance,
    Modifier,
    PayloadSchemaType,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import COLLECTION, DENSE_VECTOR, PROC_DIR, QDRANT_URL, SPARSE_VECTOR, qdrant_client  # noqa: E402
from app.embedder import VECTOR_DIM, embed_documents  # noqa: E402

log = logging.getLogger(__name__)

BATCH_SIZE = 256
CHUNKS_PATH = PROC_DIR / "chunks.json"
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


def recreate_collection(client) -> None:
    if client.collection_exists(COLLECTION):
        log.info("  Dropping existing collection '%s' …", COLLECTION)
        client.delete_collection(COLLECTION)

    log.info("  Creating collection '%s' (dense %d-d cosine + sparse BM25) …", COLLECTION, VECTOR_DIM)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={DENSE_VECTOR: VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE_VECTOR: SparseVectorParams(modifier=Modifier.IDF)},
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


def to_point(chunk: dict, dense, sparse) -> PointStruct:
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
        },
    )


def run(
    common_only: bool = False,
    limit: int | None = None,
    freq_band_max: int = FREQ_BAND_MAX,
) -> None:
    """Programmatic entry point (used by scripts/startup.py); `main()` is the CLI wrapper."""
    chunks = load_chunks(common_only, limit, freq_band_max)
    total = len(chunks)
    log.info("Loaded %s chunks from %s", f"{total:,}", CHUNKS_PATH.name)

    log.info("Connecting to Qdrant at %s …", QDRANT_URL)
    client = qdrant_client()
    recreate_collection(client)

    log.info("Embedding + uploading (batch=%d) …", BATCH_SIZE)
    step = max(1, total // BATCH_SIZE // 10) * BATCH_SIZE  # ~10 progress logs
    done = 0
    for batch in batched(chunks, BATCH_SIZE):
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
        client.upsert(
            COLLECTION,
            points=[to_point(c, d, s) for c, (d, s) in zip(batch, vectors, strict=True)],
        )
        done += len(batch)
        if done % step < BATCH_SIZE or done == total:
            log.info("  %d%%  (%s / %s)", done * 100 // total, f"{done:,}", f"{total:,}")

    count = client.count(COLLECTION).count
    log.info("Ingest complete. Collection '%s' → %s points.", COLLECTION, f"{count:,}")


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
        "--freq-band", type=int, default=FREQ_BAND_MAX, metavar="N",
        help=f"with --common, also include entries with an nf band ≤ N (default {FREQ_BAND_MAX} ≈ top ~12k)",
    )
    args = parser.parse_args()
    run(args.common, args.limit, args.freq_band)


if __name__ == "__main__":
    main()
