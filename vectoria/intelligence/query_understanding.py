"""
Query Understanding Pipeline (Phase 3).

Analyzes queries prior to retrieval to extract rich metadata:
intent, domain, complexity, named entities, temporal/comparative/multi-hop flags, and output constraints.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class QueryMetadata(BaseModel):
    original_query: str
    cleaned_query: str
    intent: str = "factual"  # factual, analytical, comparative, multi_hop, conversational
    domain: str = "general"
    complexity_score: float = 0.5  # 0.0 (simple) to 1.0 (complex)
    entities: List[str] = Field(default_factory=list)
    has_temporal: bool = False
    is_comparative: bool = False
    is_multi_hop: bool = False
    requested_format: str = "prose"  # prose, list, table, code
    constraints: List[str] = Field(default_factory=list)


class QueryUnderstandingPipeline:
    """Fast, heuristic + pattern-based query understanding engine (< 5ms execution time)."""

    COMPARISON_WORDS = {"compare", "versus", "vs", "difference", "differ", "better", "faster", "advantage", "disadvantage"}
    MULTI_HOP_WORDS = {"why", "how does", "relationship", "impact", "cause", "effect", "consequence", "lead to"}
    TEMPORAL_PATTERNS = [r"\b(19\d{2}|20\d{2})\b", r"\b(today|yesterday|now|recent|history|future|decade|century|year|month)\b"]

    def analyze(self, query: str) -> QueryMetadata:
        cleaned = query.strip()
        lower = cleaned.lower()

        # 1. Detect Comparative Intent
        is_comp = any(w in lower for w in self.COMPARISON_WORDS)

        # 2. Detect Multi-Hop Requirements
        is_multi = any(w in lower for w in self.MULTI_HOP_WORDS) or " and " in lower

        # 3. Detect Temporal References
        has_temp = any(re.search(pat, lower) for pat in self.TEMPORAL_PATTERNS)

        # 4. Extract Named Entities (heuristic capital words & quotes)
        entities = list(set(re.findall(r'"([^"]+)"', cleaned) + re.findall(r'\b[A-Z][a-zA-B0-9-]+\b', cleaned)))

        # 5. Classify Intent & Complexity
        if is_comp:
            intent = "comparative"
            complexity = 0.75
        elif is_multi:
            intent = "multi_hop"
            complexity = 0.85
        elif len(cleaned.split()) > 12:
            intent = "analytical"
            complexity = 0.65
        elif cleaned.endswith("?") and len(cleaned.split()) <= 4:
            intent = "factual"
            complexity = 0.2
        else:
            intent = "factual"
            complexity = 0.4

        # 6. Requested Format
        req_format = "prose"
        if "list" in lower or "bullet" in lower:
            req_format = "list"
        elif "table" in lower:
            req_format = "table"
        elif "code" in lower or "python" in lower or "script" in lower:
            req_format = "code"

        return QueryMetadata(
            original_query=query,
            cleaned_query=cleaned,
            intent=intent,
            complexity_score=complexity,
            entities=entities[:5],
            has_temporal=has_temp,
            is_comparative=is_comp,
            is_multi_hop=is_multi,
            requested_format=req_format,
        )
