"""
RAG Pipeline — End-to-end Retrieval-Augmented Generation orchestrator.

This module wires together the retrieval engine, context utilities,
citation validation, prompt builder, and LLM client into a single
``query -> RAGResponse`` pipeline.

Pipeline Flow:
    1. SearchEngine.search(query)             -> List[SearchResult]
    2. has_sufficient_context(results)         -> guardrail gate
    3. build_context(results)                 -> formatted context string
    4. build_citation_map(results)            -> {"[Doc X]": SearchResult}
    5. compute_context_stats(results)         -> observability dict
    6. build_messages(query, context)         -> messages list
    7. LLMClient.generate(messages)           -> raw answer text
    8. normalize_answer(answer)               -> cleaned text
    9. extract_valid_citations(answer, map)   -> validated citations
   10. Assemble RAGResponse with full metadata

Design decisions:
    - The pipeline is stateless between calls.  Each ``run()`` invocation
      is a pure function of its inputs (query + engine state).
    - Guardrails are enforced BEFORE any LLM API call to prevent wasted
      cost and latency on low-confidence retrievals.
    - LLM failures (including safety blocks) produce degraded responses
      (``refused=True``) with structured ``refusal_reason`` codes.
      Failures never silently collapse into generic refusals.
    - Citations are validated post-generation: hallucinated citations
      are stripped, and only verified references appear in the response.
    - The pipeline is provider-agnostic: it consumes ``LLMClient.generate()``
      and ``LLMClient.last_generation_meta`` without any Gemini-specific logic.
"""

from __future__ import annotations

import time
from typing import List, Optional

from vectoria.generation.citation_utils import (
    extract_valid_citations,
    normalize_answer,
)
from vectoria.generation.context_utils import (
    build_citation_map,
    build_context,
    compute_context_stats,
    has_sufficient_context,
)
from vectoria.generation.llm_client import (
    LLMClient,
    LLMError,
    LLMRateLimitError,
    LLMSafetyBlockError,
    LLMTimeoutError,
)
from vectoria.generation.prompt_builder import (
    PROMPT_VERSION,
    REFUSAL_MESSAGE,
    build_messages,
)
from vectoria.generation.response_models import (
    REASON_GENERATION_FAILURE,
    REASON_INSUFFICIENT_CONTEXT,
    REASON_PROVIDER_ERROR,
    REASON_SAFETY_BLOCK,
    REASON_TIMEOUT,
    RAGResponse,
)
from vectoria.logger import get_logger
from vectoria.models import SearchResult
from vectoria.retrieval.engine import SearchEngine

logger = get_logger(__name__)


