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
    python scripts/ingest.py              # entries with example sentences or common tag (~37k)
    python scripts/ingest.py --all        # all ~218k JMdict entries
    python scripts/ingest.py --limit 1000 # first 1000 for quick testing
"""

import argparse
import json
import sys
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

BATCH_SIZE = 256
CHUNKS_PATH = PROC_DIR / "chunks.json"


def load_chunks(ingest_all: bool = False, limit: int | None = None) -> list[dict]:
    """Load processed chunks, optionally filtered to entries worth searching."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing: {CHUNKS_PATH}\nRun  python scripts/build_chunks.py  first.")
    chunks: list[dict] = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if not ingest_all:
        chunks = [c for c in chunks if c.get("example_sentences") or c.get("is_common")]
    return chunks[:limit] if limit else chunks


def recreate_collection(client) -> None:
    if client.collection_exists(COLLECTION):
        print(f"  Dropping existing collection '{COLLECTION}' …")
        client.delete_collection(COLLECTION)

    print(f"  Creating collection '{COLLECTION}' (dense {VECTOR_DIM}-d cosine + sparse BM25) …")
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={DENSE_VECTOR: VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE_VECTOR: SparseVectorParams(modifier=Modifier.IDF)},
    )
    for field in ("kanji_form", "reading", "meanings"):
        client.create_payload_index(COLLECTION, field, PayloadSchemaType.KEYWORD)


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
            "example_sentences": chunk["example_sentences"],
            "is_common": chunk.get("is_common", False),
            "text": chunk["text"],
        },
    )


def run(ingest_all: bool = False, limit: int | None = None) -> None:
    """Programmatic entry point (used by the Prefect flow); `main()` is the CLI wrapper."""
    chunks = load_chunks(ingest_all, limit)
    total = len(chunks)
    print(f"Loaded {total:,} chunks from {CHUNKS_PATH.name}")

    print(f"Connecting to Qdrant at {QDRANT_URL} …", flush=True)
    client = qdrant_client()
    recreate_collection(client)

    print(f"Embedding + uploading (batch={BATCH_SIZE}) …", flush=True)
    for start in range(0, total, BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        vectors = embed_documents((c["text"] for c in batch), batch_size=BATCH_SIZE)
        client.upsert(COLLECTION, points=[to_point(c, d, s) for c, (d, s) in zip(batch, vectors)])
        done = min(start + BATCH_SIZE, total)
        print(f"\r  {done * 100 // total:3d}%  ({done:,} / {total:,})", end="", flush=True)

    count = client.count(COLLECTION).count
    print(f"\n\n✓ Ingest complete. Collection '{COLLECTION}' → {count:,} points.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest JMdict chunks into Qdrant.")
    parser.add_argument("--all", action="store_true", help="ingest every entry, not just common/with-examples")
    parser.add_argument("--limit", type=int, default=None, help="cap the number of entries (testing)")
    args = parser.parse_args()
    run(args.all, args.limit)


if __name__ == "__main__":
    main()
