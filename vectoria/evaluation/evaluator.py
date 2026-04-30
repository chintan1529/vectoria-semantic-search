"""
Retrieval Evaluator -- Comprehensive evaluation framework for Vectoria.

Computes Recall@K, Precision@K, MRR, Hit@K per query and aggregated,
with domain-level breakdown, failure case analysis, and optional
BM25 baseline comparison.

Relevance grading (from ground_truth):
    - **Highly relevant**: chunk is from a highly_relevant_titles article.
    - **Relevant**: chunk's domain matches AND text contains >=2 keywords.
    - **Weakly relevant**: chunk's domain matches the expected domain.
    - **Irrelevant**: wrong domain AND no keyword match.

For binary metrics, "relevant" = highly_relevant OR relevant (>= 2 keywords).
Weakly relevant (domain-only match) is NOT counted as relevant for metrics.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from vectoria.evaluation.ground_truth import EvalQuery
from vectoria.logger import get_logger
from vectoria.models import SearchResult
from vectoria.retrieval.engine import SearchEngine
from vectoria.storage import analyze_score_distribution

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Result data structures
# ------------------------------------------------------------------


@dataclass
class QueryResult:
    """Evaluation result for a single query."""

    query: str
    domain: str
    retrieved_titles: List[str]
    retrieved_domains: List[str]
    scores: List[float]
    relevance_labels: List[str]  # "highly_relevant", "relevant", "weak", "irrelevant"
    first_relevant_rank: int  # 0 if no relevant result found
    metrics: Dict[str, Dict[int, float]] = field(default_factory=dict)
    # metrics["recall"][5] = Recall@5, etc.


@dataclass
class EvalReport:
    """Aggregated evaluation report."""

    per_query: List[QueryResult]
    aggregate: Dict[str, Dict[int, float]]  # metric -> {k: value}
    domain_metrics: Dict[str, Dict[str, Dict[int, float]]]  # domain -> metric -> {k: value}
    failures: List[QueryResult]
    k_values: List[int]
    total_queries: int
    total_time_ms: int


# ------------------------------------------------------------------
# Relevance grading
# ------------------------------------------------------------------


def grade_relevance(
    result: SearchResult,
    eval_query: EvalQuery,
) -> str:
    """Grade a single search result against the ground truth query.

    Returns one of: "highly_relevant", "relevant", "weak", "irrelevant".
    """
    title = result.chunk.metadata.title
    domain = result.chunk.metadata.category
    text_lower = result.chunk.text.lower()

    # Check highly relevant titles
    if title in eval_query.highly_relevant_titles:
        return "highly_relevant"

    # Count keyword matches in chunk text
    keyword_hits = sum(
        1 for kw in eval_query.keywords
        if kw.lower() in text_lower
    )

    # Domain match + keyword threshold
    domain_match = domain == eval_query.domain

    if domain_match and keyword_hits >= 2:
        return "relevant"
    elif domain_match:
        return "weak"
    else:
        return "irrelevant"


def is_relevant(label: str) -> bool:
    """Binary relevance: highly_relevant or relevant counts as True."""
    return label in ("highly_relevant", "relevant")


# ------------------------------------------------------------------
# Core evaluator
# ------------------------------------------------------------------


class RetrievalEvaluator:
    """Comprehensive retrieval evaluation framework."""

    def __init__(self, k_values: List[int] = None):
        self.k_values = k_values or [1, 3, 5, 10]

    def evaluate(
        self,
        engine: SearchEngine,
        queries: List[EvalQuery],
        max_k: int = None,
    ) -> EvalReport:
        """Run full evaluation across all queries.

        Args:
            engine:  Loaded SearchEngine instance.
            queries: List of EvalQuery with ground truth.
            max_k:   Maximum K for retrieval (defaults to max(k_values)).

        Returns:
            Complete EvalReport with per-query and aggregate metrics.
        """
        start = time.perf_counter()
        max_k = max_k or max(self.k_values)

        logger.info(
            "Starting evaluation | queries=%d k_values=%s max_k=%d",
            len(queries), self.k_values, max_k,
        )

        per_query: List[QueryResult] = []

        for i, eq in enumerate(queries, 1):
            qr = self._evaluate_single(engine, eq, max_k)
            per_query.append(qr)

            if i % 10 == 0:
                logger.info("Evaluated %d/%d queries...", i, len(queries))

        # Aggregate
        aggregate = self._aggregate_metrics(per_query)
        domain_metrics = self._domain_breakdown(per_query)
        failures = self._identify_failures(per_query, k=self.k_values[-1])

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "Evaluation complete | queries=%d failures=%d time_ms=%d",
            len(per_query), len(failures), elapsed_ms,
        )

        return EvalReport(
            per_query=per_query,
            aggregate=aggregate,
            domain_metrics=domain_metrics,
            failures=failures,
            k_values=self.k_values,
            total_queries=len(queries),
            total_time_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Single query evaluation
    # ------------------------------------------------------------------

    def _evaluate_single(
        self,
        engine: SearchEngine,
        eq: EvalQuery,
        max_k: int,
    ) -> QueryResult:
        """Evaluate a single query."""
        results = engine.search(eq.query, top_k=max_k)

        titles = [r.chunk.metadata.title for r in results]
        domains = [r.chunk.metadata.category for r in results]
        scores = [r.score for r in results]
        labels = [grade_relevance(r, eq) for r in results]

        # First relevant rank (1-indexed, 0 if none)
        first_rel = 0
        for i, label in enumerate(labels):
            if is_relevant(label):
                first_rel = i + 1
                break

        # Compute metrics at each K
        metrics: Dict[str, Dict[int, float]] = {
            "recall": {},
            "precision": {},
            "mrr": {},
            "hit": {},
        }

        # Count total relevant in full result set
        total_relevant = sum(1 for l in labels if is_relevant(l))

        for k in self.k_values:
            top_k_labels = labels[:k]
            relevant_at_k = sum(1 for l in top_k_labels if is_relevant(l))

            # Recall@K
            if total_relevant > 0:
                metrics["recall"][k] = relevant_at_k / total_relevant
            else:
                metrics["recall"][k] = 0.0

            # Precision@K
            metrics["precision"][k] = relevant_at_k / k if k > 0 else 0.0

            # Hit@K
            metrics["hit"][k] = 1.0 if relevant_at_k > 0 else 0.0

            # MRR (reciprocal rank of first relevant in top-K)
            mrr = 0.0
            for j, l in enumerate(top_k_labels):
                if is_relevant(l):
                    mrr = 1.0 / (j + 1)
                    break
            metrics["mrr"][k] = mrr

        return QueryResult(
            query=eq.query,
            domain=eq.domain,
            retrieved_titles=titles,
            retrieved_domains=domains,
            scores=scores,
            relevance_labels=labels,
            first_relevant_rank=first_rel,
            metrics=metrics,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate_metrics(
        self, results: List[QueryResult]
    ) -> Dict[str, Dict[int, float]]:
        """Compute mean metrics across all queries."""
        aggregate: Dict[str, Dict[int, float]] = {}

        for metric_name in ("recall", "precision", "mrr", "hit"):
            aggregate[metric_name] = {}
            for k in self.k_values:
                values = [qr.metrics[metric_name][k] for qr in results]
                aggregate[metric_name][k] = float(np.mean(values))

        return aggregate

    def _domain_breakdown(
        self, results: List[QueryResult]
    ) -> Dict[str, Dict[str, Dict[int, float]]]:
        """Compute per-domain metrics."""
        by_domain: Dict[str, List[QueryResult]] = defaultdict(list)
        for qr in results:
            by_domain[qr.domain].append(qr)

        domain_metrics = {}
        for domain, domain_results in sorted(by_domain.items()):
            domain_metrics[domain] = self._aggregate_metrics(domain_results)

        return domain_metrics

    # ------------------------------------------------------------------
    # Failure analysis
    # ------------------------------------------------------------------

    def _identify_failures(
        self, results: List[QueryResult], k: int = 5
    ) -> List[QueryResult]:
        """Identify queries where no relevant result appears in top-K."""
        failures = []
        for qr in results:
            if qr.metrics["hit"][k] == 0.0:
                failures.append(qr)
            elif qr.first_relevant_rank > 3:
                # Late relevant result (rank > 3) is also a soft failure
                failures.append(qr)
        return failures


# ------------------------------------------------------------------
# Report formatting
# ------------------------------------------------------------------


def format_report(report: EvalReport) -> str:
    """Format an EvalReport as a human-readable string."""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append("  VECTORIA RETRIEVAL EVALUATION REPORT")
    lines.append("=" * 60)
    lines.append(f"  Queries: {report.total_queries}")
    lines.append(f"  K values: {report.k_values}")
    lines.append(f"  Time: {report.total_time_ms} ms")
    lines.append("")

    # Aggregate metrics table
    lines.append("-" * 60)
    lines.append("  AGGREGATE METRICS")
    lines.append("-" * 60)
    header = "  {:15s}".format("Metric")
    for k in report.k_values:
        header += f"  @{k:<6d}"
    lines.append(header)
    lines.append("  " + "-" * (15 + 8 * len(report.k_values)))

    for metric_name in ("precision", "recall", "mrr", "hit"):
        row = f"  {metric_name.upper():<15s}"
        for k in report.k_values:
            val = report.aggregate[metric_name][k]
            row += f"  {val:<6.4f}"
        lines.append(row)
    lines.append("")

    # Domain breakdown
    lines.append("-" * 60)
    lines.append("  DOMAIN BREAKDOWN")
    lines.append("-" * 60)
    for domain, metrics in sorted(report.domain_metrics.items()):
        lines.append(f"\n  [{domain.upper()}]")
        for metric_name in ("precision", "recall", "mrr", "hit"):
            row = f"    {metric_name.upper():<13s}"
            for k in report.k_values:
                val = metrics[metric_name][k]
                row += f"  {val:<6.4f}"
            lines.append(row)
    lines.append("")

    # Per-query summary
    lines.append("-" * 60)
    lines.append("  PER-QUERY RESULTS (K=5)")
    lines.append("-" * 60)
    for qr in report.per_query:
        k5_prec = qr.metrics["precision"].get(5, 0.0)
        k5_rec = qr.metrics["recall"].get(5, 0.0)
        k5_mrr = qr.metrics["mrr"].get(5, 0.0)
        status = "OK" if qr.first_relevant_rank > 0 and qr.first_relevant_rank <= 3 else (
            "LATE" if qr.first_relevant_rank > 3 else "MISS"
        )
        lines.append(
            f"  [{status:4s}] P={k5_prec:.2f} R={k5_rec:.2f} MRR={k5_mrr:.2f} "
            f"1st@{qr.first_relevant_rank} | {qr.query[:50]}"
        )
    lines.append("")

    # Score distribution
    lines.append("-" * 60)
    lines.append("  SCORE DISTRIBUTION")
    lines.append("-" * 60)
    all_scores = []
    relevant_scores = []
    irrelevant_scores = []
    for qr in report.per_query:
        for score, label in zip(qr.scores, qr.relevance_labels):
            all_scores.append(score)
            if is_relevant(label):
                relevant_scores.append(score)
            else:
                irrelevant_scores.append(score)

    if all_scores:
        lines.append(f"  All scores:       min={min(all_scores):.4f} "
                      f"max={max(all_scores):.4f} "
                      f"mean={np.mean(all_scores):.4f} "
                      f"std={np.std(all_scores):.4f}")
    if relevant_scores:
        lines.append(f"  Relevant scores:  min={min(relevant_scores):.4f} "
                      f"max={max(relevant_scores):.4f} "
                      f"mean={np.mean(relevant_scores):.4f} "
                      f"std={np.std(relevant_scores):.4f}")
    if irrelevant_scores:
        lines.append(f"  Irrelevant scores: min={min(irrelevant_scores):.4f} "
                      f"max={max(irrelevant_scores):.4f} "
                      f"mean={np.mean(irrelevant_scores):.4f} "
                      f"std={np.std(irrelevant_scores):.4f}")
    lines.append("")

    # Failure cases
    lines.append("-" * 60)
    lines.append(f"  FAILURE ANALYSIS ({len(report.failures)} issues)")
    lines.append("-" * 60)
    if not report.failures:
        lines.append("  No failures detected!")
    else:
        for qr in report.failures:
            lines.append(f"\n  QUERY: \"{qr.query}\"")
            lines.append(f"  Expected domain: {qr.domain}")
            lines.append(f"  1st relevant rank: {qr.first_relevant_rank} "
                          f"({'MISS' if qr.first_relevant_rank == 0 else 'LATE'})")
            for i, (title, label, score) in enumerate(
                zip(qr.retrieved_titles[:5], qr.relevance_labels[:5], qr.scores[:5])
            ):
                lines.append(f"    #{i+1} [{score:+.4f}] [{label:16s}] {title}")
    lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


# ------------------------------------------------------------------
# BM25 Baseline (lightweight)
# ------------------------------------------------------------------


class BM25Baseline:
    """Simple TF-IDF/BM25-like baseline for comparison.

    Uses term frequency with inverse document frequency weighting
    for keyword-based retrieval. No external dependencies.
    """

    def __init__(self, chunks: list):
        self.chunks = chunks
        self._doc_freqs: Dict[str, int] = {}
        self._tf_cache: List[Dict[str, int]] = []
        self._build_index()

    def _build_index(self) -> None:
        """Build TF and DF tables."""
        n = len(self.chunks)
        for chunk in self.chunks:
            words = chunk.text.lower().split()
            tf: Dict[str, int] = {}
            seen: set = set()
            for w in words:
                w_clean = w.strip(".,;:!?()[]\"'")
                if len(w_clean) < 2:
                    continue
                tf[w_clean] = tf.get(w_clean, 0) + 1
                if w_clean not in seen:
                    self._doc_freqs[w_clean] = self._doc_freqs.get(w_clean, 0) + 1
                    seen.add(w_clean)
            self._tf_cache.append(tf)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search using BM25-like scoring.

        Returns list of (chunk_index, score) sorted by score descending.
        """
        import math
        query_terms = [t.strip(".,;:!?()[]\"'").lower() for t in query.split()]
        query_terms = [t for t in query_terms if len(t) >= 2]

        n = len(self.chunks)
        avg_dl = sum(c.word_count for c in self.chunks) / max(n, 1)
        k1 = 1.5
        b = 0.75

        scores = []
        for idx, tf in enumerate(self._tf_cache):
            score = 0.0
            dl = self.chunks[idx].word_count
            for term in query_terms:
                if term not in tf:
                    continue
                freq = tf[term]
                df = self._doc_freqs.get(term, 0)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * dl / avg_dl))
                score += idf * tf_norm
            scores.append((idx, score))

        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def evaluate(
        self,
        queries: List[EvalQuery],
        k_values: List[int] = None,
    ) -> Dict[str, Dict[int, float]]:
        """Evaluate BM25 baseline on the same queries."""
        k_values = k_values or [1, 3, 5, 10]
        max_k = max(k_values)

        metrics: Dict[str, List[Dict[int, float]]] = {
            "precision": [], "recall": [], "mrr": [], "hit": [],
        }

        for eq in queries:
            bm25_results = self.search(eq.query, top_k=max_k)

            # Grade relevance
            labels = []
            for idx, score in bm25_results:
                chunk = self.chunks[idx]
                title = chunk.metadata.title
                domain = chunk.metadata.category
                text_lower = chunk.text.lower()

                if title in eq.highly_relevant_titles:
                    labels.append("highly_relevant")
                elif domain == eq.domain and sum(
                    1 for kw in eq.keywords if kw.lower() in text_lower
                ) >= 2:
                    labels.append("relevant")
                else:
                    labels.append("irrelevant")

            total_rel = sum(1 for l in labels if is_relevant(l))
            q_metrics: Dict[str, Dict[int, float]] = {
                "precision": {}, "recall": {}, "mrr": {}, "hit": {},
            }

            for k in k_values:
                top_k_labels = labels[:k]
                rel_at_k = sum(1 for l in top_k_labels if is_relevant(l))

                q_metrics["recall"][k] = rel_at_k / total_rel if total_rel > 0 else 0.0
                q_metrics["precision"][k] = rel_at_k / k
                q_metrics["hit"][k] = 1.0 if rel_at_k > 0 else 0.0

                mrr = 0.0
                for j, l in enumerate(top_k_labels):
                    if is_relevant(l):
                        mrr = 1.0 / (j + 1)
                        break
                q_metrics["mrr"][k] = mrr

            for m in metrics:
                metrics[m].append(q_metrics[m])

        # Aggregate
        aggregate = {}
        for metric_name in ("precision", "recall", "mrr", "hit"):
            aggregate[metric_name] = {}
            for k in k_values:
                vals = [qm[k] for qm in metrics[metric_name]]
                aggregate[metric_name][k] = float(np.mean(vals))

        return aggregate
