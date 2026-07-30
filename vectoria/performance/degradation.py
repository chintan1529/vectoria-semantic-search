"""
Adaptive Degradation Manager (Refinement 3).

Automatically sheds or scales down optional workloads (claim grounding, verification depth,
rerank pool size, cache size) under high CPU saturation or RAM RSS pressure.
"""

from enum import Enum
from pydantic import BaseModel


class DegradationLevel(str, Enum):
    NORMAL = "NORMAL"         # Full capabilities (grounding, full verification, max rerank)
    MODERATE = "MODERATE"     # Reduced rerank candidates (8), lightweight verification
    DEGRADED = "DEGRADED"     # Disable claim grounding, skip verification, min rerank pool (5)
    CRITICAL = "CRITICAL"     # Emergency mode: direct vector retrieval, load shed background tasks


class DegradationState(BaseModel):
    level: DegradationLevel = DegradationLevel.NORMAL
    enable_grounding: bool = True
    enable_verification: bool = True
    max_rerank_candidates: int = 15
    reason: str = "System resource pressure within normal operating limits."


class AdaptiveDegradationManager:
    """Monitors system pressure and adjusts execution degradation state."""

    def evaluate_state(self, cpu_percent: float, ram_rss_mb: float, queue_backlog: int) -> DegradationState:
        if cpu_percent > 90.0 or ram_rss_mb > 5500.0 or queue_backlog > 40:
            return DegradationState(
                level=DegradationLevel.CRITICAL,
                enable_grounding=False,
                enable_verification=False,
                max_rerank_candidates=5,
                reason="High CPU saturation / RAM pressure. Operating in CRITICAL degradation mode."
            )
        elif cpu_percent > 75.0 or ram_rss_mb > 4500.0 or queue_backlog > 20:
            return DegradationState(
                level=DegradationLevel.DEGRADED,
                enable_grounding=False,
                enable_verification=False,
                max_rerank_candidates=8,
                reason="Moderate system pressure. Grounding and verification disabled."
            )
        elif cpu_percent > 60.0:
            return DegradationState(
                level=DegradationLevel.MODERATE,
                enable_grounding=True,
                enable_verification=False,
                max_rerank_candidates=10,
                reason="Elevated CPU usage. Lightweight verification active."
            )
        else:
            return DegradationState(
                level=DegradationLevel.NORMAL,
                enable_grounding=True,
                enable_verification=True,
                max_rerank_candidates=15,
                reason="Normal operation."
            )


degradation_manager = AdaptiveDegradationManager()
