"""
Heuristic Context Validator — Score-based filtering without LLM calls.

Replaces the LLM-based ContextValidator with fast local heuristics:
  1. Score threshold filtering
  2. Text deduplication (hash-based)
  3. Source diversity enforcement
  4. Max chunk capping

Performance target: < 5ms execution time.
"""
from typing import List, Set
from vectoria.models import SearchResult
from backend.core.logging import logger


class HeuristicValidationResult:
    """Result of heuristic context validation."""
    def __init__(
        self,
        valid_results: List[SearchResult],
        rejected_count: int,
        confidence: str,
        rejection_reasons: dict,
        rejected_results: List[dict] = None,
    ):
        self.valid_results = valid_results
        self.rejected_count = rejected_count
        self.confidence = confidence  # HIGH, MEDIUM, LOW
        self.rejection_reasons = rejection_reasons
        self.rejected_results = rejected_results or []


class HeuristicContextValidator:
    """Fast context validation using score thresholds and deduplication.
    
    No LLM calls. All operations are O(n) where n = number of results.
    """

    def __init__(
        self,
        min_rerank_score: float = -2.0,
        dedup_similarity_chars: int = 200,
        max_chunks: int = 10,
        min_source_diversity: int = 1,
        high_confidence_threshold: float = 3.0,
        medium_confidence_threshold: float = 0.5,
    ):
        self.min_rerank_score = min_rerank_score
        self.dedup_similarity_chars = dedup_similarity_chars
        self.max_chunks = max_chunks
        self.min_source_diversity = min_source_diversity
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold

    def validate_context(
        self, query: str, results: List[SearchResult]
    ) -> HeuristicValidationResult:
        """Validate and filter retrieved context using heuristics.
        
        Steps:
          1. Score threshold filtering
          2. Text deduplication
          3. Max chunk enforcement
          4. Confidence assessment
          
        Target: < 5ms execution.
        """
        if not results:
            return HeuristicValidationResult([], 0, "LOW", {"empty": True})

        rejection_reasons = {
            "low_score": 0,
            "duplicate": 0,
            "capped": 0,
        }

        # --- Step 1: Score threshold filtering ---
        score_filtered = []
        rejected_items = []
        
        for r in results:
            if r.score >= self.min_rerank_score:
                score_filtered.append(r)
            else:
                rejection_reasons["low_score"] += 1
                rejected_items.append({
                    "chunk_id": r.chunk.chunk_id,
                    "title": r.chunk.metadata.title,
                    "score": r.score,
                    "reason": "low_score"
                })

        # --- Step 2: Text deduplication ---
        deduped: List[SearchResult] = []
        seen_hashes: Set[int] = set()

        for r in score_filtered:
            text_hash = hash(r.chunk.text[:self.dedup_similarity_chars])
            if text_hash not in seen_hashes:
                seen_hashes.add(text_hash)
                deduped.append(r)
            else:
                rejection_reasons["duplicate"] += 1
                rejected_items.append({
                    "chunk_id": r.chunk.chunk_id,
                    "title": r.chunk.metadata.title,
                    "score": r.score,
                    "reason": "duplicate"
                })

        # --- Step 3: Max chunk enforcement ---
        if len(deduped) > self.max_chunks:
            rejection_reasons["capped"] = len(deduped) - self.max_chunks
            for r in deduped[self.max_chunks:]:
                rejected_items.append({
                    "chunk_id": r.chunk.chunk_id,
                    "title": r.chunk.metadata.title,
                    "score": r.score,
                    "reason": "capped"
                })
            deduped = deduped[:self.max_chunks]

        # --- Step 4: Confidence assessment ---
        total_rejected = sum(rejection_reasons.values())

        if not deduped:
            confidence = "LOW"
        else:
            top_score = deduped[0].score
            # Check source diversity
            unique_sources = len(set(
                r.chunk.metadata.title for r in deduped if r.chunk.metadata
            ))

            if top_score >= self.high_confidence_threshold and unique_sources >= 2:
                confidence = "HIGH"
            elif top_score >= self.medium_confidence_threshold:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

        if total_rejected > 0:
            logger.debug(
                "Context validation | accepted=%d rejected=%d reasons=%s confidence=%s",
                len(deduped), total_rejected, rejection_reasons, confidence,
            )

        return HeuristicValidationResult(
            valid_results=deduped,
            rejected_count=total_rejected,
            confidence=confidence,
            rejection_reasons=rejection_reasons,
            rejected_results=rejected_items,
        )
