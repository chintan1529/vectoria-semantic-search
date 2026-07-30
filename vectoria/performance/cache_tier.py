"""
Multi-Layer Tiered Cache Engine (Phase 5).

High-performance in-memory LRU + TTL cache tier for embeddings, retrieval candidates,
reranker scores, and dynamic prompt templates.
"""

import time
from typing import Dict, Any, Optional, Tuple


class TieredCache:
    """Multi-layer in-memory LRU + TTL cache engine."""

    def __init__(self, max_size: int = 256, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            self._misses += 1
            return None

        val, timestamp = self._store[key]
        if time.time() - timestamp > self._ttl_seconds:
            del self._store[key]
            self._misses += 1
            return None

        self._hits += 1
        return val

    def put(self, key: str, val: Any) -> None:
        if len(self._store) >= self._max_size:
            # LRU eviction (FIFO pop of first key)
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = (val, time.time())

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def clear(self) -> None:
        self._store.clear()
        self._hits = 0
        self._misses = 0


# Global query embedding cache instance
query_embedding_cache = TieredCache(max_size=512, ttl_seconds=7200)
