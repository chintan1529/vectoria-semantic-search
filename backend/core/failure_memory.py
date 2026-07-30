"""
Failure Memory — Persistent logging of retrieval failures, hallucinations,
low-faithfulness answers, and empty retrieval events.

Generates recurring failure reports from the accumulated data.
"""
import json
import time
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from backend.core.logging import logger

# Persistent storage location
FAILURE_LOG_DIR = Path("logs/failures")
FAILURE_LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class FailureEvent:
    """A single failure event with full context."""
    event_type: str  # retrieval_failure, hallucination, low_faithfulness, empty_retrieval
    query: str
    timestamp: float
    request_id: str = ""
    details: Dict = field(default_factory=dict)


class FailureMemory:
    """Persistent failure logger and report generator.

    Logs every failure event to a JSONL file and provides aggregate
    reporting across failure categories.
    """

    def __init__(self, log_dir: Path = FAILURE_LOG_DIR):
        self._log_dir = log_dir
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / "failures.jsonl"

        # In-memory counters for fast telemetry
        self._counts: Dict[str, int] = {
            "retrieval_failure": 0,
            "hallucination": 0,
            "low_faithfulness": 0,
            "empty_retrieval": 0,
            "cache_miss": 0,
            "slow_query": 0,
            "provider_failure": 0,
        }
        self._recent_events: List[FailureEvent] = []
        self._max_recent = 200

        # Load existing counts from file on init
        self._load_existing_counts()

    def _load_existing_counts(self) -> None:
        """Tally up counts from the persisted log file."""
        if not self._log_file.exists():
            return
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        event_type = event.get("event_type", "")
                        if event_type in self._counts:
                            self._counts[event_type] += 1
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning("Failed to load failure memory: %s", str(e))

    def log_retrieval_failure(
        self, query: str, request_id: str = "", reason: str = "",
        total_results: int = 0, scores: List[float] = None,
    ) -> None:
        """Log a retrieval failure (low recall, bad results)."""
        event = FailureEvent(
            event_type="retrieval_failure",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={
                "reason": reason,
                "total_results": total_results,
                "top_scores": (scores or [])[:5],
            },
        )
        self._persist(event)

    def log_empty_retrieval(
        self, query: str, request_id: str = "", query_type: str = "",
    ) -> None:
        """Log a query that returned zero retrieval results."""
        event = FailureEvent(
            event_type="empty_retrieval",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={"query_type": query_type},
        )
        self._persist(event)

    def log_hallucination(
        self, query: str, request_id: str = "",
        hallucination_score: float = 0.0, evidence: str = "",
    ) -> None:
        """Log a detected hallucination event."""
        event = FailureEvent(
            event_type="hallucination",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={
                "hallucination_score": hallucination_score,
                "evidence": evidence[:500],
            },
        )
        self._persist(event)

    def log_low_faithfulness(
        self, query: str, request_id: str = "",
        faithfulness_score: float = 0.0, answer_preview: str = "",
    ) -> None:
        """Log a low-faithfulness generation event."""
        event = FailureEvent(
            event_type="low_faithfulness",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={
                "faithfulness_score": faithfulness_score,
                "answer_preview": answer_preview[:300],
            },
        )
        self._persist(event)

    def log_cache_miss(
        self, query: str, request_id: str = "", reason: str = "",
    ) -> None:
        """Log when the semantic cache was checked but missed."""
        event = FailureEvent(
            event_type="cache_miss",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={"reason": reason},
        )
        self._persist(event)

    def log_slow_query(
        self, query: str, request_id: str = "", latency_ms: int = 0,
    ) -> None:
        """Log queries that exceeded latency thresholds."""
        event = FailureEvent(
            event_type="slow_query",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={"latency_ms": latency_ms},
        )
        self._persist(event)

    def log_provider_failure(
        self, query: str, request_id: str = "", provider: str = "", error: str = "",
    ) -> None:
        """Log upstream LLM provider failures or timeouts."""
        event = FailureEvent(
            event_type="provider_failure",
            query=query,
            timestamp=time.time(),
            request_id=request_id,
            details={"provider": provider, "error": error},
        )
        self._persist(event)

    def _persist(self, event: FailureEvent) -> None:
        """Write event to JSONL log and update in-memory state."""
        self._counts[event.event_type] = self._counts.get(event.event_type, 0) + 1

        # Keep recent in-memory
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events = self._recent_events[-self._max_recent:]

        # Append to JSONL
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event)) + "\n")
        except Exception as e:
            logger.error("Failed to persist failure event: %s", str(e))

        logger.info(
            "FAILURE_LOGGED | type=%s query=%s request_id=%s",
            event.event_type, repr(event.query[:50]), event.request_id,
        )

    def generate_report(self) -> Dict:
        """Generate a summary report from accumulated failure data."""
        report = {
            "total_failures": sum(self._counts.values()),
            "breakdown": dict(self._counts),
            "recent_events": [
                {
                    "type": e.event_type,
                    "query": e.query[:100],
                    "timestamp": e.timestamp,
                    "details": e.details,
                }
                for e in self._recent_events[-20:]
            ],
        }

        # Identify recurring failure patterns
        query_failures: Dict[str, int] = {}
        for e in self._recent_events:
            key = e.query.strip().lower()[:80]
            query_failures[key] = query_failures.get(key, 0) + 1

        recurring = sorted(query_failures.items(), key=lambda x: x[1], reverse=True)[:10]
        report["recurring_failures"] = [
            {"query": q, "count": c} for q, c in recurring
        ]

        # Basic Root Cause Heuristics
        root_causes = {
            "hallucination_due_to_low_retrieval": 0,
            "provider_timeout": 0,
            "semantic_drift": 0,
        }
        
        # Frequency trends (bucket by hour relative to now)
        now = time.time()
        trends = [0] * 24 # last 24 hours
        
        for e in self._recent_events:
            # Trends
            hours_ago = int((now - e.timestamp) / 3600)
            if 0 <= hours_ago < 24:
                trends[23 - hours_ago] += 1
                
            # Root causes
            if e.event_type == "hallucination":
                if "faithfulness_score" in e.details and e.details["faithfulness_score"] < 0.3:
                    root_causes["hallucination_due_to_low_retrieval"] += 1
            elif e.event_type == "provider_failure":
                if "timeout" in e.details.get("error", "").lower():
                    root_causes["provider_timeout"] += 1
            elif e.event_type == "cache_miss":
                if "similarity" in e.details.get("reason", "").lower():
                    root_causes["semantic_drift"] += 1

        report["root_causes"] = root_causes
        report["frequency_trends_last_24h"] = trends
        report["dataset_gaps"] = self.detect_dataset_gaps()

        return report

    def detect_dataset_gaps(self) -> List[Dict[str, Any]]:
        """Identify missing knowledge topics based on recurring refusals and empty retrievals (Refinement 9)."""
        empty_queries = [e.query for e in self._recent_events if e.event_type in ("empty_retrieval", "retrieval_failure")]
        if not empty_queries:
            return []

        from collections import Counter
        words = [w.lower() for q in empty_queries for w in q.split() if len(w) > 4]
        common_topics = Counter(words).most_common(5)

        gaps = []
        for word, count in common_topics:
            gaps.append({
                "topic": word,
                "occurrences": count,
                "recommendation": f"Expand corpus with documents covering '{word}' topic to reduce refusal rates."
            })
        return gaps

    @property
    def stats(self) -> Dict:
        return {
            "total_failures": sum(self._counts.values()),
            **self._counts,
        }


# Singleton instance
failure_memory = FailureMemory()
