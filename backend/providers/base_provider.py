from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any
from dataclasses import dataclass
from backend.observability.langfuse_config import safe_observe, safe_langfuse_context

@dataclass
class GenerationResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers (OpenAI, Anthropic, Local, etc.)."""
    
    @abstractmethod
    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        """Generate a complete synchronous response."""
        pass

    @abstractmethod
    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """Stream the response tokens asynchronously."""
        pass
