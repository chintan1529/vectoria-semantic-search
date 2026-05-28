from typing import List, Dict
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider, GenerationResult

class GenerationOrchestrator:
    """
    Orchestrates the LLM generation phase based on retrieved context.
    """
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def build_prompt(self, query: str, results: List[SearchResult]) -> List[Dict[str, str]]:
        """Construct the prompt with retrieved context."""
        context_blocks = []
        for i, res in enumerate(results, 1):
            title = res.chunk.metadata.title
            text = res.chunk.text
            context_blocks.append(f"[Source {i}: {title}]\n{text}")
            
        context_text = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are an elite, highly intelligent AI assistant. "
            "Use the provided context to answer the user's query comprehensively and accurately. "
            "Always cite your sources using the [Source X: Title] format inline where appropriate. "
            "If the answer is not contained in the context, state that clearly."
        )
        
        user_prompt = f"Context:\n{context_text}\n\nQuery: {query}"
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    async def generate_response(self, query: str, results: List[SearchResult], **kwargs) -> GenerationResult:
        messages = self.build_prompt(query, results)
        return await self.provider.generate(messages, **kwargs)
