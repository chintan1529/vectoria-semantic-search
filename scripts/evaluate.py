#!/usr/bin/env python3
"""
Evaluate -- Comprehensive retrieval evaluation with before/after comparison.

Runs three retrieval configurations and compares:
  1. Dense-only (FAISS, no BM25, no reranker)
  2. Hybrid + Reranking (FAISS + BM25 RRF + CrossEncoder)
  3. BM25 Baseline (lexical only)

Usage:
    python evaluate.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from vectoria.evaluation.evaluator import (
    BM25Baseline,
    RetrievalEvaluator,
    format_report,
)
from vectoria.evaluation.ground_truth import ALL_QUERIES
from vectoria.retrieval.engine import SearchEngine
from vectoria.storage import load_chunks


def run_evaluation_mode(engine: SearchEngine, label: str, k_values=None):
    """Run evaluation on a given engine config and return aggregate metrics + latency."""
    k_values = k_values or [1, 3, 5, 10]
    evaluator = RetrievalEvaluator(k_values=k_values)

    start = time.perf_counter()
    report = evaluator.evaluate(engine, ALL_QUERIES)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Per-query latency measurement
    latencies = []
    for eq in ALL_QUERIES[:20]:  # Sample 20 for latency measurement
        engine.clear_cache()
        t0 = time.perf_counter()
        engine.search(eq.query, top_k=5)
        latencies.append((time.perf_counter() - t0) * 1000)

    avg_latency = float(np.mean(latencies)) if latencies else 0.0

    return report, avg_latency, elapsed_ms


def main() -> None:
    print("=" * 70)
    print("  VECTORIA RETRIEVAL EVALUATION — BEFORE vs AFTER")
    print("=" * 70)
    print()

    # ── 1. Load chunks (shared) ─────────────────────────────────────
    chunks = load_chunks()
    print(f"  Loaded {len(chunks)} chunks\n")

    # ── 2. Dense-Only Mode ──────────────────────────────────────────
    print("─" * 70)
    print("  [1/3] DENSE-ONLY (FAISS only, no BM25, no reranker)")
    print("─" * 70)

    engine_dense = SearchEngine(use_reranker=False)
    engine_dense.load()
    # Disable BM25 by replacing get_scores with a zero-score function
    original_bm25_get_scores = engine_dense._bm25.get_scores
    engine_dense._bm25.get_scores = lambda q: np.zeros(len(chunks))
    # Warm up
    engine_dense.search("warmup", top_k=1)
    engine_dense.clear_cache()

    report_dense, latency_dense, time_dense = run_evaluation_mode(engine_dense, "Dense-Only")
    print(format_report(report_dense))

    # Restore BM25 for hybrid mode
    engine_dense._bm25.get_scores = original_bm25_get_scores

    # ── 3. Hybrid + Reranking Mode ──────────────────────────────────
    print()
    print("─" * 70)
    print("  [2/3] HYBRID + RERANKING (FAISS + BM25 RRF + CrossEncoder)")
    print("─" * 70)

    engine_hybrid = SearchEngine(use_reranker=True)
    engine_hybrid.load()
    engine_hybrid.search("warmup", top_k=1)
    engine_hybrid.clear_cache()

    report_hybrid, latency_hybrid, time_hybrid = run_evaluation_mode(engine_hybrid, "Hybrid+Rerank")
    print(format_report(report_hybrid))

    # ── 4. BM25 Baseline ───────────────────────────────────────────
    print()
    print("─" * 70)
    print("  [3/3] BM25 BASELINE (Lexical Only)")
    print("─" * 70)

    bm25 = BM25Baseline(chunks)
    bm25_metrics = bm25.evaluate(ALL_QUERIES, k_values=[1, 3, 5, 10])
    # BM25 latency
    bm25_latencies = []
    for eq in ALL_QUERIES[:20]:
        t0 = time.perf_counter()
        bm25.search(eq.query, top_k=5)
        bm25_latencies.append((time.perf_counter() - t0) * 1000)
    latency_bm25 = float(np.mean(bm25_latencies)) if bm25_latencies else 0.0

    # ── 5. Comparison Table ─────────────────────────────────────────
    print()
    print("=" * 70)
    print("  BEFORE vs AFTER COMPARISON")
    print("=" * 70)
    print()
    print(f"  {'Metric@K':<18s}  {'BM25':>10s}  {'Dense':>10s}  {'Hybrid+RR':>10s}  {'Δ Dense→H+R':>12s}")
    print("  " + "─" * 65)

    comparison_data = {}

    for metric_name in ("precision", "recall", "mrr", "hit"):
        comparison_data[metric_name] = {}
        for k in [1, 3, 5, 10]:
            bm = bm25_metrics[metric_name][k]
            dense = report_dense.aggregate[metric_name][k]
            hybrid = report_hybrid.aggregate[metric_name][k]
            delta = hybrid - dense
            sign = "+" if delta >= 0 else ""

            comparison_data[metric_name][k] = {
                "bm25": round(bm, 4),
                "dense": round(dense, 4),
                "hybrid_rerank": round(hybrid, 4),
                "delta": round(delta, 4),
            }

            print(
                f"  {metric_name.upper()}@{k:<3d}          "
                f"  {bm:>8.4f}  {dense:>8.4f}"
                f"  {hybrid:>8.4f}  {sign}{delta:>10.4f}"
            )
        print()

    # Latency comparison
    print("  " + "─" * 65)
    print(
        f"  {'Avg Latency':<18s}"
        f"  {latency_bm25:>8.1f}ms"
        f"  {latency_dense:>8.1f}ms"
        f"  {latency_hybrid:>8.1f}ms"
        f"  {'':>12s}"
    )
    print()

    # ── 6. Improvement Summary ──────────────────────────────────────
    print("=" * 70)
    print("  IMPROVEMENT SUMMARY (K=5)")
    print("=" * 70)
    print()

    for metric_name, label in [
        ("precision", "Precision@5"),
        ("recall", "Recall@5"),
        ("mrr", "MRR@5"),
        ("hit", "Hit Rate@5"),
    ]:
        dense_val = report_dense.aggregate[metric_name][5]
        hybrid_val = report_hybrid.aggregate[metric_name][5]
        delta = hybrid_val - dense_val

        if dense_val > 0:
            pct_improvement = ((hybrid_val - dense_val) / dense_val) * 100
        else:
            pct_improvement = 100.0 if hybrid_val > 0 else 0.0

        bar_dense = "█" * int(dense_val * 30)
        bar_hybrid = "█" * int(hybrid_val * 30)

        sign = "+" if delta >= 0 else ""
        print(f"  {label:<15s}")
        print(f"    Dense:     {dense_val:.4f}  {bar_dense}")
        print(f"    Hybrid+RR: {hybrid_val:.4f}  {bar_hybrid}")
        print(f"    Delta:     {sign}{delta:.4f} ({sign}{pct_improvement:.1f}%)")
        print()

    # ── 7. Domain Breakdown Comparison ──────────────────────────────
    print("=" * 70)
    print("  DOMAIN BREAKDOWN (K=5)")
    print("=" * 70)
    print()

    for domain in sorted(report_hybrid.domain_metrics.keys()):
        print(f"  [{domain.upper()}]")
        for metric_name in ("precision", "recall", "mrr", "hit"):
            d_val = report_dense.domain_metrics.get(domain, {}).get(metric_name, {}).get(5, 0)
            h_val = report_hybrid.domain_metrics.get(domain, {}).get(metric_name, {}).get(5, 0)
            delta = h_val - d_val
            sign = "+" if delta >= 0 else ""
            print(
                f"    {metric_name.upper():<12s}  Dense={d_val:.4f}  Hybrid+RR={h_val:.4f}  Δ={sign}{delta:.4f}"
            )
        print()

    # ── 8. Save Results ─────────────────────────────────────────────
    output = {
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
        "total_queries": len(ALL_QUERIES),
        "chunks_indexed": len(chunks),
        "comparison": comparison_data,
        "latencies": {
            "bm25_avg_ms": round(latency_bm25, 2),
            "dense_avg_ms": round(latency_dense, 2),
            "hybrid_rerank_avg_ms": round(latency_hybrid, 2),
        },
        "dense_failures": len(report_dense.failures),
        "hybrid_failures": len(report_hybrid.failures),
    }

    output_path = PROJECT_ROOT / "evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {output_path}")

    print()
    print("=" * 70)
    print("  EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
