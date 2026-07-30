"""
Tests for the Semantic Cache — validates triple-gate validation logic.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest
from vectoria.retrieval.semantic_cache import SemanticCache


def _random_embedding(seed: int = 0) -> np.ndarray:
    """Generate a random L2-normalised 384-d vector."""
    rng = np.random.RandomState(seed)
    vec = rng.randn(384).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


def _near_embedding(base: np.ndarray, noise: float = 0.01) -> np.ndarray:
    """Generate an embedding very close to base (high similarity)."""
    perturbed = base + np.random.randn(384).astype(np.float32) * noise
    perturbed /= np.linalg.norm(perturbed)
    return perturbed


class TestSemanticCacheGates:
    """Test the three validation gates independently."""

    def test_empty_cache_miss(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        result = cache.lookup(emb, "factual", ["chunk_1"])
        assert not result.hit
        assert result.rejection_reason == "empty_cache"

    def test_gate1_similarity_too_low(self):
        cache = SemanticCache()
        emb1 = _random_embedding(0)
        emb2 = _random_embedding(42)  # Very different

        cache.store("query1", emb1, "factual", ["c1", "c2"], "This is a sufficiently long answer for caching.", {"tokens": 10})

        result = cache.lookup(emb2, "factual", ["c1", "c2"])
        assert not result.hit
        assert "similarity_too_low" in result.rejection_reason

    def test_gate2_intent_mismatch(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        near = _near_embedding(emb, noise=0.001)

        cache.store("query1", emb, "factual", ["c1", "c2"], "This is a sufficiently long answer for caching.", {"tokens": 10})

        # Same embedding, different intent
        result = cache.lookup(near, "analytical", ["c1", "c2"])
        assert not result.hit
        assert "intent_mismatch" in result.rejection_reason

    def test_gate3_chunk_overlap_too_low(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        near = _near_embedding(emb, noise=0.001)

        cache.store("query1", emb, "factual", ["c1", "c2", "c3"], "This is a sufficiently long answer for caching.", {"tokens": 10})

        # Same embedding, same intent, completely different chunks
        result = cache.lookup(near, "factual", ["c99", "c98", "c97"])
        assert not result.hit
        assert "chunk_overlap_low" in result.rejection_reason

    def test_all_gates_pass(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        near = _near_embedding(emb, noise=0.001)

        cache.store("query1", emb, "factual", ["c1", "c2", "c3"],
                     "This is a detailed answer.", {"tokens": 50})

        # Identical intent, very similar embedding, overlapping chunks
        result = cache.lookup(near, "factual", ["c1", "c2", "c4"])
        assert result.hit
        assert result.entry.answer_text == "This is a detailed answer."
        assert result.similarity > 0.97
        assert result.intent_match
        assert result.chunk_overlap >= 0.60

    def test_empty_chunk_set_misses(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        near = _near_embedding(emb, noise=0.001)

        cache.store("q", emb, "factual", ["c1"], "A valid answer text.", {"tokens": 10})

        result = cache.lookup(near, "factual", [])
        assert not result.hit
        assert result.rejection_reason == "empty_chunk_set"

    def test_short_answer_not_stored(self):
        cache = SemanticCache()
        emb = _random_embedding(0)

        # Answer too short — should NOT be stored
        cache.store("q", emb, "factual", ["c1"], "short", {"tokens": 1})
        assert len(cache._entries) == 0

    def test_cache_eviction(self):
        cache = SemanticCache(max_entries=2)
        e1 = _random_embedding(1)
        e2 = _random_embedding(2)
        e3 = _random_embedding(3)

        cache.store("q1", e1, "factual", ["c1"], "Answer one is long enough.", {"t": 1})
        cache.store("q2", e2, "factual", ["c2"], "Answer two is also long enough.", {"t": 2})
        assert len(cache._entries) == 2

        cache.store("q3", e3, "factual", ["c3"], "Answer three forces eviction.", {"t": 3})
        assert len(cache._entries) == 2  # Oldest evicted

    def test_hit_count_increments(self):
        cache = SemanticCache()
        emb = _random_embedding(0)
        near = _near_embedding(emb, noise=0.001)

        cache.store("q", emb, "factual", ["c1", "c2"], "A complete answer for the test.", {"t": 1})

        r1 = cache.lookup(near, "factual", ["c1", "c2"])
        assert r1.hit
        assert r1.entry.hit_count == 1

        r2 = cache.lookup(near, "factual", ["c1", "c2"])
        assert r2.hit
        assert r2.entry.hit_count == 2

    def test_stats_tracking(self):
        cache = SemanticCache()
        emb = _random_embedding(0)

        cache.store("q", emb, "factual", ["c1"], "Stored answer for stats test.", {"t": 1})

        # Miss
        cache.lookup(_random_embedding(42), "factual", ["c1"])
        stats = cache.stats
        assert stats["total_lookups"] == 1
        assert stats["total_misses"] == 1
        assert stats["total_hits"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
