"""
Retrieval Analysis — Identify failure patterns in the retrieval pipeline.

Produces:
  1. Top 50 Retrieval Failures (lowest Recall@5)
  2. Top 50 Retrieval Successes (highest Recall@5)
  3. Top 20 Ambiguous Queries (multiple intent classifications)
  4. Top 20 Hallucination Trigger Queries (low grounding)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import numpy as np
from typing import List, Dict
from pathlib import Path

from vectoria.retrieval.engine import SearchEngine
from vectoria.generation.intent_router import HybridIntentRouter
from vectoria.config import CHUNKS_PATH

DATASET_PATH = Path("data/evaluation/datasets/dataset_v1.json")
OUTPUT_DIR = Path("data/evaluation/reports")
TOP_K = 5


def load_dataset() -> List[Dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("questions", [])


def compute_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    found = len(set(retrieved_ids[:k]) & set(expected_ids))
    return found / len(expected_ids)


def analyze_retrieval():
    print("=" * 70)
    print("RETRIEVAL ANALYSIS")
    print("=" * 70)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} evaluation questions")

    # Load engine with full pipeline
    engine = SearchEngine(use_reranker=True)
    engine.load()

    router = HybridIntentRouter()

    results_data = []

    for i, q in enumerate(dataset):
        query = q["query"]
        expected = q.get("expected_sources", [])
        category = q.get("category", "unknown")
        difficulty = q.get("difficulty", "unknown")

        # Classify intent
        intent = router.classify(query)

        engine.clear_cache()
        start = time.perf_counter()
        try:
            results = engine.search(query, top_k=TOP_K)
        except Exception as e:
            results_data.append({
                "query": query,
                "category": category,
                "difficulty": difficulty,
                "recall_at_5": 0.0,
                "intent_type": intent.query_type.value,
                "intent_confidence": intent.confidence,
                "error": str(e),
                "scores": [],
                "retrieved_ids": [],
                "expected_ids": expected,
            })
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000

        retrieved_ids = [r.chunk.chunk_id for r in results]
        scores = [r.score for r in results]
        recall = compute_recall_at_k(retrieved_ids, expected, TOP_K)

        # Detect ambiguity: low intent confidence
        is_ambiguous = intent.confidence < 0.85

        # Detect potential hallucination triggers: low retrieval scores
        avg_score = np.mean(scores) if scores else 0.0
        is_hallucination_risk = avg_score < 0.2 and len(results) > 0

        results_data.append({
            "query": query,
            "category": category,
            "difficulty": difficulty,
            "recall_at_5": recall,
            "intent_type": intent.query_type.value,
            "intent_confidence": intent.confidence,
            "avg_score": float(avg_score),
            "top_score": float(scores[0]) if scores else 0.0,
            "latency_ms": elapsed_ms,
            "retrieved_count": len(results),
            "retrieved_ids": retrieved_ids,
            "expected_ids": expected,
            "scores": [float(s) for s in scores],
            "is_ambiguous": is_ambiguous,
            "is_hallucination_risk": is_hallucination_risk,
        })

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(dataset)} queries...")

    # --- Sort and extract ---
    # Top 50 Failures (lowest recall)
    sorted_by_recall = sorted(results_data, key=lambda x: x["recall_at_5"])
    top_failures = sorted_by_recall[:50]

    # Top 50 Successes (highest recall)
    top_successes = sorted(results_data, key=lambda x: x["recall_at_5"], reverse=True)[:50]

    # Top 20 Ambiguous
    ambiguous = [r for r in results_data if r.get("is_ambiguous")]
    ambiguous.sort(key=lambda x: x.get("intent_confidence", 1.0))
    top_ambiguous = ambiguous[:20]

    # Top 20 Hallucination Triggers
    hall_triggers = [r for r in results_data if r.get("is_hallucination_risk")]
    hall_triggers.sort(key=lambda x: x.get("avg_score", 0.0))
    top_hallucination = hall_triggers[:20]

    # --- Print summaries ---
    print(f"\n--- Top 10 Retrieval FAILURES (of {len(top_failures)}) ---")
    for f in top_failures[:10]:
        print(f"  Recall={f['recall_at_5']:.2f} | {f['category']:>12} | {f['query'][:70]}")

    print(f"\n--- Top 10 Retrieval SUCCESSES (of {len(top_successes)}) ---")
    for s in top_successes[:10]:
        print(f"  Recall={s['recall_at_5']:.2f} | {s['category']:>12} | {s['query'][:70]}")

    print(f"\n--- Ambiguous Queries: {len(top_ambiguous)} ---")
    for a in top_ambiguous[:10]:
        print(f"  Conf={a['intent_confidence']:.2f} | {a['intent_type']:>15} | {a['query'][:60]}")

    print(f"\n--- Hallucination Triggers: {len(top_hallucination)} ---")
    for h in top_hallucination[:10]:
        print(f"  AvgScore={h['avg_score']:.4f} | {h['query'][:60]}")

    # --- Save ---
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "summary": {
            "total_queries": len(results_data),
            "avg_recall_at_5": float(np.mean([r["recall_at_5"] for r in results_data])),
            "total_failures": len([r for r in results_data if r["recall_at_5"] == 0]),
            "total_ambiguous": len(ambiguous),
            "total_hallucination_risk": len(hall_triggers),
        },
        "top_50_failures": top_failures,
        "top_50_successes": top_successes,
        "top_20_ambiguous": top_ambiguous,
        "top_20_hallucination_triggers": top_hallucination,
    }
    output_path = OUTPUT_DIR / "retrieval_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to {output_path}")


if __name__ == "__main__":
    analyze_retrieval()
