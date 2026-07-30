"""
Query Intelligence Engine

Lightweight tracker for query analytics. Tracks:
- Most frequent queries
- Most failed queries
- Slowest queries
- Highest cache hit queries
- Most ambiguous queries
"""
import json
import time
from typing import Dict, List
from pathlib import Path
from dataclasses import dataclass, asdict
from backend.core.logging import logger

ANALYTICS_DIR = Path("logs/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class QueryStats:
    query: str
    count: int = 0
    failure_count: int = 0
    cache_hit_count: int = 0
    total_latency_ms: int = 0
    max_latency_ms: int = 0
    total_ambiguity_score: float = 0.0  # (1.0 - intent_confidence)
    last_seen: float = 0.0

class QueryIntelligenceEngine:
    def __init__(self, db_path: Path = ANALYTICS_DIR / "query_intelligence.json"):
        self.db_path = db_path
        self.stats: Dict[str, QueryStats] = {}
        self._load()

    def _normalize(self, query: str) -> str:
        return query.strip().lower()

    def _load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.stats[k] = QueryStats(**v)
            except Exception as e:
                logger.warning(f"Failed to load query intelligence: {e}")

    def _save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({k: asdict(v) for k, v in self.stats.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save query intelligence: {e}")

    def log_query(
        self, query: str, latency_ms: int, is_failure: bool = False,
        is_cache_hit: bool = False, intent_confidence: float = 1.0
    ):
        norm = self._normalize(query)
        if norm not in self.stats:
            self.stats[norm] = QueryStats(query=query)
        
        qs = self.stats[norm]
        qs.count += 1
        qs.total_latency_ms += latency_ms
        qs.max_latency_ms = max(qs.max_latency_ms, latency_ms)
        qs.last_seen = time.time()
        
        if is_failure:
            qs.failure_count += 1
        if is_cache_hit:
            qs.cache_hit_count += 1
            
        ambiguity = 1.0 - intent_confidence
        qs.total_ambiguity_score += max(0.0, ambiguity)
        
        # Save occasionally or just save (lightweight enough for low-volume, 
        # but could batch if high-volume. We will save every 5 updates for safety)
        if qs.count % 5 == 0 or is_failure:
            self._save()

    def generate_report(self) -> Dict:
        """Generate analytics on query execution."""
        all_stats = list(self.stats.values())
        
        # Helper to sort
        def get_top(key_func, limit=10):
            return [asdict(qs) for qs in sorted(all_stats, key=key_func, reverse=True)[:limit]]

        return {
            "most_frequent": get_top(lambda qs: qs.count),
            "most_failed": get_top(lambda qs: qs.failure_count),
            "slowest": get_top(lambda qs: qs.max_latency_ms),
            "highest_cache_hit": get_top(lambda qs: qs.cache_hit_count),
            "most_ambiguous": get_top(lambda qs: qs.total_ambiguity_score / qs.count if qs.count else 0)
        }

# Singleton
query_intelligence = QueryIntelligenceEngine()
