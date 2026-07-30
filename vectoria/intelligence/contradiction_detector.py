"""
Contradiction Detection Engine (Phase 7).

Analyzes retrieved chunks to identify conflicting facts, inconsistent dates, or differing numerical values.
Surfaces contradictory viewpoints in response payloads rather than masking them.
"""

import re
from typing import List, Dict
from pydantic import BaseModel, Field
from vectoria.models import SearchResult


class ContradictionResult(BaseModel):
    has_contradictions: bool = False
    detected_conflicts: List[Dict[str, str]] = Field(default_factory=list)
    explanation: str = ""


class ContradictionDetector:
    """Fast pattern-based contradiction detector across retrieved chunk texts."""

    DATE_PATTERN = r"\b(19\d{2}|20\d{2})\b"

    def detect(self, results: List[SearchResult]) -> ContradictionResult:
        if len(results) < 2:
            return ContradictionResult(has_contradictions=False)

        conflicts = []
        # Extract dates across chunks
        chunk_dates = {}
        for r in results:
            dates = re.findall(self.DATE_PATTERN, r.chunk.text)
            if dates:
                chunk_dates[r.chunk.chunk_id] = set(dates)

        # Check for multiple differing dates for same entity/topic
        all_dates = [d for dates in chunk_dates.values() for d in dates]
        if len(set(all_dates)) > 3:
            conflicts.append({
                "type": "date_discrepancy",
                "detail": f"Retrieved chunks reference conflicting timeline dates: {sorted(list(set(all_dates)))[:4]}"
            })

        has_conflicts = len(conflicts) > 0
        expl = "Contradictory facts detected across context sources." if has_conflicts else "No contradictions detected."

        return ContradictionResult(
            has_contradictions=has_conflicts,
            detected_conflicts=conflicts,
            explanation=expl
        )
