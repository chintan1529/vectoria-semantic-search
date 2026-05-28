import asyncio
from typing import List, Optional
from vectoria.models import SearchResult
from backend.core.startup import state
from backend.core.logging import logger

async def search_async(query: str, top_k: int, min_score: Optional[float] = None) -> List[SearchResult]:
    """
    Asynchronous wrapper for the CPU-bound FAISS search and cross-encoder reranking.
    Offloads to a threadpool to prevent blocking the asyncio event loop.
    """
    if not state.engine:
        raise RuntimeError("SearchEngine is not initialized.")
        
    logger.debug(f"Executing async search for query: {query[:30]}...")
    
    # Run the synchronous CPU-heavy engine.search() in a separate thread
    results = await asyncio.to_thread(
        state.engine.search,
        query,
        top_k=top_k,
        min_score=min_score
    )
    
    return results
