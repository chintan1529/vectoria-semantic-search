"""
Benchmark Asset Versioning Module (Refinement 5).

Tracks semantic versioning for dataset, schema, benchmark runs, metric algorithms, prompts, and model weights.
"""

from typing import Dict
from pydantic import BaseModel


class BenchmarkAssetVersions(BaseModel):
    dataset_version: str = "v2.1.0"
    schema_version: str = "v2.0.0"
    benchmark_version: str = "v3.0.0"
    metric_version: str = "v2.1.0"
    prompt_version: str = "v3.0.0"
    model_version: str = "gemini-2.5-flash"
    embed_model_version: str = "sentence-transformers/all-MiniLM-L6-v2"
    rerank_model_version: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def to_dict(self) -> Dict[str, str]:
        return self.model_dump()


def get_current_asset_versions() -> BenchmarkAssetVersions:
    return BenchmarkAssetVersions()
