"""
Answerability Classifier Engine (Phase 2).

Classifies query answerability status prior to generation:
  - FULLY_ANSWERABLE
  - PARTIALLY_ANSWERABLE
  - REQUIRES_CLARIFICATION
  - OUTSIDE_INDEXED_KNOWLEDGE
  - REQUIRES_EXTERNAL_KNOWLEDGE
  - UNSAFE_TO_INFER
"""

from enum import Enum
from pydantic import BaseModel
from .query_understanding import QueryMetadata
from .evidence_sufficiency import SufficiencyResult


class AnswerabilityCategory(str, Enum):
    FULLY_ANSWERABLE = "FULLY_ANSWERABLE"
    PARTIALLY_ANSWERABLE = "PARTIALLY_ANSWERABLE"
    REQUIRES_CLARIFICATION = "REQUIRES_CLARIFICATION"
    OUTSIDE_INDEXED_KNOWLEDGE = "OUTSIDE_INDEXED_KNOWLEDGE"
    REQUIRES_EXTERNAL_KNOWLEDGE = "REQUIRES_EXTERNAL_KNOWLEDGE"
    UNSAFE_TO_INFER = "UNSAFE_TO_INFER"


class AnswerabilityResult(BaseModel):
    category: AnswerabilityCategory
    is_safe_to_generate: bool
    explanation: str


class AnswerabilityClassifier:
    """Classifies answerability state based on query metadata and evidence sufficiency."""

    def classify(self, meta: QueryMetadata, sufficiency: SufficiencyResult) -> AnswerabilityResult:
        if sufficiency.sufficiency_score >= 90.0:
            return AnswerabilityResult(
                category=AnswerabilityCategory.FULLY_ANSWERABLE,
                is_safe_to_generate=True,
                explanation="Complete evidence available."
            )
        elif sufficiency.sufficiency_score >= 70.0:
            return AnswerabilityResult(
                category=AnswerabilityCategory.PARTIALLY_ANSWERABLE,
                is_safe_to_generate=True,
                explanation="Partial evidence available; assumptions required."
            )
        elif sufficiency.confidence_level == "CLARIFY" or meta.complexity_score > 0.8:
            return AnswerabilityResult(
                category=AnswerabilityCategory.REQUIRES_CLARIFICATION,
                is_safe_to_generate=False,
                explanation="Ambiguous or highly complex query requires clarification."
            )
        elif sufficiency.sufficiency_score < 20.0:
            return AnswerabilityResult(
                category=AnswerabilityCategory.OUTSIDE_INDEXED_KNOWLEDGE,
                is_safe_to_generate=False,
                explanation="Topic is outside the indexed corpus knowledge."
            )
        else:
            return AnswerabilityResult(
                category=AnswerabilityCategory.UNSAFE_TO_INFER,
                is_safe_to_generate=False,
                explanation="Insufficient evidence to safely infer a factual answer."
            )
