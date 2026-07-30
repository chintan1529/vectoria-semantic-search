"""
Central Decision Engine (Refinement 1 & 8).

The single authority module for governing platform actions:
  - GENERATE
  - GENERATE_WITH_WARNING
  - CLARIFY
  - RE_RETRIEVE
  - REFUSE
  - ESCALATE

Consolidates Query Understanding, Evidence Sufficiency, Answerability, and Contradiction inputs.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from vectoria.models import SearchResult
from .query_understanding import QueryUnderstandingPipeline, QueryMetadata
from .query_budget import allocate_query_budget, QueryBudget
from .evidence_sufficiency import EvidenceSufficiencyEngine, SufficiencyResult
from .answerability import AnswerabilityClassifier, AnswerabilityCategory, AnswerabilityResult
from .contradiction_detector import ContradictionDetector, ContradictionResult


class DecisionAction(str, Enum):
    GENERATE = "GENERATE"
    GENERATE_WITH_WARNING = "GENERATE_WITH_WARNING"
    CLARIFY = "CLARIFY"
    RE_RETRIEVE = "RE_RETRIEVE"
    REFUSE = "REFUSE"
    ESCALATE = "ESCALATE"


class DecisionOutcome(BaseModel):
    action: DecisionAction
    query_meta: QueryMetadata
    query_budget: QueryBudget
    sufficiency: SufficiencyResult
    answerability: AnswerabilityResult
    contradictions: ContradictionResult
    reasoning_trace: Dict[str, Any] = Field(default_factory=dict)
    clarification_prompt: Optional[str] = None
    refusal_reason: Optional[str] = None


class DecisionEngine:
    """Central Decision Engine — Single authority for pipeline behavior."""

    def __init__(self):
        self.understanding = QueryUnderstandingPipeline()
        self.sufficiency_engine = EvidenceSufficiencyEngine()
        self.answerability_classifier = AnswerabilityClassifier()
        self.contradiction_detector = ContradictionDetector()

    def evaluate_pipeline(
        self,
        query: str,
        results: List[SearchResult],
        attempt_count: int = 1
    ) -> DecisionOutcome:
        # 1. Query Understanding
        meta = self.understanding.analyze(query)

        # 2. Query Budget Allocation
        budget = allocate_query_budget(meta)

        # 3. Evidence Sufficiency
        sufficiency = self.sufficiency_engine.evaluate(meta, results)

        # 4. Answerability Classification
        answerability = self.answerability_classifier.classify(meta, sufficiency)

        # 5. Contradiction Detection
        contradictions = self.contradiction_detector.detect(results)

        # 6. Central Decision Logic
        action = DecisionAction.GENERATE
        clarification_prompt = None
        refusal_reason = None

        if answerability.category == AnswerabilityCategory.REQUIRES_CLARIFICATION or sufficiency.confidence_level == "CLARIFY":
            action = DecisionAction.CLARIFY
            missing_str = ", ".join(sufficiency.missing_elements[:3]) if sufficiency.missing_elements else "specific details"
            clarification_prompt = f"Could you please specify what aspect of '{query}' you are focusing on regarding {missing_str}?"
        elif sufficiency.confidence_level == "DECLINE" or not answerability.is_safe_to_generate:
            action = DecisionAction.REFUSE
            refusal_reason = f"Unable to answer. {sufficiency.explanation}"
        elif meta.is_multi_hop and sufficiency.sufficiency_score < 75.0 and attempt_count < budget.max_retries and budget.allow_secondary_retrieval:
            action = DecisionAction.RE_RETRIEVE
        elif sufficiency.confidence_level == "NOTICE" or contradictions.has_contradictions:
            action = DecisionAction.GENERATE_WITH_WARNING
        else:
            action = DecisionAction.GENERATE

        # 7. Construct Reasoning Trace
        reasoning_trace = {
            "intent": meta.intent,
            "complexity": meta.complexity_score,
            "sufficiency_score": sufficiency.sufficiency_score,
            "answerability": answerability.category.value,
            "has_contradictions": contradictions.has_contradictions,
            "action": action.value,
            "attempt": attempt_count,
        }

        return DecisionOutcome(
            action=action,
            query_meta=meta,
            query_budget=budget,
            sufficiency=sufficiency,
            answerability=answerability,
            contradictions=contradictions,
            reasoning_trace=reasoning_trace,
            clarification_prompt=clarification_prompt,
            refusal_reason=refusal_reason,
        )
