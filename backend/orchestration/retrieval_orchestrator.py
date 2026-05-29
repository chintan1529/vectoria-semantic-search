import time
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from vectoria.models import SearchResult
from backend.core.startup import state
from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger
from vectoria.generation.query_classifier import QueryClassifier, QueryType
from vectoria.generation.context_validator import ContextValidator

class RetrievalDiagnostics(BaseModel):
    original_query: str
    rewritten_query: Optional[str] = None
    retrieval_latency_ms: int = 0
    total_results: int = 0
    scores: List[float] = []
    query_type: str = "unknown"
    retrieval_confidence: str = "LOW"
    fallback_used: bool = False

class RetrievalOrchestrator:
    """
    Orchestrates the retrieval phase:
    1. Query Classification (Intent & Routing)
    2. Query Rewriting (optional, for context)
    3. Hybrid Search & Reranking
    4. Context Validation & Fallback
    5. Diagnostic gathering
    """
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider
        if provider:
            self.classifier = QueryClassifier(provider)
            self.validator = ContextValidator(provider)
        else:
            self.classifier = None
            self.validator = None
            
    async def rewrite_query(self, query: str, context: str = "") -> str:
        """Rewrite the query to resolve pronouns if context exists."""
        if not context or not self.provider:
            return query
            
        prompt = f"""Given the conversation context, rewrite the user query to be fully self-contained.
Context:
{context}

User Query: {query}
Rewritten Query:"""

        try:
            result = await self.provider.generate([{"role": "user", "content": prompt}], max_tokens=50)
            rewritten = result.text.strip()
            logger.info("Query rewritten", original=query, rewritten=rewritten)
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
            return query

    async def execute_retrieval(self, query: str, context: str = "", top_k: int = 5) -> tuple[List[SearchResult], RetrievalDiagnostics]:
        start_time = time.perf_counter()
        
        fallback_used = False
        query_type = "unknown"
        retrieval_confidence = "LOW"
        search_query = query
        results = []
        
        # 1. Classify Query
        if self.classifier:
            intent = await self.classifier.classify(query)
            query_type = intent.query_type.value
            logger.info(f"Query classified as {query_type}, requires_retrieval={intent.requires_retrieval}")
            
            if not intent.requires_retrieval:
                # Bypass retrieval for pure conversational queries
                latency = int((time.perf_counter() - start_time) * 1000)
                diagnostics = RetrievalDiagnostics(
                    original_query=query,
                    retrieval_latency_ms=latency,
                    total_results=0,
                    query_type=query_type,
                    retrieval_confidence="HIGH"
                )
                return [], diagnostics
                
            if intent.query_type == QueryType.ANALYTICAL:
                # Increase depth for analytical queries
                top_k = top_k * 2
                
        # 2. Rewrite Query
        search_query = await self.rewrite_query(query, context)
        
        # 3. Retrieve
        if not state.engine:
            raise RuntimeError("SearchEngine is not loaded in application state.")
            
        results = await asyncio.to_thread(state.engine.search, search_query, top_k=top_k)
        
        # 4. Validate Context
        if self.validator:
            validation_result = await self.validator.validate_context(query, results)
            results = validation_result.valid_results
            retrieval_confidence = validation_result.confidence
            
            # 5. Fallback Recovery (if confidence is LOW)
            if retrieval_confidence == "LOW" and self.provider:
                logger.info(f"Low confidence retrieval for '{query}'. Triggering fallback expansion...")
                fallback_used = True
                
                # Simple expansion via LLM
                expand_prompt = f"Expand the following search query with synonyms and related concepts: '{query}'"
                try:
                    expand_res = await self.provider.generate([{"role": "user", "content": expand_prompt}], max_tokens=30)
                    expanded_query = expand_res.text.strip()
                    logger.info(f"Expanded query to: {expanded_query}")
                    
                    if not expanded_query:
                        raise ValueError("LLM returned an empty expanded query.")
                    
                    # Retry search with broader depth
                    fallback_results = await asyncio.to_thread(state.engine.search, expanded_query, top_k=top_k + 5)
                    fallback_val = await self.validator.validate_context(query, fallback_results)
                    
                    # Merge results (prefer fallback if better)
                    if fallback_val.confidence in ["HIGH", "MEDIUM"]:
                        results = fallback_val.valid_results
                        retrieval_confidence = fallback_val.confidence
                        search_query = expanded_query
                    else:
                        # Append the best we got
                        results.extend(fallback_val.valid_results)
                        
                except Exception as e:
                    logger.warning(f"Fallback expansion failed: {e}")

        # Final deduplication just in case fallback merged things
        seen = set()
        final_results = []
        for r in results:
            if r.chunk.chunk_id not in seen:
                seen.add(r.chunk.chunk_id)
                final_results.append(r)
        
        # Sort by score descending and take top_k
        final_results.sort(key=lambda x: x.score, reverse=True)
        final_results = final_results[:top_k]
                
        latency = int((time.perf_counter() - start_time) * 1000)
        
        diagnostics = RetrievalDiagnostics(
            original_query=query,
            rewritten_query=search_query if search_query != query else None,
            retrieval_latency_ms=latency,
            total_results=len(final_results),
            scores=[r.score for r in final_results],
            query_type=query_type,
            retrieval_confidence=retrieval_confidence,
            fallback_used=fallback_used
        )
        
        return final_results, diagnostics
