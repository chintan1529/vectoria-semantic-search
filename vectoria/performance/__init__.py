"""
Vectoria Performance & Optimization Subsystem.

Provides centralized budgets, profiling, adaptive degradation, hardware monitoring,
multi-layer caching, and priority worker queues.
"""

from .budget import PerformanceBudgetManager, PerformanceBudget
from .degradation import AdaptiveDegradationManager, DegradationState
from .hardware_detector import HardwareMonitor, SystemResourceStats
from .cache_tier import TieredCache
from .profiler import PipelineProfiler, MicrosecondTimer

__all__ = [
    "PerformanceBudgetManager",
    "PerformanceBudget",
    "AdaptiveDegradationManager",
    "DegradationState",
    "HardwareMonitor",
    "SystemResourceStats",
    "TieredCache",
    "PipelineProfiler",
    "MicrosecondTimer",
]
