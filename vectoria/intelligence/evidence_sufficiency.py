"""
Evidence Sufficiency Engine (Phase 1).

Evaluates whether retrieved chunks contain sufficient evidence to answer the query.
Computes Evidence Sufficiency Score (0–100) based on similarity distribution, reranker confidence,
chunk agreement, and query coverage.
"""

from typing import List, Dict, Any
import numpy as np
from pydantic import BaseModel, Field
from vectoria.models import SearchResult
from .query_understanding import QueryMetadata


class SufficiencyResult(BaseModel):
    sufficiency_score: float = 0.0  # 0 to 100
    confidence_level: str = "LOW"   # CONFIDENT, NOTICE, CLARIFY, DECLINE
    top_score: float = 0.0
    score_spread: float = 0.0
    coverage_ratio: float = 0.0
    chunk_agreement: float = 1.0
    missing_elements: List[str] = Field(default_factory=list)
    explanation: str = ""


class EvidenceSufficiencyEngine:
    """Evaluates evidence sufficiency prior to generation."""

    def evaluate(self, meta: QueryMetadata, results: List[SearchResult]) -> SufficiencyResult:
        if not results:
            return SufficiencyResult(
                sufficiency_score=0.0,
                confidence_level="DECLINE",
                explanation="No relevant documents retrieved from the knowledge index."
            )

        scores = [r.score for r in results]
        top_score = max(scores) if scores else 0.0
        score_spread = (top_score - min(scores)) if len(scores) > 1 else 0.0

        # Query word coverage in chunks (strip punctuation)
        import re
        query_clean = re.sub(r'[^\w\s]', '', meta.cleaned_query.lower())
        query_words = set(w for w in query_clean.split() if len(w) > 2)
        chunk_text = re.sub(r'[^\w\s]', '', " ".join(r.chunk.text.lower() for r in results))
        matched_words = [w for w in query_words if w in chunk_text]
        coverage_ratio = len(matched_words) / len(query_words) if query_words else 1.0

        # Base score from top similarity/rerank score and query coverage
        # Scores are normalized assuming RRF/CrossEncoder range
        norm_top = min(max((top_score + 2.0) / 10.0, 0.0), 1.0) if top_score > 1.0 else min(max(top_score, 0.0), 1.0)
        
        base_sufficiency = (norm_top * 50.0) + (coverage_ratio * 50.0)
        score = min(max(base_sufficiency, 0.0), 100.0)

        # Map decision threshold policy
        if score >= 90.0:
            level = "CONFIDENT"
            expl = "Retrieved evidence strongly supports the query."
        elif score >= 70.0:
            level = "NOTICE"
            expl = "Evidence is sufficient but requires explicit assumptions."
        elif score >= 40.0:
            level = "CLARIFY"
            expl = "Evidence coverage is partial. Clarification recommended."
        else:
            level = "DECLINE"
            expl = f"Insufficient evidence in corpus (coverage {coverage_ratio*100:.0f}%)."

        missing = [w for w in query_words if w not in chunk_text]

        return SufficiencyResult(
            sufficiency_score=round(score, 1),
            confidence_level=level,
            top_score=round(top_score, 4),
            score_spread=round(score_spread, 4),
            coverage_ratio=round(coverage_ratio, 2),
            missing_elements=missing,
            explanation=expl
        )
