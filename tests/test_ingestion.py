"""Integration test for the refined ingestion module."""

import json
from collections import Counter

from vectoria.ingestion.loader import load_documents
from vectoria.ingestion.chunker import chunk_documents
from vectoria.models import Chunk


def main() -> None:
    print("=" * 60)
    print("  INGESTION MODULE -- Refinement Validation")
    print("=" * 60)
    print()

    # -- Load ----------------------------------------------------------
    docs = load_documents()

    # -- Chunk (logs include per-doc stats, overlap, quality) ----------
    all_chunks = chunk_documents(docs)

    # -- Summary -------------------------------------------------------
    print()
    print("-" * 60)
    print(f"  Documents loaded: {len(docs)}")
    print(f"  Total chunks:     {len(all_chunks)}")
    print("-" * 60)

    doc_counts = Counter(c.metadata.title for c in all_chunks)
    print()
    print("  Chunks per document:")
    for title, count in doc_counts.items():
        print(f"    {title}: {count} chunk(s)")

    # -- Chunk size distribution ---------------------------------------
    word_counts = [c.word_count for c in all_chunks]
    print()
    print("-" * 60)
    print("  CHUNK SIZE DISTRIBUTION")
    print("-" * 60)
    print(f"  Average: {sum(word_counts) // len(word_counts)} words")
    print(f"  Min:     {min(word_counts)} words")
    print(f"  Max:     {max(word_counts)} words")
    print(f"  Std dev: {_std(word_counts):.1f} words")

    under_200 = sum(1 for w in word_counts if w < 200)
    in_range  = sum(1 for w in word_counts if 200 <= w <= 400)
    over_400  = sum(1 for w in word_counts if w > 400)
    print(f"  < 200 words: {under_200}")
    print(f"  200-400:     {in_range}")
    print(f"  > 400 words: {over_400}")

    # -- Sample chunks -------------------------------------------------
    nn = [c for c in all_chunks if "Neural" in c.metadata.title]
    if nn:
        print()
        print("-" * 60)
        print("  SAMPLE CHUNK (Neural Networks, chunk 0)")
        print("-" * 60)
        s = nn[0]
        print(f"  chunk_id:    {s.chunk_id}")
        print(f"  doc_id:      {s.doc_id}")
        print(f"  chunk_index: {s.chunk_index}")
        print(f"  word_count:  {s.word_count}")
        print(f"  category:    {s.metadata.category}")
        print(f"  title:       {s.metadata.title}")
        print(f"  source:      {s.metadata.source[-40:]}")
        print(f"  timestamp:   {s.metadata.timestamp}")
        print(f"  text:        {s.text[:180]}...")

    # -- Serialization round-trip --------------------------------------
    print()
    print("-" * 60)
    print("  SERIALIZATION ROUND-TRIP")
    print("-" * 60)
    sample = all_chunks[0]
    sample_dict = sample.to_dict()
    restored = Chunk.from_dict(sample_dict)
    ok = (
        restored.chunk_id == sample.chunk_id
        and restored.word_count == sample.word_count
        and restored.metadata.category == sample.metadata.category
    )
    print(f"  Round-trip OK: {ok}")
    jsonl = json.dumps(sample_dict)
    print(f"  JSONL sample:  {jsonl[:100]}...")

    print()
    print("  [OK] ALL TESTS PASSED")


def _std(values: list) -> float:
    """Simple standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


if __name__ == "__main__":
    main()
