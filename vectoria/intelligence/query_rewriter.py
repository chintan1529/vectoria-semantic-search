"""
Query Rewriter Module (Phase 5).

Expands abbreviations, normalizes terms, and generates alternative search formulations to improve recall.
"""

import re
from typing import List
from .query_understanding import QueryMetadata


class QueryRewriter:
    """Normalizes and expands queries without changing intent."""

    ABBREVIATION_MAP = {
        "rag": "retrieval augmented generation",
        "faiss": "facebook AI similarity search",
        "mrr": "mean reciprocal rank",
        "ndcg": "normalized discounted cumulative gain",
        "llm": "large language model",
        "sse": "server sent events",
        "kg": "knowledge graph",
    }

    def rewrite(self, meta: QueryMetadata) -> List[str]:
        """Generates list of search query formulations."""
        primary = meta.cleaned_query
        formulations = [primary]

        # 1. Abbreviation Expansion
        words = primary.split()
        expanded_words = [self.ABBREVIATION_MAP.get(w.lower().strip("?,."), w) for w in words]
        expanded_str = " ".join(expanded_words)
        if expanded_str.lower() != primary.lower():
            formulations.append(expanded_str)

        # 2. Entity-focused formulation if multi-entity
        if len(meta.entities) >= 2:
            formulations.append(" ".join(meta.entities))

        return formulations
