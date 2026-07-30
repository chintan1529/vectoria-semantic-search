"""
Unit tests for Vectoria Intelligence Subsystem.
"""

import pytest
from vectoria.models import Chunk, SearchResult
from vectoria.intelligence import (
    QueryUnderstandingPipeline,
    allocate_query_budget,
    QueryRewriter,
    EvidenceSufficiencyEngine,
    AnswerabilityClassifier,
    AnswerabilityCategory,
    ContradictionDetector,
    ClaimGroundingEngine,
    ConfidenceCalibrator,
    DecisionEngine,
    DecisionAction,
)


@pytest.fixture
def sample_results():
    chunk1 = Chunk(chunk_id="chk1", text="Climate change is caused by greenhouse gas emissions.", doc_id="doc1", chunk_index=0, metadata={"title": "Climate Doc"})
    chunk2 = Chunk(chunk_id="chk2", text="Global warming was documented extensively in 2021 and 2023.", doc_id="doc2", chunk_index=1, metadata={"title": "Warming Doc"})
    return [
        SearchResult(chunk=chunk1, score=8.5, rank=1),
        SearchResult(chunk=chunk2, score=7.2, rank=2),
    ]


def test_query_understanding():
    pipeline = QueryUnderstandingPipeline()
    meta = pipeline.analyze("Compare FAISS vs BM25 in 2024?")
    assert meta.is_comparative is True
    assert meta.intent == "comparative"
    assert meta.has_temporal is True


def test_adaptive_query_budget():
    pipeline = QueryUnderstandingPipeline()
    meta = pipeline.analyze("What is RAG?")
    budget = allocate_query_budget(meta)
    assert budget.top_k <= 5


def test_evidence_sufficiency(sample_results):
    pipeline = QueryUnderstandingPipeline()
    meta = pipeline.analyze("What causes climate change?")
    engine = EvidenceSufficiencyEngine()
    sufficiency = engine.evaluate(meta, sample_results)
    assert sufficiency.sufficiency_score > 50.0
    assert sufficiency.confidence_level in ("CONFIDENT", "NOTICE")


def test_decision_engine_confident(sample_results):
    engine = DecisionEngine()
    outcome = engine.evaluate_pipeline("What causes climate change?", sample_results)
    assert outcome.action in (DecisionAction.GENERATE, DecisionAction.GENERATE_WITH_WARNING)
    assert "action" in outcome.reasoning_trace


def test_decision_engine_refusal():
    engine = DecisionEngine()
    outcome = engine.evaluate_pipeline("Who won the 2099 galactic cup?", [])
    assert outcome.action == DecisionAction.REFUSE
    assert outcome.refusal_reason is not None


def test_claim_grounding(sample_results):
    grounding = ClaimGroundingEngine()
    answer = "Climate change is caused by greenhouse gas emissions. Global warming is well documented."
    res = grounding.evaluate(answer, sample_results)
    assert res.total_claims == 2
    assert res.coverage_percentage >= 50.0


def test_confidence_calibration():
    calibrator = ConfidenceCalibrator()
    ece = calibrator.compute_ece([0.9, 0.8, 0.7], [True, True, False])
    assert 0.0 <= ece <= 1.0
