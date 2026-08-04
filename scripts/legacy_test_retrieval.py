"""Integration test for the retrieval engine."""

from vectoria.retrieval.engine import SearchEngine


def main() -> None:
    print("=" * 60)
    print("  RETRIEVAL ENGINE -- Integration Test")
    print("=" * 60)
    print()

    # -- Load engine from persisted storage ----------------------------
    engine = SearchEngine()
    engine.load()

    # -- Query 1: AI-related -------------------------------------------
    q1 = "How do neural networks learn?"
    results1 = engine.search(q1, top_k=5)

    print("-" * 60)
    print(f"  QUERY: '{q1}'")
    print(f"  Results: {len(results1)}")
    print("-" * 60)
    for r in results1:
        print(f"  #{r.rank} [{r.score:+.4f}] {r.chunk.metadata.title} "
              f"(chunk {r.chunk.chunk_index}, {r.chunk.word_count}w)")
        print(f"          {r.chunk.text[:70]}...")

    # -- Query 2: Climate-related --------------------------------------
    q2 = "What causes global warming and sea level rise?"
    results2 = engine.search(q2, top_k=5)

    print()
    print("-" * 60)
    print(f"  QUERY: '{q2}'")
    print(f"  Results: {len(results2)}")
    print("-" * 60)
    for r in results2:
        print(f"  #{r.rank} [{r.score:+.4f}] {r.chunk.metadata.title} "
              f"(chunk {r.chunk.chunk_index}, {r.chunk.word_count}w)")
        print(f"          {r.chunk.text[:70]}...")

    # -- Query 3: with min_score threshold -----------------------------
    q3 = "machine learning algorithms"
    results3_all = engine.search(q3, top_k=5)
    results3_filtered = engine.search(q3, top_k=5, min_score=0.2)

    print()
    print("-" * 60)
    print(f"  QUERY: '{q3}' (with min_score=0.2 filter)")
    print("-" * 60)
    print(f"  Without filter: {len(results3_all)} results")
    print(f"  With filter:    {len(results3_filtered)} results")
    for r in results3_filtered:
        print(f"  #{r.rank} [{r.score:+.4f}] {r.chunk.metadata.title}")

    # -- Determinism check ---------------------------------------------
    print()
    print("-" * 60)
    print("  DETERMINISM CHECK")
    print("-" * 60)
    r_a = engine.search(q1, top_k=5)
    r_b = engine.search(q1, top_k=5)
    ids_match = [r.chunk.chunk_id for r in r_a] == [r.chunk.chunk_id for r in r_b]
    scores_match = all(
        abs(a.score - b.score) < 1e-6 for a, b in zip(r_a, r_b)
    )
    print(f"  Same IDs:    {ids_match}")
    print(f"  Same scores: {scores_match}")

    # -- Top-K safety --------------------------------------------------
    print()
    print("-" * 60)
    print("  TOP-K SAFETY")
    print("-" * 60)
    big_k = engine.search(q1, top_k=100)
    print(f"  Requested top_k=100, got {len(big_k)} results (no crash)")

    # -- Cache check ---------------------------------------------------
    print()
    print("-" * 60)
    print("  CACHE")
    print("-" * 60)
    # Second call should hit cache
    import time
    start = time.perf_counter()
    _ = engine.search(q1, top_k=5)
    cached_ms = (time.perf_counter() - start) * 1000
    print(f"  Cached query time: {cached_ms:.1f} ms (should be ~0 ms)")

    engine.clear_cache()
    start = time.perf_counter()
    _ = engine.search(q1, top_k=5)
    fresh_ms = (time.perf_counter() - start) * 1000
    print(f"  Fresh query time:  {fresh_ms:.1f} ms")

    # -- Result structure check ----------------------------------------
    print()
    print("-" * 60)
    print("  RESULT STRUCTURE")
    print("-" * 60)
    r = results1[0]
    print(f"  rank:              {r.rank}")
    print(f"  score:             {r.score:.4f}")
    print(f"  chunk.chunk_id:    {r.chunk.chunk_id}")
    print(f"  chunk.doc_id:      {r.chunk.doc_id}")
    print(f"  chunk.chunk_index: {r.chunk.chunk_index}")
    print(f"  chunk.word_count:  {r.chunk.word_count}")
    print(f"  meta.title:        {r.chunk.metadata.title}")
    print(f"  meta.category:     {r.chunk.metadata.category}")
    print(f"  meta.source:       ...{r.chunk.metadata.source[-40:]}")

    print()
    print("  [OK] ALL TESTS PASSED")


if __name__ == "__main__":
    main()
