"""
RAG Response Models — Typed data structures for the generation layer.

Design decisions:
    - Plain dataclass, consistent with the existing models.py pattern.
    - ``refused`` flag distinguishes genuine answers from guardrail blocks,
      so downstream consumers never treat a refusal as a real answer.
    - ``refusal_reason`` provides structured, deterministic failure codes
      so downstream systems can programmatically handle different failure
      modes (e.g., retry on timeout, alert on auth errors).
    - ``generation_meta`` carries LLM-level observability (latency, tokens,
      model, finish reason, prompt version) separately from pipeline metrics.
    - ``to_dict()`` enables JSON serialization for API responses and logging
      without introducing Pydantic or other heavy frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from vectoria.models import SearchResult


# ─────────────────────────────────────────────────────────────────────
# Refusal Reason Constants
# ─────────────────────────────────────────────────────────────────────

# Deterministic refusal codes.  These are the ONLY valid values for
# RAGResponse.refusal_reason.  Adding new reasons requires updating
# this section and the pipeline logic that sets them.
REASON_INSUFFICIENT_CONTEXT = "insufficient_context"
REASON_SAFETY_BLOCK = "safety_block"
REASON_GENERATION_FAILURE = "generation_failure"
REASON_TIMEOUT = "timeout"
REASON_PROVIDER_ERROR = "provider_error"


@dataclass
class RAGResponse:
    """Complete output of the RAG pipeline.

    Attributes:
        answer:             Generated text from the LLM, or a static refusal message.
        citations:          Validated mapping from "[Doc X]" tags to the
                            SearchResult objects actually referenced in the answer.
                            Only contains citations that (a) appear in the generated
                            text AND (b) exist in the original citation map.
        retrieved_results:  Full list of SearchResult objects from the retrieval
                            stage, preserved for debugging and evaluation.
        context_stats:      Observability metrics from ``compute_context_stats``:
                            num_chunks, total_characters, average_score,
                            unique_sources.
        latency_ms:         End-to-end pipeline execution time in milliseconds.
        model_name:         LLM model identifier that actually produced the answer.
                            Tracks which model (including fallbacks) responded,
                            for reproducibility and audit.
        refused:            True if guardrails blocked generation (insufficient
                            context or LLM failure).  Prevents downstream systems
                            from treating refusals as real answers.
        refusal_reason:     Structured failure code when ``refused=True``.
                            One of: insufficient_context, safety_block,
                            generation_failure, timeout, provider_error.
                            ``None`` when generation succeeded.
        generation_meta:    LLM-level observability: generation latency, token
                            usage, finish reason, prompt version, chunk IDs,
                            and citation count.  Empty dict when generation
                            was not attempted (pre-generation refusal).
    """

    answer: str
    citations: Dict[str, SearchResult] = field(default_factory=dict)
    retrieved_results: List[SearchResult] = field(default_factory=list)
    context_stats: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    model_name: str = ""
    refused: bool = False
    refusal_reason: Optional[str] = None
    generation_meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "answer": self.answer,
            "citations": {
                tag: result.to_dict() for tag, result in self.citations.items()
            },
            "context_stats": self.context_stats,
            "latency_ms": self.latency_ms,
            "model_name": self.model_name,
            "refused": self.refused,
            "refusal_reason": self.refusal_reason,
            "generation_meta": self.generation_meta,
            "num_retrieved": len(self.retrieved_results),
        }
