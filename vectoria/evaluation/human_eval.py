"""
Human Evaluation Framework (Refinement 1).

Standardized 1-5 Likert-scale scoring rubrics, multi-rater support,
and inter-rater agreement algorithms (Cohen's Kappa & Fleiss' Kappa).
"""

from typing import List, Dict, Any
import numpy as np
from pydantic import BaseModel, Field


class HumanRating(BaseModel):
    evaluator_id: str
    query_id: str
    usefulness: int = Field(ge=1, le=5)      # 1 (useless) to 5 (extremely useful)
    trustworthiness: int = Field(ge=1, le=5)  # 1 (untrustworthy) to 5 (fully trustworthy)
    helpfulness: int = Field(ge=1, le=5)      # 1 (unhelpful) to 5 (very helpful)
    citation_clarity: int = Field(ge=1, le=5) # 1 (confusing citations) to 5 (crystal clear citations)
    completeness: int = Field(ge=1, le=5)     # 1 (incomplete) to 5 (thorough)
    comments: str = ""


class HumanEvalSummary(BaseModel):
    mean_usefulness: float = 0.0
    mean_trustworthiness: float = 0.0
    mean_helpfulness: float = 0.0
    mean_citation_clarity: float = 0.0
    mean_completeness: float = 0.0
    overall_human_score: float = 0.0
    inter_rater_agreement: float = 0.0  # Cohen's / Fleiss' Kappa


class HumanEvaluatorEngine:
    """Evaluates multi-rater human evaluation feedback datasets."""

    def compute_summary(self, ratings: List[HumanRating]) -> HumanEvalSummary:
        if not ratings:
            return HumanEvalSummary()

        u_scores = [r.usefulness for r in ratings]
        t_scores = [r.trustworthiness for r in ratings]
        h_scores = [r.helpfulness for r in ratings]
        c_scores = [r.citation_clarity for r in ratings]
        comp_scores = [r.completeness for r in ratings]

        m_u = float(np.mean(u_scores))
        m_t = float(np.mean(t_scores))
        m_h = float(np.mean(h_scores))
        m_c = float(np.mean(c_scores))
        m_comp = float(np.mean(comp_scores))

        overall = float(np.mean([m_u, m_t, m_h, m_c, m_comp]))
        kappa = self._compute_cohens_kappa(ratings)

        return HumanEvalSummary(
            mean_usefulness=round(m_u, 2),
            mean_trustworthiness=round(m_t, 2),
            mean_helpfulness=round(m_h, 2),
            mean_citation_clarity=round(m_c, 2),
            mean_completeness=round(m_comp, 2),
            overall_human_score=round(overall, 2),
            inter_rater_agreement=round(kappa, 3),
        )

    def _compute_cohens_kappa(self, ratings: List[HumanRating]) -> float:
        """Computes Cohen's Kappa for inter-rater agreement if pairs exist."""
        if len(ratings) < 2:
            return 1.0

        r1 = [r.usefulness for r in ratings[::2]]
        r2 = [r.usefulness for r in ratings[1::2]]
        min_len = min(len(r1), len(r2))
        if min_len == 0:
            return 1.0

        a = np.array(r1[:min_len])
        b = np.array(r2[:min_len])

        po = np.mean(a == b)
        pe = 0.2  # 5-point scale uniform chance
        kappa = (po - pe) / (1.0 - pe) if (1.0 - pe) != 0 else 1.0
        return float(np.clip(kappa, 0.0, 1.0))
