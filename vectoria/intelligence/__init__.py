"""
Vectoria Intelligence Subsystem.

Decoupled decision, understanding, sufficiency, answerability, and grounding modules.
"""

from .query_understanding import QueryUnderstandingPipeline, QueryMetadata
from .query_budget import QueryBudget, allocate_query_budget
from .query_rewriter import QueryRewriter
from .evidence_sufficiency import EvidenceSufficiencyEngine, SufficiencyResult
from .answerability import AnswerabilityClassifier, AnswerabilityCategory
from .contradiction_detector import ContradictionDetector, ContradictionResult
from .claim_grounding import ClaimGroundingEngine, ClaimGroundingResult
from .calibration import ConfidenceCalibrator
from .decision_engine import DecisionEngine, DecisionAction, DecisionOutcome

__all__ = [
    "QueryUnderstandingPipeline",
    "QueryMetadata",
    "QueryBudget",
    "allocate_query_budget",
    "QueryRewriter",
    "EvidenceSufficiencyEngine",
    "SufficiencyResult",
    "AnswerabilityClassifier",
    "AnswerabilityCategory",
    "ContradictionDetector",
    "ContradictionResult",
    "ClaimGroundingEngine",
    "ClaimGroundingResult",
    "ConfidenceCalibrator",
    "DecisionEngine",
    "DecisionAction",
    "DecisionOutcome",
]
