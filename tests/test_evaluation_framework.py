"""
Unit tests for Vectoria Research Evaluation Framework.
"""

import pytest
from vectoria.evaluation.versioning import get_current_asset_versions
from vectoria.evaluation.cost_tracker import CostTracker
from vectoria.evaluation.human_eval import HumanRating, HumanEvaluatorEngine
from vectoria.evaluation.manifest import ManifestGenerator
from vectoria.evaluation.stat_tests import StatisticalValidator
from vectoria.evaluation.failure_categorizer import FailureCategorizer, FailureSeverity
from scripts.run_baselines import run_baseline_comparison
from scripts.run_ablation_matrix import run_ablation_matrix
from scripts.regression_gate import run_regression_gate


def test_asset_versioning():
    versions = get_current_asset_versions()
    assert versions.dataset_version == "v2.1.0"
    assert versions.benchmark_version == "v3.0.0"


def test_cost_tracker():
    tracker = CostTracker()
    metrics = tracker.compute_cost(prompt_tokens=1000, completion_tokens=500, latency_ms=120)
    assert metrics.total_tokens == 1500
    assert metrics.total_cost_usd > 0.0


def test_human_evaluation():
    engine = HumanEvaluatorEngine()
    ratings = [
        HumanRating(evaluator_id="r1", query_id="q1", usefulness=5, trustworthiness=5, helpfulness=5, citation_clarity=4, completeness=5),
        HumanRating(evaluator_id="r2", query_id="q1", usefulness=4, trustworthiness=5, helpfulness=4, citation_clarity=5, completeness=4),
    ]
    summary = engine.compute_summary(ratings)
    assert summary.overall_human_score >= 4.0
    assert summary.inter_rater_agreement >= 0.0


def test_manifest_generator():
    generator = ManifestGenerator()
    manifest = generator.generate_manifest("test-run-1", {"accuracy": 0.95})
    assert manifest.benchmark_id == "test-run-1"
    assert len(manifest.result_checksum) == 64


def test_statistical_validator():
    validator = StatisticalValidator()
    treatment = [0.95, 0.92, 0.96, 0.94, 0.93]
    baseline = [0.70, 0.72, 0.68, 0.71, 0.69]
    res = validator.compare_against_baseline(treatment, baseline)
    assert res.is_statistically_significant is True
    assert res.cohens_d_effect_size > 1.0


def test_failure_categorizer():
    categorizer = FailureCategorizer()
    res = categorizer.categorize_event("Who won the galactic cup?", "hallucination", {})
    assert res.severity == FailureSeverity.CRITICAL
    assert res.affected_subsystem == "GenerationOrchestrator"


def test_run_baselines():
    summary = run_baseline_comparison(quick_mode=True)
    assert "Vectoria Adaptive Intelligence (Current)" in summary["results_by_system"]


def test_run_ablation_matrix():
    ablations = run_ablation_matrix()
    assert "Full Platform (All Engines Active)" in ablations
    assert len(ablations) >= 5


def test_regression_gate():
    passing_metrics = {
        "hallucination_rate": 0.005,
        "unsupported_claim_rate": 0.02,
        "ece": 0.04,
        "grounding_coverage": 0.95,
        "decision_accuracy": 0.96,
    }
    assert run_regression_gate(passing_metrics) is True

    failing_metrics = dict(passing_metrics, hallucination_rate=0.08)
    assert run_regression_gate(failing_metrics) is False