class RAGPipeline:
    """Production RAG orchestrator built on top of the Vectoria retrieval engine.

    Args:
        engine:               A loaded ``SearchEngine`` instance.
        llm_client:           A configured ``LLMClient`` instance.
        top_k:                Number of results to retrieve per query.
        max_context_chars:    Character budget for context truncation.
        min_score_threshold:  Minimum top-result score to proceed with
                              generation.  Below this, the pipeline refuses.

    Usage::

        engine = SearchEngine()
        engine.load()

        client = LLMClient()
        pipeline = RAGPipeline(engine=engine, llm_client=client)

        response = pipeline.run("How do neural networks learn?")
        print(response.answer)
        print(response.citations)
        print(response.generation_meta)
    """

    def __init__(
        self,
        engine: SearchEngine,
        llm_client: LLMClient,
        top_k: int = 5,
        max_context_chars: int = 4000,
        min_score_threshold: float = 0.3,
    ) -> None:
        self._engine = engine
        self._llm = llm_client
        self._top_k = top_k
        self._max_context_chars = max_context_chars
        self._min_score_threshold = min_score_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str) -> RAGResponse:
        """Execute the full RAG pipeline for a single query.

        Args:
            query: Natural-language question.

        Returns:
            A :class:`RAGResponse` containing the normalized answer,
            validated citations, retrieval context, observability stats,
            generation metadata, and latency.  On failure, ``refused=True``
            with a structured ``refusal_reason``.
        """
        start = time.perf_counter()

        # -- 1. Retrieve -----------------------------------------------
        results = self._engine.search(query, top_k=self._top_k)

        logger.info(
            "RAG retrieval complete | query=%s results=%d",
            repr(query[:50]), len(results),
        )

        # -- 2. Guardrail: sufficient context? -------------------------
        if not has_sufficient_context(results, self._min_score_threshold):
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning(
                "RAG refused | reason=%s query=%s top_score=%.4f "
                "threshold=%.4f prompt_version=%s latency_ms=%d",
                REASON_INSUFFICIENT_CONTEXT,
                repr(query[:50]),
                results[0].score if results else 0.0,
                self._min_score_threshold,
                PROMPT_VERSION,
                latency_ms,
            )
            return RAGResponse(
                answer=REFUSAL_MESSAGE,
                retrieved_results=results,
                context_stats=compute_context_stats(results),
                latency_ms=latency_ms,
                model_name=self._llm.model_name,
                refused=True,
                refusal_reason=REASON_INSUFFICIENT_CONTEXT,
            )

        # -- 3. Build context ------------------------------------------
        context = build_context(results, max_context_chars=self._max_context_chars)
        full_citation_map = build_citation_map(results)
        stats = compute_context_stats(results)
        retrieved_chunk_ids = [r.chunk.chunk_id for r in results]

        # -- 4. Assemble prompt ----------------------------------------
        messages = build_messages(query, context)

        # -- 5. Generate -----------------------------------------------
        try:
            raw_answer = self._llm.generate(messages)
        except LLMError as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            refusal_reason = self._classify_error(e)

            logger.error(
                "RAG generation failed | type=%s reason=%s msg=%s "
                "prompt_version=%s latency_ms=%d",
                type(e).__name__, refusal_reason, str(e),
                PROMPT_VERSION, latency_ms,
            )
            return RAGResponse(
                answer=REFUSAL_MESSAGE,
                citations={},
                retrieved_results=results,
                context_stats=stats,
                latency_ms=latency_ms,
                model_name=self._llm.model_name,
                refused=True,
                refusal_reason=refusal_reason,
            )

        # -- 6. Post-process: normalize + validate citations -----------
        answer = normalize_answer(raw_answer)
        valid_tags, valid_citations = extract_valid_citations(
            answer, full_citation_map
        )

        # -- 7. Assemble generation metadata ---------------------------
        gen_meta = self._llm.last_generation_meta
        generation_meta = gen_meta.to_dict()
        generation_meta["prompt_version"] = PROMPT_VERSION
        generation_meta["retrieved_chunk_ids"] = retrieved_chunk_ids
        generation_meta["citation_count"] = len(valid_tags)

        # -- 8. Assemble final response --------------------------------
        latency_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "RAG complete | query=%s answer_len=%d citations=%d "
            "latency_ms=%d model=%s gen_ms=%d tokens=%d "
            "prompt_version=%s",
            repr(query[:50]),
            len(answer),
            len(valid_tags),
            latency_ms,
            gen_meta.model_used,
            gen_meta.generation_latency_ms,
            gen_meta.total_tokens,
            PROMPT_VERSION,
        )

        return RAGResponse(
            answer=answer,
            citations=valid_citations,
            retrieved_results=results,
            context_stats=stats,
            latency_ms=latency_ms,
            model_name=gen_meta.model_used,
            refused=False,
            refusal_reason=None,
            generation_meta=generation_meta,
        )

    # ------------------------------------------------------------------
    # Internal: error classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_error(error: LLMError) -> str:
        """Map an LLM exception to a deterministic refusal reason code.

        This ensures failures never silently collapse into a generic
        refusal — each failure mode is precisely identified for
        downstream handling, monitoring, and alerting.
        """
        if isinstance(error, LLMTimeoutError):
            return REASON_TIMEOUT
        if isinstance(error, LLMSafetyBlockError):
            return REASON_SAFETY_BLOCK
        if isinstance(error, LLMRateLimitError):
            return REASON_PROVIDER_ERROR
        return REASON_GENERATION_FAILURE
