"""
Experiment Logger & Configuration Snapshots

Persists every benchmark execution and optimization run.
Supports replaying historical experiments.
"""
import json
import time
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from backend.core.logging import logger

EXPERIMENT_DIR = Path("logs/experiments")
EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

def _get_git_commit() -> str:
    """Helper to grab current git commit hash, if available."""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return commit.decode("utf-8").strip()
    except Exception:
        return "unknown"

@dataclass
class ConfigSnapshot:
    embedding_model: str = "all-MiniLM-L6-v2"
    reranker: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    prompt_version: str = "v2_structured"
    context_size_top_k: int = 5
    provider: str = "anthropic/claude-3-opus"
    cache_enabled: bool = True
    cache_threshold: float = 0.97
    dataset_version: str = "dataset_v1.json"
    git_commit: str = field(default_factory=_get_git_commit)

@dataclass
class ExperimentRecord:
    experiment_id: str
    timestamp: float
    query: str
    retrieved_chunks: List[Dict[str, Any]]
    prompt: str
    response: str
    metrics: Dict[str, float]
    config: ConfigSnapshot

class ExperimentLogger:
    def __init__(self, log_dir: Path = EXPERIMENT_DIR):
        self.log_dir = log_dir
        self.log_file = self.log_dir / "experiments.jsonl"
        self._cache = []
        self._load_cache()

    def _load_cache(self, limit: int = 100):
        """Load recent experiments into memory."""
        if not self.log_file.exists():
            return
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    self._cache.append(json.loads(line.strip()))
        except Exception as e:
            logger.warning(f"Failed to load experiments cache: {e}")

    def log_experiment(
        self,
        experiment_id: str,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        prompt: str,
        response: str,
        metrics: Dict[str, float],
        config: ConfigSnapshot = None
    ) -> None:
        """Persist a benchmark execution."""
        if config is None:
            config = ConfigSnapshot()
            
        record = ExperimentRecord(
            experiment_id=experiment_id,
            timestamp=time.time(),
            query=query,
            retrieved_chunks=retrieved_chunks,
            prompt=prompt,
            response=response,
            metrics=metrics,
            config=config
        )
        
        record_dict = asdict(record)
        self._cache.append(record_dict)
        if len(self._cache) > 500:
            self._cache.pop(0)
            
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record_dict) + "\n")
            logger.info(f"EXPERIMENT_LOGGED | id={experiment_id} query='{query[:30]}...'")
        except Exception as e:
            logger.error(f"Failed to log experiment {experiment_id}: {e}")

    def get_history(self, limit: int = 50) -> List[Dict]:
        """Retrieve recent experiments for replay or regression monitoring."""
        return self._cache[-limit:]

# Singleton
experiment_logger = ExperimentLogger()
