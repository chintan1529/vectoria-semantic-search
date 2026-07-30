"""
Provider Performance Analytics

Tracks upstream LLM provider metrics:
- Provider latency (TTFT, Total)
- Provider failures
- Provider switches (Failovers)
- Failover reasons
"""
import json
import time
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from backend.core.logging import logger

ANALYTICS_DIR = Path("logs/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class ProviderStats:
    total_requests: int = 0
    total_latency_ms: int = 0
    total_failures: int = 0
    total_switches: int = 0
    failover_reasons: Dict[str, int] = field(default_factory=dict)
    last_seen: float = 0.0

class ProviderAnalyticsEngine:
    def __init__(self, db_path: Path = ANALYTICS_DIR / "provider_analytics.json"):
        self.db_path = db_path
        self.providers: Dict[str, ProviderStats] = {}
        self._load()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.providers[k] = ProviderStats(**v)
            except Exception as e:
                logger.warning(f"Failed to load provider analytics: {e}")

    def _save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({k: asdict(v) for k, v in self.providers.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save provider analytics: {e}")

    def log_request(self, provider_name: str, latency_ms: int):
        if provider_name not in self.providers:
            self.providers[provider_name] = ProviderStats()
            
        ps = self.providers[provider_name]
        ps.total_requests += 1
        ps.total_latency_ms += latency_ms
        ps.last_seen = time.time()
        
        if ps.total_requests % 10 == 0:
            self._save()

    def log_failure(self, provider_name: str):
        if provider_name not in self.providers:
            self.providers[provider_name] = ProviderStats()
            
        ps = self.providers[provider_name]
        ps.total_failures += 1
        self._save()
        
    def log_switch(self, from_provider: str, to_provider: str, reason: str):
        if from_provider not in self.providers:
            self.providers[from_provider] = ProviderStats()
            
        ps = self.providers[from_provider]
        ps.total_switches += 1
        ps.failover_reasons[reason] = ps.failover_reasons.get(reason, 0) + 1
        self._save()

    def generate_report(self) -> Dict:
        """Generate a summary of provider performance."""
        report = {}
        for name, ps in self.providers.items():
            avg_latency = ps.total_latency_ms / ps.total_requests if ps.total_requests > 0 else 0
            report[name] = {
                "total_requests": ps.total_requests,
                "total_failures": ps.total_failures,
                "total_switches": ps.total_switches,
                "avg_latency_ms": round(avg_latency, 2),
                "failover_reasons": ps.failover_reasons
            }
        return report

# Singleton
provider_analytics = ProviderAnalyticsEngine()
