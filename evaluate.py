#!/usr/bin/env python3
"""
Evaluate -- Run the full retrieval evaluation suite on Vectoria.

Usage:
    python evaluate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def main() -> None:
    # -- Load engine ---------------------------------------------------
    print("Loading search engine...")
    engine = SearchEngine()
    engine.load()
    print(f"Engine ready: {len(engine._chunks)} chunks indexed")

    # -- Run semantic evaluation ----------------------------------------
    print("\nRunning semantic retrieval evaluation (40 queries)...\n")
    evaluator = RetrievalEvaluator(k_values=[1, 3, 5, 10])
    report = evaluator.evaluate(engine, ALL_QUERIES)

    # Print formatted report
    print(format_report(report))

    # -- BM25 baseline comparison --------------------------------------
    print("=" * 60)
    print("  BM25 BASELINE COMPARISON")
    print("=" * 60)

    chunks = load_chunks()
    bm25 = BM25Baseline(chunks)
    bm25_metrics = bm25.evaluate(ALL_QUERIES, k_values=[1, 3, 5, 10])

    print("\n  {:15s}  {:>8s}  {:>8s}  {:>10s}".format(
        "Metric@K", "Semantic", "BM25", "Delta"))
    print("  " + "-" * 45)

    for metric_name in ("precision", "recall", "mrr", "hit"):
        for k in [1, 3, 5, 10]:
            sem = report.aggregate[metric_name][k]
            bm = bm25_metrics[metric_name][k]
            delta = sem - bm
            sign = "+" if delta >= 0 else ""
            print(f"  {metric_name.upper()}@{k:<3d}         "
                  f"{sem:6.4f}    {bm:6.4f}    {sign}{delta:.4f}")
        print()

    print("=" * 60)
    print("  EVALUATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
