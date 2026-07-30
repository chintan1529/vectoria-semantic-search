"""
Retrieval Orchestrator v2 — Optimized for sub-second retrieval.

Changes from v1:
  - Replaced LLM QueryClassifier with HybridIntentRouter (< 1ms)
  - Replaced LLM ContextValidator with HeuristicContextValidator (< 5ms)
  - Removed query rewriting from single-turn critical path
  - LLM escalation only when local confidence < 90% (rare)
  - Added orchestrator-level result cache

Performance targets:
  - Query routing: < 50ms
  - Retrieval + reranking: < 500ms
  - Total orchestration: < 1s
"""
import time
import asyncio
import hashlib
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from vectoria.models import SearchResult
from backend.core.startup import state
from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger
from vectoria.generation.intent_router import HybridIntentRouter, QueryType, QueryIntent
from vectoria.generation.heuristic_validator import HeuristicContextValidator
from vectoria.intelligence.query_understanding import QueryUnderstandingPipeline
from vectoria.intelligence.query_budget import allocate_query_budget
from vectoria.intelligence.query_rewriter import QueryRewriter


class RetrievalDiagnostics(BaseModel):
    original_query: str
    rewritten_query: Optional[str] = None
    retrieval_latency_ms: int = 0
    classification_latency_ms: int = 0
    reranking_latency_ms: int = 0
    validation_latency_ms: int = 0
    total_results: int = 0
    scores: List[float] = []
    query_type: str = "unknown"
    retrieval_confidence: str = "LOW"
    fallback_used: bool = False
    cached: bool = False
    routed_locally: bool = True
    rejected_candidates: List[dict] = []


class RetrievalOrchestrator:
    """Orchestrates retrieval with zero LLM calls in the critical path.
    
    Pipeline:
      1. Local Intent Classification (< 1ms)
      2. Hybrid Search + Reranking (via SearchEngine)
      3. Heuristic Context Validation (< 5ms)
      4. LLM escalation only if classification confidence < 90% (async, non-blocking)
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider
        self.router = HybridIntentRouter(escalation_threshold=0.90)
        self.validator = HeuristicContextValidator()
        self.understanding = QueryUnderstandingPipeline()
        self.rewriter = QueryRewriter()
        
        # Orchestrator-level result cache: query_hash -> (results, diagnostics)
        self._cache: Dict[str, Tuple[List[SearchResult], RetrievalDiagnostics]] = {}
        self._max_cache_size = 64

    def _query_hash(self, query: str, top_k: int) -> str:
        """Deterministic hash for cache key."""
        return hashlib.md5(f"{query.strip().lower()}:{top_k}".encode()).hexdigest()

    async def execute_retrieval(
        self, query: str, context: str = "", top_k: int = 5
    ) -> Tuple[List[SearchResult], RetrievalDiagnostics]:
        """Execute the optimized retrieval pipeline.
        
        Critical path (no LLM calls):
          1. Check cache → instant return if hit
          2. Local intent classification (< 1ms)
          3. SearchEngine.search() with reranking (target < 500ms)
          4. Heuristic validation (< 5ms)
        """
        pipeline_start = time.perf_counter()

        # --- 0. Check orchestrator cache ---
        cache_key = self._query_hash(query, top_k)
        if cache_key in self._cache:
            cached_results, cached_diag = self._cache[cache_key]
            cached_diag_copy = cached_diag.model_copy()
            cached_diag_copy.cached = True
            logger.info("Orchestrator cache hit | query=%s", repr(query[:50]))
            return cached_results, cached_diag_copy

        # --- 1. Local Intent Classification ---
        classify_start = time.perf_counter()
        intent = self.router.classify(query)
        classify_ms = int((time.perf_counter() - classify_start) * 1000)

        logger.info(
            "Query classified | type=%s confidence=%.2f requires_retrieval=%s "
            "routed_locally=%s reason='%s' latency_ms=%d",
            intent.query_type.value, intent.confidence,
            intent.requires_retrieval, intent.routed_locally,
            intent.explanation, classify_ms,
        )

        # Short-circuit for conversational queries
        if not intent.requires_retrieval:
            total_ms = int((time.perf_counter() - pipeline_start) * 1000)
            diagnostics = RetrievalDiagnostics(
                original_query=query,
                retrieval_latency_ms=total_ms,
                classification_latency_ms=classify_ms,
                total_results=0,
                query_type=intent.query_type.value,
                retrieval_confidence="HIGH",
                routed_locally=intent.routed_locally,
            )
            return [], diagnostics

        # Analyze query and allocate adaptive budget
        meta = self.understanding.analyze(query)
        budget = allocate_query_budget(meta)
        effective_top_k = budget.top_k

        # Rewrite query if necessary
        rewritten_queries = self.rewriter.rewrite(meta)
        search_query = rewritten_queries[0]

        # --- 2. Retrieve (includes embedding, FAISS, BM25, reranking) ---
        if not state.engine:
            raise RuntimeError("SearchEngine is not loaded in application state.")

        retrieve_start = time.perf_counter()
        results = await asyncio.to_thread(
            state.engine.search, search_query, top_k=effective_top_k
        )
        retrieve_ms = int((time.perf_counter() - retrieve_start) * 1000)

        # --- 3. Heuristic Validation ---
        validate_start = time.perf_counter()
        validation = self.validator.validate_context(query, results)
        validate_ms = int((time.perf_counter() - validate_start) * 1000)

        final_results = validation.valid_results
        retrieval_confidence = validation.confidence

        # --- 4. Final results ---
        # Sort by score descending, take top_k
        final_results.sort(key=lambda x: x.score, reverse=True)
        final_results = final_results[:top_k]

        total_ms = int((time.perf_counter() - pipeline_start) * 1000)

        diagnostics = RetrievalDiagnostics(
            original_query=query,
            retrieval_latency_ms=retrieve_ms,
            classification_latency_ms=classify_ms,
            reranking_latency_ms=0,  # Included in retrieval_latency_ms (engine handles it)
            validation_latency_ms=validate_ms,
            total_results=len(final_results),
            scores=[r.score for r in final_results],
            query_type=intent.query_type.value,
            retrieval_confidence=retrieval_confidence,
            routed_locally=intent.routed_locally,
            rejected_candidates=validation.rejected_results,
        )

        logger.info(
            "Retrieval complete | query=%s results=%d confidence=%s "
            "classify_ms=%d retrieve_ms=%d validate_ms=%d total_ms=%d",
            repr(query[:50]), len(final_results), retrieval_confidence,
            classify_ms, retrieve_ms, validate_ms, total_ms,
        )

        # Cache the result
        self._cache_put(cache_key, final_results, diagnostics)

        return final_results, diagnostics

    def _cache_put(
        self,
        key: str,
        results: List[SearchResult],
        diagnostics: RetrievalDiagnostics,
    ) -> None:
        """Insert into orchestrator cache, evicting oldest if full."""
        if len(self._cache) >= self._max_cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = (results, diagnostics)
