import asyncio
from vectoria.generation.response_models import RAGResponse
from backend.core.startup import state
from backend.core.logging import logger

async def run_rag_pipeline_async(query: str) -> RAGResponse:
    """
    Asynchronous wrapper for the full end-to-end RAG pipeline.
    Runs the entire orchestration (Retrieval -> Guardrails -> Prompt -> LLM -> Validate)
    in a separate thread to preserve FastAPI's event loop concurrency.
    """
    if not state.rag:
        raise RuntimeError("RAGPipeline is not initialized.")
        
    logger.debug(f"Executing async RAG pipeline for query: {query[:30]}...")
    
    # Run the entire pipeline in a threadpool
    response = await asyncio.to_thread(
        state.rag.run,
        query
    )
    
    return response
