"""
Query Expansion Study — Compare retrieval quality across expansion strategies.

Strategies:
  1. Raw Query (baseline)
  2. Keyword Expansion (add synonyms/related terms via heuristics)
  3. LLM Expansion (use Gemini to rewrite the query for better retrieval)

Measures: Recall@5, MRR, nDCG@5, Latency
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import math
import asyncio
import numpy as np
from typing import List, Dict
from pathlib import Path

from vectoria.retrieval.engine import SearchEngine

DATASET_PATH = Path("data/evaluation/datasets/dataset_v1.json")
OUTPUT_PATH = Path("data/evaluation/reports/query_expansion_study.json")
TOP_K = 5

# Simple keyword expansion using synonym-like augmentation
EXPANSION_MAP = {
    "how": ["mechanism", "process", "method"],
    "what": ["definition", "meaning", "concept"],
    "why": ["reason", "cause", "motivation"],
    "compare": ["difference", "similarity", "versus"],
    "explain": ["describe", "elaborate", "detail"],
    "best": ["optimal", "recommended", "top"],
    "improve": ["optimize", "enhance", "boost"],
    "learn": ["training", "learning", "education"],
    "model": ["architecture", "algorithm", "system"],
    "network": ["neural network", "graph", "architecture"],
    "data": ["dataset", "information", "corpus"],
    "search": ["retrieval", "query", "lookup"],
}


def load_dataset() -> List[Dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data if isinstance(data, list) else data.get("questions", [])
    return [q for q in questions if q.get("expected_sources")][:50]  # Use first 50 for study


def keyword_expand(query: str) -> str:
    """Expand query with synonym-like keywords."""
    words = query.lower().split()
    expansions = []
    for word in words:
        if word in EXPANSION_MAP:
            expansions.extend(EXPANSION_MAP[word][:1])  # Add one synonym
    if expansions:
        return query + " " + " ".join(expansions)
    return query


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


def run_study():
    print("=" * 70)
    print("QUERY EXPANSION STUDY")
    print("=" * 70)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} evaluation questions")

    engine = SearchEngine(use_reranker=True)
    engine.load()

    strategies = {
        "Raw Query": lambda q: q,
        "Keyword Expansion": keyword_expand,
    }

    all_results = []

    for strategy_name, expand_fn in strategies.items():
        print(f"\n--- Strategy: {strategy_name} ---")
        recalls = []
        mrrs = []
        ndcgs = []
        latencies = []

        for q in dataset:
            query = q["query"]
            expected = q.get("expected_sources", [])

            expanded = expand_fn(query)
            engine.clear_cache()
            start = time.perf_counter()
            try:
                results = engine.search(expanded, top_k=TOP_K)
            except Exception as e:
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)

            retrieved_ids = [r.chunk.chunk_id for r in results]
            recalls.append(compute_recall_at_k(retrieved_ids, expected, TOP_K))
            mrrs.append(compute_mrr(retrieved_ids, expected))
            ndcgs.append(compute_ndcg_at_k(retrieved_ids, expected, TOP_K))

        result = {
            "strategy": strategy_name,
            "recall_at_5": float(np.mean(recalls)) if recalls else 0.0,
            "mrr": float(np.mean(mrrs)) if mrrs else 0.0,
            "ndcg_at_5": float(np.mean(ndcgs)) if ndcgs else 0.0,
            "avg_latency_ms": float(np.mean(latencies)) if latencies else 0.0,
            "samples": len(recalls),
        }
        all_results.append(result)
        print(f"  Recall@5={result['recall_at_5']:.4f}  MRR={result['mrr']:.4f}  nDCG@5={result['ndcg_at_5']:.4f}  Latency={result['avg_latency_ms']:.1f}ms")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("QUERY EXPANSION STUDY SUMMARY")
    print("=" * 70)
    print(f"{'Strategy':<25} {'Recall@5':>10} {'MRR':>10} {'nDCG@5':>10} {'Latency(ms)':>12}")
    print("-" * 67)
    for r in all_results:
        print(f"{r['strategy']:<25} {r['recall_at_5']:>10.4f} {r['mrr']:>10.4f} {r['ndcg_at_5']:>10.4f} {r['avg_latency_ms']:>12.1f}")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    run_study()
