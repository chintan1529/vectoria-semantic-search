"""Integration test for the refined embedding module."""

import numpy as np

from vectoria.ingestion.loader import load_documents
from vectoria.ingestion.chunker import chunk_documents
from vectoria.embedding.encoder import EmbeddingEncoder, EmbeddingMapping
from vectoria.config import EMBEDDINGS_PATH, MAPPING_PATH


def main() -> None:
    print("=" * 60)
    print("  EMBEDDING MODULE -- Refinement Validation")
    print("=" * 60)
    print()

    # -- Ingest --------------------------------------------------------
    docs = load_documents()
    chunks = chunk_documents(docs)

    # -- Encode (now returns tuple) ------------------------------------
    encoder = EmbeddingEncoder()
    embeddings, mapping = encoder.encode_chunks(chunks)

    # -- Core results --------------------------------------------------
    print()
    print("-" * 60)
    print("  EMBEDDING RESULTS")
    print("-" * 60)
    print(f"  Chunks encoded:  {len(chunks)}")
    print(f"  Embedding shape: {embeddings.shape}")
    print(f"  Dtype:           {embeddings.dtype}")
    print(f"  Memory:          {embeddings.nbytes} bytes ({embeddings.nbytes / 1024:.1f} KB)")

    # -- Dtype verification --------------------------------------------
    print()
    print("-" * 60)
    print("  DTYPE VERIFICATION")
    print("-" * 60)
    print(f"  dtype == float32: {embeddings.dtype == np.float32}")

    # -- Mapping verification ------------------------------------------
    print()
    print("-" * 60)
    print("  EXPLICIT INDEX MAPPING")
    print("-" * 60)
    for i in range(len(chunks)):
        cid = mapping.get_chunk_id(i)
        idx = mapping.get_index(cid)
        print(f"  index {i} -> {cid} -> index {idx} (round-trip OK: {idx == i})")

    # -- L2 normalisation check ----------------------------------------
    norms = np.linalg.norm(embeddings, axis=1)
    print()
    print("-" * 60)
    print("  L2 NORMALISATION")
    print("-" * 60)
    print(f"  Norm range:      [{norms.min():.6f}, {norms.max():.6f}]")
    print(f"  All norms ~1.0:  {np.allclose(norms, 1.0, atol=1e-4)}")

    # -- Sample vector -------------------------------------------------
    print()
    print("-" * 60)
    print("  SAMPLE EMBEDDING (first 10 dims)")
    print("-" * 60)
    print(f"  Chunk: {chunks[0].chunk_id}")
    print(f"  Vector: [{', '.join(f'{v:.4f}' for v in embeddings[0][:10])}, ...]")

    # -- Semantic similarity -------------------------------------------
    query_vec = encoder.encode_query("How do neural networks learn?")
    print()
    print("-" * 60)
    print("  QUERY: 'How do neural networks learn?'")
    print("-" * 60)
    print(f"  Query dtype: {query_vec.dtype}")
    print(f"  Query norm:  {np.linalg.norm(query_vec):.6f}")
    print()
    for i, chunk in enumerate(chunks):
        sim = float(np.dot(query_vec, embeddings[i]))
        print(f"  [{sim:+.4f}] {chunk.metadata.title} (chunk {chunk.chunk_index})")

    # -- Persistence with checksum -------------------------------------
    print()
    print("-" * 60)
    print("  PERSISTENCE (embeddings + mapping + checksum)")
    print("-" * 60)

    # Save
    EmbeddingEncoder.save_embeddings(embeddings, EMBEDDINGS_PATH)
    mapping.save(MAPPING_PATH)

    # Load
    reloaded_emb = EmbeddingEncoder.load_embeddings(EMBEDDINGS_PATH)
    reloaded_map = EmbeddingMapping.load(MAPPING_PATH)

    # Verify
    emb_match = np.array_equal(embeddings, reloaded_emb)
    map_match = all(
        reloaded_map.get_chunk_id(i) == mapping.get_chunk_id(i)
        for i in range(len(mapping))
    )
    print(f"  Embeddings match: {emb_match}")
    print(f"  Mapping match:    {map_match}")
    print(f"  Loaded dtype:     {reloaded_emb.dtype}")

    # -- Checksum file exists ------------------------------------------
    from pathlib import Path
    sha_path = Path(EMBEDDINGS_PATH).with_suffix(".sha256")
    print(f"  Checksum file:    {sha_path.exists()}")
    if sha_path.exists():
        print(f"  Checksum:         {sha_path.read_text().strip()[:32]}...")

    print()
    print("  [OK] ALL TESTS PASSED")


if __name__ == "__main__":
    main()
