import json
from typing import AsyncGenerator, List
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.orchestration.retrieval_orchestrator import RetrievalDiagnostics
from .generation_orchestrator import GenerationOrchestrator

class StreamingOrchestrator:
    """
    Coordinates SSE streaming of context, diagnostics, and LLM tokens.
    """
    def __init__(self, provider: BaseLLMProvider):
        self.generation = GenerationOrchestrator(provider)

    async def stream_response(self, query: str, results: List[SearchResult], diagnostics: RetrievalDiagnostics, **kwargs) -> AsyncGenerator[str, None]:
        """
        Yields Server-Sent Events.
        First yields the 'context' and 'diagnostics' events, then streams 'token' events,
        and finally yields a 'done' event.
        """
        # Yield retrieval context
        context_data = [
            {
                "id": r.chunk.chunk_id,
                "title": r.chunk.metadata.title,
                "score": r.score,
                "text": r.chunk.text
            }
            for r in results
        ]
        
        yield {"event": "context", "data": json.dumps(context_data)}
        
        # Yield diagnostics
        yield {"event": "diagnostics", "data": diagnostics.model_dump_json()}
        
        # Stream LLM tokens
        messages = self.generation.build_prompt(query, results, diagnostics)
        
        try:
            async for token in self.generation.provider.stream(messages, **kwargs):
                # Send standard JSON string for the token to preserve whitespace
                clean_token = json.dumps(token)
                yield {"event": "token", "data": clean_token}
                
            yield {"event": "done", "data": "{}"}
        except Exception as e:
            from backend.core.logging import logger
            logger.error(f"Streaming generation failed: {e}")
            yield {"event": "error", "data": json.dumps(str(e))}
