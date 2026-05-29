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
        
        yield f"event: context\ndata: {json.dumps(context_data)}\n\n"
        
        # Yield diagnostics
        yield f"event: diagnostics\ndata: {diagnostics.model_dump_json()}\n\n"
        
        # Stream LLM tokens
        messages = self.generation.build_prompt(query, results, diagnostics)
        
        async for token in self.generation.provider.stream(messages, **kwargs):
            # Send standard JSON string for the token to preserve whitespace
            clean_token = json.dumps(token)
            yield f"event: token\ndata: {clean_token}\n\n"
            
        yield "event: done\ndata: {}\n\n"
