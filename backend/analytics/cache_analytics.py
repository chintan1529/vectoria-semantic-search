"""
Adaptive Cache Analytics

Tracks cache performance metrics:
- Hit Rate
- Miss Rate
- Latency Saved
- Cost Saved
"""
import json
import time
from typing import Dict
from pathlib import Path
from dataclasses import dataclass, asdict
from backend.core.logging import logger

ANALYTICS_DIR = Path("logs/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class CacheStats:
    total_requests: int = 0
    total_hits: int = 0
    total_misses: int = 0
    latency_saved_ms: int = 0
    cost_saved_usd: float = 0.0

class CacheAnalyticsEngine:
    def __init__(self, db_path: Path = ANALYTICS_DIR / "cache_analytics.json"):
        self.db_path = db_path
        self.stats = CacheStats()
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.stats = CacheStats(**data)
            except Exception as e:
                logger.warning(f"Failed to load cache analytics: {e}")

    def _save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self.stats), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache analytics: {e}")

    def log_cache_event(self, is_hit: bool, latency_saved_ms: int = 0, cost_saved_usd: float = 0.0):
        self.stats.total_requests += 1
        if is_hit:
            self.stats.total_hits += 1
            self.stats.latency_saved_ms += latency_saved_ms
            self.stats.cost_saved_usd += cost_saved_usd
        else:
            self.stats.total_misses += 1
            
        if self.stats.total_requests % 10 == 0:
            self._save()

    def generate_report(self) -> Dict:
        """Generate a summary of cache performance."""
        hit_rate = 0.0
        miss_rate = 0.0
        if self.stats.total_requests > 0:
            hit_rate = self.stats.total_hits / self.stats.total_requests
            miss_rate = self.stats.total_misses / self.stats.total_requests
            
        return {
            "total_requests": self.stats.total_requests,
            "total_hits": self.stats.total_hits,
            "total_misses": self.stats.total_misses,
            "hit_rate_pct": round(hit_rate * 100, 2),
            "miss_rate_pct": round(miss_rate * 100, 2),
            "latency_saved_ms": self.stats.latency_saved_ms,
            "cost_saved_usd": round(self.stats.cost_saved_usd, 4)
        }

# Singleton
cache_analytics = CacheAnalyticsEngine()
