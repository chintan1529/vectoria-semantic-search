"""
Performance Telemetry Dashboard Endpoint (Phase 14 & Refinement 6).

Exposes /api/performance/telemetry for real-time monitoring of stage latencies,
TTFT, cache hit ratios, worker queue depth, system RAM RSS, CPU percent, and degradation level.
"""

from fastapi import APIRouter
from vectoria.performance.hardware_detector import hardware_monitor
from vectoria.performance.degradation import degradation_manager
from vectoria.performance.cache_tier import query_embedding_cache
from vectoria.performance.budget import budget_manager
from backend.core.async_queue import async_worker_queue

router = APIRouter()


@router.get("/performance/telemetry")
def get_performance_telemetry():
    """Returns real-time system performance telemetry and budget compliance."""
    stats = hardware_monitor.get_resource_stats()
    queue_depth = async_worker_queue.qsize
    deg_state = degradation_manager.evaluate_state(stats.cpu_percent, stats.memory_rss_mb, queue_depth)

    current_metrics = {
        "memory_rss_mb": stats.memory_rss_mb,
        "cpu_percent": stats.cpu_percent,
        "queue_depth": queue_depth,
        "cache_hit_ratio": round(query_embedding_cache.hit_ratio, 3),
        "degradation_level": deg_state.level.value,
        "degradation_reason": deg_state.reason,
    }

    budget_status = budget_manager.validate_metrics(current_metrics)

    return {
        "status": "healthy",
        "telemetry": current_metrics,
        "resource_stats": stats.model_dump(),
        "budget_compliance": budget_status,
        "active_budget": budget_manager.budget.model_dump(),
    }
