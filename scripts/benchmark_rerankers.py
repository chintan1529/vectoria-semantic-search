"""
Reranker Benchmark — Compare cross-encoder models across balanced query categories.

Models:
  - cross-encoder/ms-marco-MiniLM-L-6-v2 (current)
  - BAAI/bge-reranker-base
  - BAAI/bge-reranker-v2-m3

Sample: 50 queries (10 factual, 10 analytical, 10 comparison, 10 multi-hop, 10 adversarial)
Metrics: Latency, nDCG@5, Recall@5, MRR
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import math
import numpy as np
from typing import List, Dict
from pathlib import Path

from vectoria.retrieval.engine import SearchEngine
from vectoria.reranking.reranker import CrossEncoderReranker
from vectoria.storage import load_chunks
from vectoria.config import CHUNKS_PATH

DATASET_PATH = Path("data/evaluation/datasets/dataset_v1.json")
OUTPUT_PATH = Path("data/evaluation/reports/reranker_benchmark.json")
TOP_K = 5

RERANKER_MODELS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "BAAI/bge-reranker-base",
    "BAAI/bge-reranker-v2-m3",
]


def load_balanced_sample() -> List[Dict]:
    """Load a balanced 50-question sample across categories."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data if isinstance(data, list) else data.get("questions", [])

    categories = {
        "factual": [],
        "analytical": [],
        "comparison": [],
        "multi_hop": [],
        "adversarial": [],
    }

    for q in questions:
        cat = q.get("category", "").lower().replace("-", "_").replace(" ", "_")
        difficulty = q.get("difficulty", "").lower()
        
        if cat in categories and len(categories[cat]) < 10:
            categories[cat].append(q)
        elif "multi" in cat and len(categories["multi_hop"]) < 10:
            categories["multi_hop"].append(q)
        elif "adversarial" in difficulty and len(categories["adversarial"]) < 10:
            categories["adversarial"].append(q)

    # Flatten and fill any gaps
    sample = []
    for cat_name, items in categories.items():
        print(f"  Category '{cat_name}': {len(items)} questions")
        sample.extend(items)

    print(f"Total balanced sample: {len(sample)} questions")
    return sample


def compute_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    found = len(set(retrieved_ids[:k]) & set(expected_ids))
    return found / len(expected_ids)


def compute_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    if not expected_ids:
        return 1.0
    expected_set = set(expected_ids)
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in expected_set:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    expected_set = set(expected_ids)
    dcg = sum((1.0 if rid in expected_set else 0.0) / math.log2(i + 2) for i, rid in enumerate(retrieved_ids[:k]))
    ideal_rels = sorted([1.0] * min(len(expected_ids), k) + [0.0] * max(0, k - len(expected_ids)), reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal_rels))
    return dcg / idcg if idcg > 0 else 0.0


def benchmark_rerankers():
    """Run the reranker bake-off."""
    print("=" * 70)
    print("RERANKER BENCHMARK")
    print("=" * 70)

    sample = load_balanced_sample()
    if not sample:
        print("ERROR: No evaluation questions found!")
        return

    all_results = []

    for model_name in RERANKER_MODELS:
        print(f"\n--- Testing: {model_name} ---")
        
        # Create engine with specific reranker
        engine = SearchEngine(use_reranker=True)
        engine._reranker = CrossEncoderReranker(model_name=model_name)
        engine.load()

        recalls = []
        mrrs = []
        ndcgs = []
        latencies = []
        errors = 0

        for q in sample:
            query = q["query"]
            expected = q.get("expected_sources", [])

            engine.clear_cache()
            start = time.perf_counter()
            try:
                results = engine.search(query, top_k=TOP_K)
            except Exception as e:
                print(f"  ERROR: {e}")
                errors += 1
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            retrieved_ids = [r.chunk.chunk_id for r in results]
            recalls.append(compute_recall_at_k(retrieved_ids, expected, TOP_K))
            mrrs.append(compute_mrr(retrieved_ids, expected))
            ndcgs.append(compute_ndcg_at_k(retrieved_ids, expected, TOP_K))

        result = {
            "model": model_name,
            "recall_at_5": float(np.mean(recalls)) if recalls else 0.0,
            "mrr": float(np.mean(mrrs)) if mrrs else 0.0,
            "ndcg_at_5": float(np.mean(ndcgs)) if ndcgs else 0.0,
            "avg_latency_ms": float(np.mean(latencies)) if latencies else 0.0,
            "p95_latency_ms": float(np.percentile(latencies, 95)) if latencies else 0.0,
            "errors": errors,
            "samples": len(recalls),
        }
        all_results.append(result)
        print(f"  Recall@5={result['recall_at_5']:.4f}  MRR={result['mrr']:.4f}  nDCG@5={result['ndcg_at_5']:.4f}")
        print(f"  Avg Latency={result['avg_latency_ms']:.1f}ms  P95={result['p95_latency_ms']:.1f}ms  Errors={errors}")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("RERANKER BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"{'Model':<42} {'Recall@5':>10} {'MRR':>8} {'nDCG@5':>8} {'Latency':>10} {'P95':>10}")
    print("-" * 88)
    for r in all_results:
        print(f"{r['model']:<42} {r['recall_at_5']:>10.4f} {r['mrr']:>8.4f} {r['ndcg_at_5']:>8.4f} {r['avg_latency_ms']:>10.1f} {r['p95_latency_ms']:>10.1f}")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    benchmark_rerankers()
