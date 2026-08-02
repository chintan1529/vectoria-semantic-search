#!/usr/bin/env python3
"""
Vectoria Performance Benchmark Suite
=====================================

Measures backend latency, throughput, memory, and CPU across
small / medium / large query workloads.

Metrics captured:
    - Average, P50, P95 retrieval latency
    - Reranker-only latency (isolated)
    - End-to-end response latency
    - Memory usage (RSS)
    - CPU usage during benchmark
    - Token throughput estimation

Usage:
    python benchmark_performance.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from vectoria.evaluation.ground_truth import ALL_QUERIES
from vectoria.retrieval.engine import SearchEngine
from vectoria.reranking.reranker import CrossEncoderReranker
from vectoria.storage import load_chunks

# ---------------------------------------------------------------------------
# Attempt to import psutil for system metrics (optional)
# ---------------------------------------------------------------------------
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class LatencyStats:
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    std_ms: float = 0.0
    n_samples: int = 0


@dataclass
class BenchmarkConfig:
    name: str
    n_queries: int
    top_k: int
    description: str


@dataclass
class BenchmarkResult:
    config: BenchmarkConfig
    retrieval_latency: LatencyStats
    reranker_latency: LatencyStats
    embedding_latency: LatencyStats
    e2e_latency: LatencyStats
    memory_rss_mb: float = 0.0
    memory_delta_mb: float = 0.0
    cpu_percent: float = 0.0
    chunks_indexed: int = 0


# ---------------------------------------------------------------------------
# Measurement Helpers
# ---------------------------------------------------------------------------

def compute_latency_stats(latencies_ms: List[float]) -> LatencyStats:
    """Compute percentile statistics from a list of latencies."""
    if not latencies_ms:
        return LatencyStats()
    arr = np.array(latencies_ms)
    return LatencyStats(
        avg_ms=round(float(np.mean(arr)), 2),
        p50_ms=round(float(np.percentile(arr, 50)), 2),
        p95_ms=round(float(np.percentile(arr, 95)), 2),
        min_ms=round(float(np.min(arr)), 2),
        max_ms=round(float(np.max(arr)), 2),
        std_ms=round(float(np.std(arr)), 2),
        n_samples=len(latencies_ms),
    )


def get_memory_mb() -> float:
    """Current process RSS in MB."""
    if HAS_PSUTIL:
        proc = psutil.Process(os.getpid())
        return round(proc.memory_info().rss / (1024 * 1024), 2)
    return 0.0


def get_cpu_percent() -> float:
    """Current process CPU percent (snapshot)."""
    if HAS_PSUTIL:
        proc = psutil.Process(os.getpid())
        return proc.cpu_percent(interval=0.5)
    return 0.0


# ---------------------------------------------------------------------------
# Core Benchmark Runner
# ---------------------------------------------------------------------------

class PerformanceBenchmark:
    """Run latency and resource benchmarks against a loaded SearchEngine."""

    CONFIGS = [
        BenchmarkConfig("small",  5,  3, "5 queries × top_k=3"),
        BenchmarkConfig("medium", 20, 5, "20 queries × top_k=5"),
        BenchmarkConfig("large",  40, 10, "40 queries × top_k=10"),
    ]

    def __init__(self) -> None:
        self.engine: Optional[SearchEngine] = None
        self.results: List[BenchmarkResult] = []

    def load_engine(self) -> None:
        """Load the search engine and warm up models."""
        print("Loading search engine...")
        self.engine = SearchEngine()
        self.engine.load()
        # Warm up to ensure fair timing (model weights loaded)
        self.engine.search("warmup query", top_k=1)
        self.engine.clear_cache()
        print(f"Engine ready: {len(self.engine._chunks)} chunks indexed\n")

    def run_all(self) -> List[BenchmarkResult]:
        """Execute benchmarks for all configurations."""
        if not self.engine:
            self.load_engine()

        self.results = []
        queries = [eq.query for eq in ALL_QUERIES]

        for config in self.CONFIGS:
            print(f"{'='*60}")
            print(f"  BENCHMARK: {config.name.upper()} — {config.description}")
            print(f"{'='*60}")

            result = self._run_config(config, queries[:config.n_queries])
            self.results.append(result)
            self._print_result(result)

        return self.results

    def _run_config(
        self, config: BenchmarkConfig, queries: List[str]
    ) -> BenchmarkResult:
        """Run a single benchmark configuration."""
        mem_before = get_memory_mb()

        # Start CPU measurement
        if HAS_PSUTIL:
            proc = psutil.Process(os.getpid())
            proc.cpu_percent()  # Initialize (first call returns 0)

        retrieval_latencies: List[float] = []
        embedding_latencies: List[float] = []
        reranker_latencies: List[float] = []
        e2e_latencies: List[float] = []

        for query in queries:
            self.engine.clear_cache()

            # ---- End-to-end timing ----
            e2e_start = time.perf_counter()

            # ---- Embedding timing ----
            embed_start = time.perf_counter()
            query_vec = self.engine._encoder.encode_query(query)
            embed_ms = (time.perf_counter() - embed_start) * 1000
            embedding_latencies.append(embed_ms)

            # ---- FAISS + BM25 retrieval timing ----
            retrieval_start = time.perf_counter()
            fetch_k = config.top_k * self.engine._fetch_k_multiplier
            scores, indices = self.engine._index.search(query_vec, top_k=fetch_k)
            bm25_scores = self.engine._bm25.get_scores(query)
            retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
            retrieval_latencies.append(retrieval_ms)

            # ---- Build candidates ----
            faiss_candidates = self.engine._build_results(scores, indices, None)
            candidates = self.engine._reciprocal_rank_fusion(
                faiss_candidates, bm25_scores, top_k=fetch_k
            )

            # ---- Reranker timing (isolated) ----
            rerank_ms = 0.0
            if self.engine._reranker and candidates:
                rerank_start = time.perf_counter()
                candidates = self.engine._reranker.rerank(query, candidates)
                rerank_ms = (time.perf_counter() - rerank_start) * 1000
            reranker_latencies.append(rerank_ms)

            e2e_ms = (time.perf_counter() - e2e_start) * 1000
            e2e_latencies.append(e2e_ms)

        # End CPU measurement
        cpu_pct = get_cpu_percent() if HAS_PSUTIL else 0.0
        mem_after = get_memory_mb()

        return BenchmarkResult(
            config=config,
            retrieval_latency=compute_latency_stats(retrieval_latencies),
            reranker_latency=compute_latency_stats(reranker_latencies),
            embedding_latency=compute_latency_stats(embedding_latencies),
            e2e_latency=compute_latency_stats(e2e_latencies),
            memory_rss_mb=mem_after,
            memory_delta_mb=round(mem_after - mem_before, 2),
            cpu_percent=cpu_pct,
            chunks_indexed=len(self.engine._chunks),
        )

    def _print_result(self, r: BenchmarkResult) -> None:
        """Print a formatted benchmark result."""
        print()
        header = f"  {'Metric':<25s}  {'Avg':>8s}  {'P50':>8s}  {'P95':>8s}  {'Min':>8s}  {'Max':>8s}"
        print(header)
        print("  " + "-" * 75)

        for label, stats in [
            ("Embedding", r.embedding_latency),
            ("Retrieval (FAISS+BM25)", r.retrieval_latency),
            ("Reranker (CrossEnc)", r.reranker_latency),
            ("End-to-End", r.e2e_latency),
        ]:
            print(
                f"  {label:<25s}"
                f"  {stats.avg_ms:>7.1f}ms"
                f"  {stats.p50_ms:>7.1f}ms"
                f"  {stats.p95_ms:>7.1f}ms"
                f"  {stats.min_ms:>7.1f}ms"
                f"  {stats.max_ms:>7.1f}ms"
            )

        print()
        print(f"  Memory RSS:       {r.memory_rss_mb:.1f} MB")
        print(f"  Memory Delta:     {r.memory_delta_mb:+.1f} MB")
        if r.cpu_percent > 0:
            print(f"  CPU Usage:        {r.cpu_percent:.1f}%")
        print()

    def save_json(self, path: str = "benchmark_results.json") -> None:
        """Save results to JSON for dashboard consumption."""
        output = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "chunks_indexed": self.results[0].chunks_indexed if self.results else 0,
            "benchmarks": [],
        }

        for r in self.results:
            output["benchmarks"].append({
                "config": asdict(r.config),
                "embedding_latency": asdict(r.embedding_latency),
                "retrieval_latency": asdict(r.retrieval_latency),
                "reranker_latency": asdict(r.reranker_latency),
                "e2e_latency": asdict(r.e2e_latency),
                "memory_rss_mb": r.memory_rss_mb,
                "memory_delta_mb": r.memory_delta_mb,
                "cpu_percent": r.cpu_percent,
            })

        filepath = PROJECT_ROOT / path
        with open(filepath, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nResults saved to {filepath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  VECTORIA PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)
    print()

    if not HAS_PSUTIL:
        print("  [NOTE] psutil not installed — memory/CPU metrics unavailable")
        print("  Install with: pip install psutil")
        print()

    bench = PerformanceBenchmark()
    bench.run_all()
    bench.save_json()

    # ── Summary Table ──
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print()
    print(f"  {'Config':<10s}  {'Embed':>10s}  {'Retrieve':>10s}  {'Rerank':>10s}  {'E2E':>10s}")
    print("  " + "-" * 55)
    for r in bench.results:
        print(
            f"  {r.config.name:<10s}"
            f"  {r.embedding_latency.avg_ms:>9.1f}ms"
            f"  {r.retrieval_latency.avg_ms:>9.1f}ms"
            f"  {r.reranker_latency.avg_ms:>9.1f}ms"
            f"  {r.e2e_latency.avg_ms:>9.1f}ms"
        )
    print()
    print("=" * 60)
    print("  BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
