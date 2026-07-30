"""
Microsecond Pipeline Profiler (Phase 1).

Measures stage execution time, TTFT, CPU utilization, and memory RSS per query request.
"""

import time
from typing import Dict, Any
from pydantic import BaseModel, Field
from .hardware_detector import hardware_monitor


class PipelineStageMetrics(BaseModel):
    query_id: str
    understanding_ms: float = 0.0
    budget_ms: float = 0.0
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    decision_ms: float = 0.0
    prompt_ms: float = 0.0
    ttft_ms: float = 0.0
    total_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_rss_mb: float = 0.0


class MicrosecondTimer:
    """Context manager for microsecond timing of code blocks."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.perf_counter() - self.start) * 1000.0


class PipelineProfiler:
    """Tracks per-request microsecond stage latencies."""

    def record_stage(self, metrics: PipelineStageMetrics) -> None:
        stats = hardware_monitor.get_resource_stats()
        metrics.cpu_percent = stats.cpu_percent
        metrics.memory_rss_mb = stats.memory_rss_mb


global_profiler = PipelineProfiler()
