"""
Retrieval Ablation Study — Benchmarks retrieval pipeline variants.

Compares:
  1. FAISS Only (dense retrieval)
  2. BM25 Only (sparse retrieval)
  3. FAISS + BM25 (hybrid, no reranker)
  4. FAISS + BM25 + Reranker (full pipeline)

Measures: Recall@5, MRR, nDCG@5, Latency

Uses dataset_v1.json as the evaluation corpus.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import math
import asyncio
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

from vectoria.retrieval.engine import SearchEngine
from vectoria.models import SearchResult
from vectoria.config import CHUNKS_PATH, FAISS_INDEX_PATH, MAPPING_PATH

DATASET_PATH = Path("data/evaluation/datasets/dataset_v1.json")
TOP_K = 5


def load_dataset() -> List[Dict]:
    """Load the golden evaluation dataset."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data if isinstance(data, list) else data.get("questions", [])
    # Filter to questions that have expected_sources
    return [q for q in questions if q.get("expected_sources") or q.get("expected_concepts")]


def compute_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    """Recall@K: fraction of expected items found in top-K."""
    if not expected_ids:
        return 1.0
    retrieved_set = set(retrieved_ids[:k])
    found = len(retrieved_set & set(expected_ids))
    return found / len(expected_ids)


def compute_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    """Mean Reciprocal Rank: 1/(rank of first relevant result)."""
    if not expected_ids:
        return 1.0
    expected_set = set(expected_ids)
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in expected_set:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    """nDCG@K: Normalized Discounted Cumulative Gain."""
    if not expected_ids:
        return 1.0
    expected_set = set(expected_ids)
    
    # DCG
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        rel = 1.0 if rid in expected_set else 0.0
        dcg += rel / math.log2(i + 2)

    # Ideal DCG
    ideal_rels = sorted([1.0] * min(len(expected_ids), k) + [0.0] * max(0, k - len(expected_ids)), reverse=True)
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal_rels))

    return dcg / idcg if idcg > 0 else 0.0


def run_ablation():
    """Run the full ablation study."""
    print("=" * 70)
    print("RETRIEVAL ABLATION STUDY")
    print("=" * 70)

    dataset = load_dataset()
    print(f"Loaded {len(dataset)} evaluation questions")

    # --- Variant 1: FAISS Only ---
    print("\n--- Variant 1: FAISS Only (no BM25, no reranker) ---")
    engine_faiss = SearchEngine(use_reranker=False)
    engine_faiss.load()
    # Override BM25 scores to always return zeros (effectively disabling BM25)
    class ZeroBM25:
        def get_scores(self, query):
            return np.zeros(len(engine_faiss._chunks))
    engine_faiss._bm25 = ZeroBM25()
    results_faiss = benchmark_engine(engine_faiss, dataset, "FAISS Only")

    # --- Variant 2: BM25 Only ---
    print("\n--- Variant 2: BM25 Only ---")
    results_bm25 = benchmark_bm25_only(dataset)

    # --- Variant 3: FAISS + BM25 (no reranker) ---
    print("\n--- Variant 3: FAISS + BM25 (Hybrid, no reranker) ---")
    engine_hybrid = SearchEngine(use_reranker=False)
    engine_hybrid.load()
    results_hybrid = benchmark_engine(engine_hybrid, dataset, "FAISS+BM25")

    # --- Variant 4: FAISS + BM25 + Reranker ---
    print("\n--- Variant 4: FAISS + BM25 + Reranker (Full Pipeline) ---")
    engine_full = SearchEngine(use_reranker=True)
    engine_full.load()
    results_full = benchmark_engine(engine_full, dataset, "FAISS+BM25+Reranker")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("ABLATION STUDY SUMMARY")
    print("=" * 70)
    all_results = [results_faiss, results_bm25, results_hybrid, results_full]
    print(f"{'Variant':<30} {'Recall@5':>10} {'MRR':>10} {'nDCG@5':>10} {'Latency(ms)':>12}")
    print("-" * 72)
    for r in all_results:
        print(f"{r['variant']:<30} {r['recall_at_5']:>10.4f} {r['mrr']:>10.4f} {r['ndcg_at_5']:>10.4f} {r['avg_latency_ms']:>12.1f}")

    # Save results
    output_path = Path("data/evaluation/reports/ablation_study.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {output_path}")


def benchmark_engine(engine: SearchEngine, dataset: List[Dict], variant_name: str) -> Dict:
    """Run benchmark against a configured engine variant."""
    recalls = []
    mrrs = []
    ndcgs = []
    latencies = []

    for q in dataset:
        query = q["query"]
        expected = q.get("expected_sources", [])

        engine.clear_cache()
        start = time.perf_counter()
        try:
            results = engine.search(query, top_k=TOP_K)
        except Exception as e:
            print(f"  ERROR on query '{query[:50]}': {e}")
            continue
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        retrieved_ids = [r.chunk.chunk_id for r in results]
        recalls.append(compute_recall_at_k(retrieved_ids, expected, TOP_K))
        mrrs.append(compute_mrr(retrieved_ids, expected))
        ndcgs.append(compute_ndcg_at_k(retrieved_ids, expected, TOP_K))

    result = {
        "variant": variant_name,
        "recall_at_5": np.mean(recalls) if recalls else 0.0,
        "mrr": np.mean(mrrs) if mrrs else 0.0,
        "ndcg_at_5": np.mean(ndcgs) if ndcgs else 0.0,
        "avg_latency_ms": np.mean(latencies) if latencies else 0.0,
        "samples": len(recalls),
    }
    print(f"  Recall@5={result['recall_at_5']:.4f}  MRR={result['mrr']:.4f}  nDCG@5={result['ndcg_at_5']:.4f}  Latency={result['avg_latency_ms']:.1f}ms")
    return result


def benchmark_bm25_only(dataset: List[Dict]) -> Dict:
    """Benchmark BM25 retrieval without FAISS."""
    from vectoria.retrieval.bm25 import BM25Retriever
    from vectoria.storage import load_chunks

    chunks = load_chunks(CHUNKS_PATH)
    bm25 = BM25Retriever()
    bm25.fit(chunks)

    recalls = []
    mrrs = []
    ndcgs = []
    latencies = []

    for q in dataset:
        query = q["query"]
        expected = q.get("expected_sources", [])

        start = time.perf_counter()
        scores = bm25.get_scores(query)
        top_indices = np.argsort(scores)[::-1][:TOP_K]
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

        retrieved_ids = [chunks[i].chunk_id for i in top_indices if scores[i] > 0][:TOP_K]
        recalls.append(compute_recall_at_k(retrieved_ids, expected, TOP_K))
        mrrs.append(compute_mrr(retrieved_ids, expected))
        ndcgs.append(compute_ndcg_at_k(retrieved_ids, expected, TOP_K))

    result = {
        "variant": "BM25 Only",
        "recall_at_5": np.mean(recalls) if recalls else 0.0,
        "mrr": np.mean(mrrs) if mrrs else 0.0,
        "ndcg_at_5": np.mean(ndcgs) if ndcgs else 0.0,
        "avg_latency_ms": np.mean(latencies) if latencies else 0.0,
        "samples": len(recalls),
    }
    print(f"  Recall@5={result['recall_at_5']:.4f}  MRR={result['mrr']:.4f}  nDCG@5={result['ndcg_at_5']:.4f}  Latency={result['avg_latency_ms']:.1f}ms")
    return result


if __name__ == "__main__":
    run_ablation()
