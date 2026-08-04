"""Integration test: full pipeline + system integrity validation."""

import numpy as np

from vectoria.ingestion.loader import load_documents
from vectoria.ingestion.chunker import chunk_documents
from vectoria.embedding.encoder import EmbeddingEncoder
from vectoria.indexing.faiss_index import VectorIndex
from vectoria.storage import (
    save_chunks,
    load_chunks,
    analyze_score_distribution,
    validate_system_integrity,
)
from vectoria.config import EMBEDDINGS_PATH, CHUNKS_PATH


def main() -> None:
    print("=" * 60)
    print("  SYSTEM INTEGRITY -- Pre-Retrieval Validation")
    print("=" * 60)
    print()

    # -- Full pipeline: Ingest -> Chunk -> Embed -> Index --------------
    docs = load_documents()
    chunks = chunk_documents(docs)

    encoder = EmbeddingEncoder()
    embeddings, mapping = encoder.encode_chunks(chunks)

    index = VectorIndex()
    index.build(embeddings, mapping)

    # -- 1. Chunk persistence ------------------------------------------
    print()
    print("-" * 60)
    print("  1. CHUNK PERSISTENCE (JSONL)")
    print("-" * 60)
    save_chunks(chunks)
    reloaded = load_chunks()

    ids_match = [c.chunk_id for c in chunks] == [c.chunk_id for c in reloaded]
    text_match = all(a.text == b.text for a, b in zip(chunks, reloaded))
    meta_match = all(
        a.metadata.category == b.metadata.category
        and a.metadata.title == b.metadata.title
        and a.metadata.source == b.metadata.source
        for a, b in zip(chunks, reloaded)
    )
    print(f"  Saved:          {len(chunks)} chunks")
    print(f"  Loaded:         {len(reloaded)} chunks")
    print(f"  IDs match:      {ids_match}")
    print(f"  Text match:     {text_match}")
    print(f"  Metadata match: {meta_match}")

    # Show JSONL sample
    import json
    from pathlib import Path
    first_line = Path(CHUNKS_PATH).read_text("utf-8").split("\n")[0]
    d = json.loads(first_line)
    print(f"  JSONL fields:   {list(d.keys())}")
    print(f"  Meta fields:    {list(d['metadata'].keys())}")

    # -- 2. Mapping consistency ----------------------------------------
    print()
    print("-" * 60)
    print("  2. MAPPING CONSISTENCY")
    print("-" * 60)
    chunk_id_set = {c.chunk_id for c in chunks}
    all_mapped = all(
        mapping.get_chunk_id(i) in chunk_id_set
        for i in range(len(mapping))
    )
    no_dupes = len(chunk_id_set) == len(chunks)
    count_match = len(chunks) == len(mapping) == embeddings.shape[0] == len(index)
    print(f"  len(chunks)={len(chunks)} len(mapping)={len(mapping)} "
          f"len(embeddings)={embeddings.shape[0]} len(index)={len(index)}")
    print(f"  Counts aligned: {count_match}")
    print(f"  All mapped IDs in chunks: {all_mapped}")
    print(f"  No duplicate chunk_ids: {no_dupes}")

    # -- 3. Memory safety ----------------------------------------------
    print()
    print("-" * 60)
    print("  3. MEMORY SAFETY")
    print("-" * 60)
    contiguous = embeddings.flags["C_CONTIGUOUS"]
    dtype_ok = embeddings.dtype == np.float32
    no_nan = not np.any(np.isnan(embeddings))
    no_inf = not np.any(np.isinf(embeddings))
    print(f"  C-contiguous: {contiguous}")
    print(f"  dtype float32: {dtype_ok}")
    print(f"  No NaN: {no_nan}")
    print(f"  No Inf: {no_inf}")

    # -- 4. Score distribution -----------------------------------------
    print()
    print("-" * 60)
    print("  4. SCORE DISTRIBUTION ANALYSIS")
    print("-" * 60)
    query_vec = encoder.encode_query("How do neural networks learn?")
    scores, indices = index.search(query_vec, top_k=4)
    stats = analyze_score_distribution(scores, label="nn_query")
    print(f"  Min:    {stats['min']:.4f}")
    print(f"  Max:    {stats['max']:.4f}")
    print(f"  Mean:   {stats['mean']:.4f}")
    print(f"  Std:    {stats['std']:.4f}")
    print(f"  Median: {stats['median']:.4f}")

    # -- 5. Persist everything -----------------------------------------
    print()
    print("-" * 60)
    print("  5. FULL PERSISTENCE")
    print("-" * 60)
    EmbeddingEncoder.save_embeddings(embeddings, EMBEDDINGS_PATH)
    index.save()
    # chunks already saved above
    print("  All artifacts persisted to storage/")

    # -- 6. System integrity check -------------------------------------
    print()
    print("-" * 60)
    print("  6. SYSTEM INTEGRITY VALIDATION")
    print("-" * 60)
    ok = validate_system_integrity()
    print(f"  Result: {'PASSED' if ok else 'FAILED'}")

    print()
    if ok:
        print("  [OK] SYSTEM IS RETRIEVAL-READY")
    else:
        print("  [FAIL] FIX ISSUES BEFORE PROCEEDING")


if __name__ == "__main__":
    main()
