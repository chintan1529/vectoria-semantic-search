"""
Cost & Efficiency Tracker Module (Refinement 4).

Calculates per-query prompt/completion token usage, embedding compute cost,
reranking overhead, total financial cost ($), and cost-vs-quality metrics.
"""

from pydantic import BaseModel, Field


class QueryCostMetrics(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    embedding_cost_usd: float = 0.0
    generation_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    latency_ms: int = 0
    memory_rss_mb: float = 0.0


class CostTracker:
    """Calculates query execution cost based on standard model pricing."""

    # Pricing per 1,000 tokens (Gemini / standard model tier)
    PROMPT_PRICE_PER_1K = 0.00015
    COMPLETION_PRICE_PER_1K = 0.00060

    def compute_cost(self, prompt_tokens: int, completion_tokens: int, latency_ms: int = 0) -> QueryCostMetrics:
        gen_cost = ((prompt_tokens / 1000.0) * self.PROMPT_PRICE_PER_1K) + \
                   ((completion_tokens / 1000.0) * self.COMPLETION_PRICE_PER_1K)

        # Local embeddings & rerankers run on CPU (infra cost estimation)
        embed_cost = 0.000002

        total_cost = round(gen_cost + embed_cost, 6)

        return QueryCostMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            embedding_cost_usd=embed_cost,
            generation_cost_usd=round(gen_cost, 6),
            total_cost_usd=total_cost,
            latency_ms=latency_ms,
        )
