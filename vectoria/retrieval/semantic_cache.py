"""
Semantic Cache — Vector-similarity response cache with strict validation.

Cache hit criteria (ALL must be satisfied):
  1. Cosine similarity >= 0.97 between query embeddings
  2. Intent classification must match exactly
  3. >= 60% overlap in retrieved chunk IDs
  4. Bias towards cache MISS on any ambiguity

This is deliberately conservative: a false cache hit is far more damaging
to trust than re-generating an answer.
"""
import time
import hashlib
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from vectoria.logger import get_logger

logger = get_logger(__name__)

# Strict similarity threshold — prefer miss over false hit
SIMILARITY_THRESHOLD = 0.97
# Minimum chunk ID overlap ratio
CHUNK_OVERLAP_THRESHOLD = 0.60
# Maximum number of cached entries
MAX_CACHE_ENTRIES = 128


@dataclass
class CachedResponse:
    """A cached query-response pair with validation metadata."""
    query: str
    query_embedding: np.ndarray
    intent_type: str
    chunk_ids: List[str]
    answer_text: str
    generation_meta: Dict
    trust_verification: Optional[Dict] = None
    context_data: Optional[List[Dict]] = None
    created_at: float = 0.0
    hit_count: int = 0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class CacheLookupResult:
    """Result of a cache lookup attempt."""
    hit: bool
    entry: Optional[CachedResponse] = None
    similarity: float = 0.0
    intent_match: bool = False
    chunk_overlap: float = 0.0
    rejection_reason: str = ""


