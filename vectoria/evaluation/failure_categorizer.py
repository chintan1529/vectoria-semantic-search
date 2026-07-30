"""
Advanced Failure Categorizer & Remediation Engine (Phase 6 & Refinement 6).

Categorizes evaluation failures by severity, affected subsystem, root cause,
and generates prioritized recommendations for future releases.
"""

from typing import List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class FailureSeverity(str, Enum):
    CRITICAL = "CRITICAL" # e.g. hallucination or security bypass
    HIGH = "HIGH"         # e.g. incorrect refusal or missed citation
    MEDIUM = "MEDIUM"     # e.g. low grounding coverage
    LOW = "LOW"            # e.g. slight latency breach


class CategorizedFailure(BaseModel):
    query: str
    failure_type: str
    severity: FailureSeverity
    affected_subsystem: str
    root_cause: str
    remediation_recommendation: str


class FailureCategorizer:
    """Classifies system failures into actionable buckets."""

    def categorize_event(self, query: str, failure_type: str, details: Dict[str, Any]) -> CategorizedFailure:
        if failure_type == "hallucination":
            return CategorizedFailure(
                query=query,
                failure_type=failure_type,
                severity=FailureSeverity.CRITICAL,
                affected_subsystem="GenerationOrchestrator",
                root_cause="LLM generated claims ungrounded in context evidence.",
                remediation_recommendation="Increase Evidence Sufficiency threshold or enable stricter Claim Grounding filter."
            )
        elif failure_type in ("retrieval_failure", "empty_retrieval"):
            return CategorizedFailure(
                query=query,
                failure_type=failure_type,
                severity=FailureSeverity.HIGH,
                affected_subsystem="SearchEngine / FAISS",
                root_cause="Corpus does not contain relevant chunks for query topic.",
                remediation_recommendation="Expand document corpus or tune BM25/Dense hybrid fusion weights."
            )
        elif failure_type == "incorrect_refusal":
            return CategorizedFailure(
                query=query,
                failure_type=failure_type,
                severity=FailureSeverity.HIGH,
                affected_subsystem="DecisionEngine",
                root_cause="Decision Engine declined answer despite sufficient chunk context.",
                remediation_recommendation="Recalibrate Evidence Sufficiency score threshold for analytical queries."
            )
        else:
            return CategorizedFailure(
                query=query,
                failure_type=failure_type,
                severity=FailureSeverity.MEDIUM,
                affected_subsystem="RetrievalOrchestrator",
                root_cause="Sub-optimal candidate reranking or context window limit.",
                remediation_recommendation="Increase QueryBudget rerank candidate depth."
            )
