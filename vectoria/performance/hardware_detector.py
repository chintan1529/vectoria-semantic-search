"""
Hardware Detector & Resource Pressure Monitor (Refinement 6 & Phase 13).

Detects CPU cores, available memory RSS, thread contention, and configures PyTorch thread limits.
"""

import os
import psutil
from typing import Dict, Any
from pydantic import BaseModel


class SystemResourceStats(BaseModel):
    cpu_cores: int
    cpu_percent: float
    memory_rss_mb: float
    memory_percent: float
    thread_count: int


class HardwareMonitor:
    """Monitors system hardware pressure and tunes thread settings."""

    def __init__(self):
        self._process = psutil.Process(os.getpid())
        self.configure_pytorch_threads()

    def configure_pytorch_threads(self) -> int:
        """Configures PyTorch CPU threads based on hardware core count."""
        cores = os.cpu_count() or 4
        # On 4-core machine (Ryzen 3), cap PyTorch to 2 threads to avoid Uvicorn contention
        recommended_threads = max(1, cores // 2)
        try:
            import torch
            torch.set_num_threads(recommended_threads)
        except ImportError:
            pass
        return recommended_threads

    def get_resource_stats(self) -> SystemResourceStats:
        mem_info = self._process.memory_info()
        return SystemResourceStats(
            cpu_cores=os.cpu_count() or 4,
            cpu_percent=psutil.cpu_percent(interval=None),
            memory_rss_mb=round(mem_info.rss / 1024 / 1024, 2),
            memory_percent=psutil.virtual_memory().percent,
            thread_count=self._process.num_threads(),
        )


hardware_monitor = HardwareMonitor()
