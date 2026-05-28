import time
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from vectoria.models import SearchResult
from backend.core.startup import state
from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger

class RetrievalDiagnostics(BaseModel):
    original_query: str
    rewritten_query: Optional[str] = None
    retrieval_latency_ms: int = 0
    total_results: int = 0
    scores: List[float] = []

class RetrievalOrchestrator:
    """
    Orchestrates the retrieval phase:
    1. Query Rewriting (optional, for context)
    2. Hybrid Search & Reranking (via engine)
    3. Diagnostic gathering
    """
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider
        
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
        
        # 1. Rewrite Query
        search_query = await self.rewrite_query(query, context)
        
        # 2. Execute Search via Vectoria Engine (synchronous wrapped in thread)
        if not state.engine:
            raise RuntimeError("SearchEngine is not loaded in application state.")
            
        results = await asyncio.to_thread(state.engine.search, search_query, top_k)
        
        latency = int((time.perf_counter() - start_time) * 1000)
        
        # 3. Compile Diagnostics
        diagnostics = RetrievalDiagnostics(
            original_query=query,
            rewritten_query=search_query if search_query != query else None,
            retrieval_latency_ms=latency,
            total_results=len(results),
            scores=[r.score for r in results]
        )
        
        return results, diagnostics
