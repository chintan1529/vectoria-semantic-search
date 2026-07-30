"""
Claim-Level Grounding Engine (Phase 8 & Refinement 7).

Splits generated answers into claims/sentences and maps each claim to supporting chunk evidence.
Computes claim coverage percentage and flags unsupported or weakly supported claims.
"""

import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from vectoria.models import SearchResult


class ClaimGroundingResult(BaseModel):
    total_claims: int = 0
    grounded_claims: int = 0
    coverage_percentage: float = 100.0
    unsupported_claims: List[str] = Field(default_factory=list)
    claim_map: List[Dict[str, Any]] = Field(default_factory=list)


class ClaimGroundingEngine:
    """Evaluates claim-to-evidence coverage for generated answers."""

    def evaluate(self, answer_text: str, results: List[SearchResult]) -> ClaimGroundingResult:
        if not answer_text.strip():
            return ClaimGroundingResult()

        # Split into sentences / claims
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer_text) if len(s.strip()) > 10]
        if not sentences:
            return ClaimGroundingResult()

        chunk_texts = [r.chunk.text.lower() for r in results]
        grounded_count = 0
        unsupported = []
        claim_map = []

        for stmt in sentences:
            stmt_words = set(w.lower() for w in stmt.split() if len(w) > 3)
            best_overlap = 0.0
            best_chunk_id = None

            for r in results:
                c_words = set(w.lower() for w in r.chunk.text.split() if len(w) > 3)
                overlap = len(stmt_words.intersection(c_words)) / len(stmt_words) if stmt_words else 1.0
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_chunk_id = r.chunk.chunk_id

            is_grounded = best_overlap >= 0.3
            if is_grounded:
                grounded_count += 1
            else:
                unsupported.append(stmt)

            claim_map.append({
                "claim": stmt,
                "is_grounded": is_grounded,
                "overlap_score": round(best_overlap, 2),
                "supported_by": best_chunk_id
            })

        coverage = (grounded_count / len(sentences)) * 100.0 if sentences else 100.0

        return ClaimGroundingResult(
            total_claims=len(sentences),
            grounded_claims=grounded_count,
            coverage_percentage=round(coverage, 1),
            unsupported_claims=unsupported,
            claim_map=claim_map
        )
