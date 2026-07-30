"""
Adaptive Query Budget Allocator (Refinement 4).

Allocates compute and retrieval resources dynamically based on query intent and complexity.
Prevents wasting CPU/latency resources on simple queries while giving complex queries larger context.
"""

from pydantic import BaseModel
from .query_understanding import QueryMetadata


class QueryBudget(BaseModel):
    top_k: int = 5
    rerank_candidate_k: int = 15
    max_context_tokens: int = 4000
    allow_secondary_retrieval: bool = False
    max_retries: int = 1


def allocate_query_budget(meta: QueryMetadata) -> QueryBudget:
    """Calculates query budget from metadata."""
    if meta.intent == "factual" and meta.complexity_score < 0.3:
        # Simple query: lightweight path
        return QueryBudget(
            top_k=3,
            rerank_candidate_k=8,
            max_context_tokens=2000,
            allow_secondary_retrieval=False,
            max_retries=1
        )
    elif meta.is_multi_hop or meta.intent == "multi_hop":
        # Complex multi-hop query
        return QueryBudget(
            top_k=8,
            rerank_candidate_k=25,
            max_context_tokens=6000,
            allow_secondary_retrieval=True,
            max_retries=2
        )
    elif meta.is_comparative or meta.intent == "comparative":
        # Comparison query
        return QueryBudget(
            top_k=6,
            rerank_candidate_k=20,
            max_context_tokens=5000,
            allow_secondary_retrieval=True,
            max_retries=1
        )
    else:
        # Standard analytical / factual query
        return QueryBudget(
            top_k=5,
            rerank_candidate_k=15,
            max_context_tokens=4000,
            allow_secondary_retrieval=False,
            max_retries=1
        )
