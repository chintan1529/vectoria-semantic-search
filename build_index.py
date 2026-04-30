#!/usr/bin/env python3
"""
Build Index -- End-to-end pipeline: documents -> chunks -> embeddings -> FAISS index.

Executes the full Vectoria ingestion-to-indexing pipeline on the Wikipedia
dataset and persists all artifacts to storage/.

Usage:
    python build_index.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from vectoria.config import (
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    MAPPING_PATH,
)
from vectoria.embedding.encoder import EmbeddingEncoder
from vectoria.indexing.faiss_index import VectorIndex
from vectoria.ingestion.chunker import chunk_documents
from vectoria.ingestion.loader import load_documents
from vectoria.logger import get_logger
from vectoria.retrieval.engine import SearchEngine
from vectoria.storage import save_chunks, validate_system_integrity

logger = get_logger("build_index")


def main() -> None:
    print("=" * 60)
    print("  VECTORIA -- Full Pipeline Build")
    print("=" * 60)
    print()

    pipeline_start = time.perf_counter()

    # ------------------------------------------------------------------
    # Stage 1: Load documents
    # ------------------------------------------------------------------
    print("[1/5] Loading documents...")
    stage_start = time.perf_counter()

    docs = load_documents()

    load_ms = int((time.perf_counter() - stage_start) * 1000)
    print(f"      Documents loaded: {len(docs)} ({load_ms} ms)")

    # ------------------------------------------------------------------
    # Stage 2: Chunk documents
    # ------------------------------------------------------------------
    print("[2/5] Chunking documents...")
    stage_start = time.perf_counter()

    chunks = chunk_documents(docs)

    chunk_ms = int((time.perf_counter() - stage_start) * 1000)
    avg_per_doc = len(chunks) / max(len(docs), 1)
    print(f"      Chunks created: {len(chunks)} "
          f"(avg {avg_per_doc:.1f}/doc, {chunk_ms} ms)")

    # ------------------------------------------------------------------
    # Stage 3: Generate embeddings
    # ------------------------------------------------------------------
    print("[3/5] Encoding embeddings (this may take a few minutes on CPU)...")
    stage_start = time.perf_counter()

    encoder = EmbeddingEncoder()
    embeddings, mapping = encoder.encode_chunks(chunks)

    embed_ms = int((time.perf_counter() - stage_start) * 1000)
    vps = len(chunks) / max((time.perf_counter() - stage_start), 1e-6)
    mem_mb = embeddings.nbytes / (1024 * 1024)
    print(f"      Embeddings: {embeddings.shape} float32 "
          f"({mem_mb:.1f} MB, {embed_ms} ms, {vps:.1f} vec/s)")

    # ------------------------------------------------------------------
    # Stage 4: Build FAISS index
    # ------------------------------------------------------------------
    print("[4/5] Building FAISS index...")
    stage_start = time.perf_counter()

    index = VectorIndex()
    index.build(embeddings, mapping)

    index_ms = int((time.perf_counter() - stage_start) * 1000)
    print(f"      Index: {len(index)} vectors ({index_ms} ms)")

    # ------------------------------------------------------------------
    # Stage 5: Persist all artifacts
    # ------------------------------------------------------------------
    print("[5/5] Saving artifacts...")
    stage_start = time.perf_counter()

    save_chunks(chunks, CHUNKS_PATH)
    EmbeddingEncoder.save_embeddings(embeddings, EMBEDDINGS_PATH)
    index.save(FAISS_INDEX_PATH, MAPPING_PATH)

    save_ms = int((time.perf_counter() - stage_start) * 1000)
    print(f"      Saved to storage/ ({save_ms} ms)")

    # ------------------------------------------------------------------
    # Pipeline summary
    # ------------------------------------------------------------------
    total_ms = int((time.perf_counter() - pipeline_start) * 1000)

    print()
    print("=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Documents:       {len(docs)}")
    print(f"  Chunks:          {len(chunks)}")
    print(f"  Embeddings:      {embeddings.shape}")
    print(f"  Index vectors:   {len(index)}")
    print(f"  Mapping entries: {len(mapping)}")
    print()
    print(f"  Load time:       {load_ms:,} ms")
    print(f"  Chunk time:      {chunk_ms:,} ms")
    print(f"  Embed time:      {embed_ms:,} ms")
    print(f"  Index time:      {index_ms:,} ms")
    print(f"  Save time:       {save_ms:,} ms")
    print(f"  TOTAL:           {total_ms:,} ms ({total_ms/1000:.1f}s)")
    print()
    print(f"  Throughput:      {vps:.1f} vectors/sec")
    print(f"  Memory:          {mem_mb:.1f} MB (embeddings)")

    # ------------------------------------------------------------------
    # System integrity check
    # ------------------------------------------------------------------
    print()
    print("-" * 60)
    print("  SYSTEM INTEGRITY CHECK")
    print("-" * 60)
    ok = validate_system_integrity()
    print(f"  Result: {'PASSED' if ok else 'FAILED'}")

    # ------------------------------------------------------------------
    # Sample retrieval queries
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  SAMPLE RETRIEVAL QUERIES")
    print("=" * 60)

    engine = SearchEngine()
    engine.load_from_objects(chunks, embeddings, mapping)

    queries = [
        "how do neural networks learn",
        "renewable energy benefits and solar power",
        "what causes climate change and global warming",
        "machine learning applications in healthcare",
        "deforestation and biodiversity loss",
    ]

    for query in queries:
        results = engine.search(query, top_k=3)
        print(f"\n  Q: \"{query}\"")
        print(f"  {'-' * 50}")
        for r in results:
            print(f"    #{r.rank} [{r.score:+.4f}] {r.chunk.metadata.title} "
                  f"(chunk {r.chunk.chunk_index})")

    print()
    print("=" * 60)
    if ok:
        print("  [OK] PIPELINE BUILD COMPLETE -- SYSTEM READY")
    else:
        print("  [WARN] BUILD COMPLETE BUT INTEGRITY CHECK FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
