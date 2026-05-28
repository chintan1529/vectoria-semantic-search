import asyncio
from typing import Dict, List
from backend.core.startup import state
from backend.core.logging import logger

async def generate_async(messages: List[Dict[str, str]]) -> str:
    """
    Asynchronous wrapper for the synchronous Gemini HTTP client.
    Offloads the blocking I/O request to a threadpool.
    """
    if not state.llm:
        raise RuntimeError("LLMClient is not initialized.")
        
    logger.debug("Executing async LLM generation...")
    
    # Run the synchronous HTTP generation in a separate thread
    response_text = await asyncio.to_thread(
        state.llm.generate,
        messages
    )
    
    return response_text
