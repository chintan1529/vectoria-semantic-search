"""
Unit tests for Vectoria Performance Engineering Subsystem.
"""

import time
import pytest
from vectoria.performance.budget import PerformanceBudgetManager, budget_manager
from vectoria.performance.degradation import AdaptiveDegradationManager, DegradationLevel
from vectoria.performance.hardware_detector import HardwareMonitor
from vectoria.performance.cache_tier import TieredCache
from vectoria.performance.profiler import PipelineProfiler, MicrosecondTimer, PipelineStageMetrics
from backend.core.async_queue import AsyncWorkerQueue
from scripts.performance_gate import run_performance_gate


def test_performance_budget_manager():
    mgr = PerformanceBudgetManager(profile="dev")
    metrics = {"startup_s": 2.0, "ttft_ms": 200, "retrieval_ms": 50, "memory_rss_mb": 2048.0}
    status = mgr.validate_metrics(metrics)
    assert status["startup_ok"] is True
    assert status["ttft_ok"] is True


def test_adaptive_degradation_manager():
    deg = AdaptiveDegradationManager()

    # Normal state
    st_norm = deg.evaluate_state(cpu_percent=30.0, ram_rss_mb=2048.0, queue_backlog=5)
    assert st_norm.level == DegradationLevel.NORMAL
    assert st_norm.enable_grounding is True

    # Critical state
    st_crit = deg.evaluate_state(cpu_percent=95.0, ram_rss_mb=6000.0, queue_backlog=45)
    assert st_crit.level == DegradationLevel.CRITICAL
    assert st_crit.enable_grounding is False


def test_hardware_monitor():
    monitor = HardwareMonitor()
    stats = monitor.get_resource_stats()
    assert stats.cpu_cores >= 1
    assert stats.memory_rss_mb > 0.0


def test_tiered_cache():
    cache = TieredCache(max_size=10, ttl_seconds=60)
    cache.put("k1", "v1")
    assert cache.get("k1") == "v1"
    assert cache.get("non_existent") is None
    assert cache.hit_ratio == 0.5


def test_microsecond_timer():
    with MicrosecondTimer() as t:
        time.sleep(0.01)
    assert t.elapsed_ms >= 8.0


@pytest.mark.anyio
async def test_async_worker_queue():
    queue = AsyncWorkerQueue(max_queue_size=10)
    queue.start()

    executed = []

    def sample_task(val):
        executed.append(val)

    assert queue.enqueue(sample_task, "test_val") is True
    import anyio
    await anyio.sleep(0.05)
    assert "test_val" in executed


def test_performance_gate():
    passing_metrics = {"startup_s": 2.0, "ttft_ms": 200, "memory_rss_mb": 3000.0}
    assert run_performance_gate(passing_metrics) is True

    failing_metrics = {"startup_s": 10.0, "ttft_ms": 600, "memory_rss_mb": 8000.0}
    assert run_performance_gate(failing_metrics) is False
