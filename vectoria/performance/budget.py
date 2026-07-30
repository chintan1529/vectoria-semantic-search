"""
Performance Budget Manager (Refinement 1).

Centralizes system latency, memory RSS, startup duration, and throughput budgets
instead of hardcoding fixed threshold values throughout the codebase.
"""

from typing import Dict, Any
from pydantic import BaseModel


class PerformanceBudget(BaseModel):
    max_startup_seconds: float = 5.0
    max_ttft_ms: int = 300
    max_retrieval_ms: int = 150
    max_rerank_ms: int = 200
    max_memory_rss_mb: float = 6144.0  # 6 GB cap for 8 GB laptop
    min_cache_hit_ratio: float = 0.30
    max_queue_backlog: int = 50


class PerformanceBudgetManager:
    """Central manager for hardware-aware performance budgets."""

    def __init__(self, profile: str = "dev"):
        self.profile = profile
        if profile == "dev":
            self.budget = PerformanceBudget(
                max_startup_seconds=3.0,
                max_ttft_ms=250,
                max_retrieval_ms=100,
                max_rerank_ms=150,
                max_memory_rss_mb=4096.0,
            )
        else:  # production
            self.budget = PerformanceBudget(
                max_startup_seconds=10.0,
                max_ttft_ms=500,
                max_retrieval_ms=300,
                max_rerank_ms=400,
                max_memory_rss_mb=12288.0,
            )

    def validate_metrics(self, current_metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Validates current empirical metrics against active budget."""
        return {
            "startup_ok": current_metrics.get("startup_s", 0) <= self.budget.max_startup_seconds,
            "ttft_ok": current_metrics.get("ttft_ms", 0) <= self.budget.max_ttft_ms,
            "retrieval_ok": current_metrics.get("retrieval_ms", 0) <= self.budget.max_retrieval_ms,
            "memory_ok": current_metrics.get("memory_rss_mb", 0) <= self.budget.max_memory_rss_mb,
        }


# Global singleton budget manager
budget_manager = PerformanceBudgetManager()
