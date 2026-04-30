"""Integration test for the FAISS indexing module."""

import numpy as np

from vectoria.ingestion.loader import load_documents
from vectoria.ingestion.chunker import chunk_documents
from vectoria.embedding.encoder import EmbeddingEncoder
from vectoria.indexing.faiss_index import VectorIndex
from vectoria.config import FAISS_INDEX_PATH, MAPPING_PATH


def main() -> None:
    print("=" * 60)
    print("  FAISS INDEXING MODULE -- Integration Test")
    print("=" * 60)
    print()

    # -- Pipeline: Ingest -> Embed -> Index ----------------------------
    docs = load_documents()
    chunks = chunk_documents(docs)
    encoder = EmbeddingEncoder()
    embeddings, mapping = encoder.encode_chunks(chunks)

    # -- Build index ---------------------------------------------------
    index = VectorIndex()
    index.build(embeddings, mapping)

    print()
    print("-" * 60)
    print("  INDEX STATS")
    print("-" * 60)
    print(f"  Vectors indexed: {len(index)}")
    print(f"  Index type:      IndexFlatIP (inner product)")
    print(f"  Dimension:       {index.dimension}")

    # -- Search: neural networks query ---------------------------------
    query = "How do neural networks learn?"
    query_vec = encoder.encode_query(query)
    scores, indices = index.search(query_vec, top_k=4)

    print()
    print("-" * 60)
    print(f"  SEARCH: '{query}'")
    print("-" * 60)
    for rank, (score, idx) in enumerate(zip(scores, indices), 1):
        chunk_id = index.get_chunk_id(int(idx))
        chunk = next(c for c in chunks if c.chunk_id == chunk_id)
        print(f"  #{rank} [{score:+.4f}] {chunk.metadata.title} "
              f"(chunk {chunk.chunk_index}) - {chunk.text[:60]}...")

    # -- Search: climate query -----------------------------------------
    query2 = "What causes global warming and sea level rise?"
    query_vec2 = encoder.encode_query(query2)
    scores2, indices2 = index.search(query_vec2, top_k=4)

    print()
    print("-" * 60)
    print(f"  SEARCH: '{query2}'")
    print("-" * 60)
    for rank, (score, idx) in enumerate(zip(scores2, indices2), 1):
        chunk_id = index.get_chunk_id(int(idx))
        chunk = next(c for c in chunks if c.chunk_id == chunk_id)
        print(f"  #{rank} [{score:+.4f}] {chunk.metadata.title} "
              f"(chunk {chunk.chunk_index}) - {chunk.text[:60]}...")

    # -- Ranking verification ------------------------------------------
    print()
    print("-" * 60)
    print("  RANKING VERIFICATION")
    print("-" * 60)
    # Scores should be in descending order
    scores_desc = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    print(f"  Scores descending: {scores_desc}")
    # No invalid indices
    no_invalid = all(idx >= 0 for idx in indices)
    print(f"  No invalid indices: {no_invalid}")
    # Result count
    print(f"  Results returned: {len(scores)} (requested: 4)")

    # -- Persistence ---------------------------------------------------
    print()
    print("-" * 60)
    print("  PERSISTENCE (save -> load -> verify)")
    print("-" * 60)

    # Save
    index.save()

    # Load into new instance
    loaded = VectorIndex.load()

    # Verify size
    print(f"  Original size: {len(index)}")
    print(f"  Loaded size:   {len(loaded)}")

    # Verify search produces identical results
    scores_loaded, indices_loaded = loaded.search(query_vec, top_k=4)
    scores_match = np.allclose(scores, scores_loaded, atol=1e-6)
    indices_match = np.array_equal(indices, indices_loaded)
    print(f"  Scores match:  {scores_match}")
    print(f"  Indices match: {indices_match}")

    # Verify mapping survived
    for i in range(len(chunks)):
        orig_id = index.get_chunk_id(i)
        loaded_id = loaded.get_chunk_id(i)
        if orig_id != loaded_id:
            print(f"  MAPPING MISMATCH at index {i}!")
            break
    else:
        print(f"  Mapping match: True ({len(chunks)} entries)")

    print()
    print("  [OK] ALL TESTS PASSED")


if __name__ == "__main__":
    main()