class SemanticCache:
    """Vector-similarity response cache with triple validation.

    Every cache hit must pass ALL three gates:
      1. Embedding similarity >= 0.97
      2. Intent type exact match
      3. Chunk ID overlap >= 60%

    If any gate fails, the cache reports a MISS and the pipeline
    proceeds to full retrieval + generation.
    """

    def __init__(
        self,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
        chunk_overlap_threshold: float = CHUNK_OVERLAP_THRESHOLD,
        max_entries: int = MAX_CACHE_ENTRIES,
    ):
        self._entries: Dict[str, CachedResponse] = {}
        self._similarity_threshold = similarity_threshold
        self._chunk_overlap_threshold = chunk_overlap_threshold
        self._max_entries = max_entries

        # Telemetry
        self._total_lookups = 0
        self._total_hits = 0
        self._total_misses = 0
        self._rejections_by_reason: Dict[str, int] = {}

    @property
    def hit_rate(self) -> float:
        if self._total_lookups == 0:
            return 0.0
        return self._total_hits / self._total_lookups

    @property
    def stats(self) -> Dict:
        return {
            "total_lookups": self._total_lookups,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate": round(self.hit_rate, 4),
            "entries": len(self._entries),
            "max_entries": self._max_entries,
            "rejections": dict(self._rejections_by_reason),
        }

    def lookup(
        self,
        query_embedding: np.ndarray,
        intent_type: str,
        chunk_ids: List[str],
    ) -> CacheLookupResult:
        """Attempt to find a cached response for the given query.

        Args:
            query_embedding: L2-normalised embedding of the query.
            intent_type: The classified intent (e.g., 'factual', 'analytical').
            chunk_ids: The chunk IDs retrieved for this query.

        Returns:
            CacheLookupResult indicating hit/miss with diagnostic details.
        """
        self._total_lookups += 1

        if not self._entries:
            self._total_misses += 1
            return CacheLookupResult(hit=False, rejection_reason="empty_cache")

        # Gate 1: Find best embedding match
        best_sim = -1.0
        best_key: Optional[str] = None
        best_entry: Optional[CachedResponse] = None

        for key, entry in self._entries.items():
            sim = float(np.dot(query_embedding, entry.query_embedding))
            if sim > best_sim:
                best_sim = sim
                best_key = key
                best_entry = entry

        if best_sim < self._similarity_threshold:
            self._total_misses += 1
            reason = f"similarity_too_low ({best_sim:.4f} < {self._similarity_threshold})"
            self._rejections_by_reason[reason] = self._rejections_by_reason.get(reason, 0) + 1
            logger.debug(
                "CACHE_MISS | reason=similarity sim=%.4f threshold=%.4f",
                best_sim, self._similarity_threshold,
            )
            return CacheLookupResult(
                hit=False, similarity=best_sim, rejection_reason=reason
            )

        # Gate 2: Intent must match exactly
        if best_entry.intent_type != intent_type:
            self._total_misses += 1
            reason = f"intent_mismatch (cached={best_entry.intent_type}, query={intent_type})"
            self._rejections_by_reason[reason] = self._rejections_by_reason.get(reason, 0) + 1
            logger.debug(
                "CACHE_MISS | reason=intent_mismatch cached=%s query=%s sim=%.4f",
                best_entry.intent_type, intent_type, best_sim,
            )
            return CacheLookupResult(
                hit=False, similarity=best_sim, intent_match=False,
                rejection_reason=reason,
            )

        # Gate 3: Chunk ID overlap must be sufficient
        cached_chunks = set(best_entry.chunk_ids)
        query_chunks = set(chunk_ids)

        if not cached_chunks or not query_chunks:
            # If either set is empty, we can't verify overlap — miss
            self._total_misses += 1
            reason = "empty_chunk_set"
            self._rejections_by_reason[reason] = self._rejections_by_reason.get(reason, 0) + 1
            return CacheLookupResult(
                hit=False, similarity=best_sim, intent_match=True,
                chunk_overlap=0.0, rejection_reason=reason,
            )

        overlap = len(cached_chunks & query_chunks) / len(query_chunks)
        if overlap < self._chunk_overlap_threshold:
            self._total_misses += 1
            reason = f"chunk_overlap_low ({overlap:.2f} < {self._chunk_overlap_threshold})"
            self._rejections_by_reason[reason] = self._rejections_by_reason.get(reason, 0) + 1
            logger.debug(
                "CACHE_MISS | reason=chunk_overlap overlap=%.2f threshold=%.2f sim=%.4f",
                overlap, self._chunk_overlap_threshold, best_sim,
            )
            return CacheLookupResult(
                hit=False, similarity=best_sim, intent_match=True,
                chunk_overlap=overlap, rejection_reason=reason,
            )

        # --- All three gates passed: CACHE HIT ---
        self._total_hits += 1
        best_entry.hit_count += 1
        logger.info(
            "CACHE_HIT | sim=%.4f intent=%s overlap=%.2f hit_count=%d",
            best_sim, intent_type, overlap, best_entry.hit_count,
        )
        return CacheLookupResult(
            hit=True, entry=best_entry, similarity=best_sim,
            intent_match=True, chunk_overlap=overlap,
        )

    def store(
        self,
        query: str,
        query_embedding: np.ndarray,
        intent_type: str,
        chunk_ids: List[str],
        answer_text: str,
        generation_meta: Dict,
        trust_verification: Optional[Dict] = None,
        context_data: Optional[List[Dict]] = None,
    ) -> None:
        """Store a response in the semantic cache.

        Only stores if the answer_text is non-trivial (> 20 chars).
        """
        if len(answer_text.strip()) < 20:
            logger.debug("CACHE_SKIP_STORE | reason=answer_too_short len=%d", len(answer_text))
            return

        # Evict oldest if full
        if len(self._entries) >= self._max_entries:
            oldest_key = min(self._entries, key=lambda k: self._entries[k].created_at)
            del self._entries[oldest_key]
            logger.debug("CACHE_EVICTED | key=%s", oldest_key)

        key = hashlib.md5(f"{query.strip().lower()}:{intent_type}".encode()).hexdigest()
        self._entries[key] = CachedResponse(
            query=query,
            query_embedding=query_embedding,
            intent_type=intent_type,
            chunk_ids=chunk_ids,
            answer_text=answer_text,
            generation_meta=generation_meta,
            trust_verification=trust_verification,
            context_data=context_data,
        )
        logger.info("CACHE_STORED | key=%s query=%s intent=%s chunks=%d",
                     key, repr(query[:50]), intent_type, len(chunk_ids))

    def clear(self) -> None:
        """Flush the entire cache."""
        count = len(self._entries)
        self._entries.clear()
        logger.info("CACHE_CLEARED | evicted=%d", count)
