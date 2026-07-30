from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any
from dataclasses import dataclass
from backend.observability.langfuse_config import safe_observe, safe_langfuse_context

@dataclass
class ProviderCapabilities:
    """Standardized provider capabilities (Phase 10)."""
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_images: bool = False
    supports_json: bool = True
    supports_reasoning: bool = False
    supports_long_context: bool = False
    supports_function_calling: bool = False
    max_context: int = 4000
    max_output: int = 2000

@dataclass
class GenerationResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    finish_reason: str

@dataclass
class StreamEvent:
    type: str
    content: Any

class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    @abstractmethod
    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        """Generate a complete synchronous response."""
        pass

    @abstractmethod
    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        """Stream the response tokens asynchronously."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity to the provider endpoint."""
        pass

    @abstractmethod
    @safe_observe(as_type="generation")
    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        """Optimized generation for long-form research tasks."""
        pass

    @abstractmethod
    def model_info(self) -> Dict[str, Any]:
        """Return provider configuration and model details."""
        pass

    def capabilities(self) -> ProviderCapabilities:
        """Return provider capabilities (Phase 10). Override in subclasses."""
        return ProviderCapabilities()
