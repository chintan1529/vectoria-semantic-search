from typing import AsyncGenerator, Dict, List
import openai
from .base_provider import BaseLLMProvider, GenerationResult

class OpenAIProvider(BaseLLMProvider):
    """Provider adapter for OpenAI and OpenAI-compatible APIs (vLLM, Ollama, Groq, Together)."""

    def __init__(self, api_key: str, base_url: str = None, model: str = "gpt-4o"):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        model = kwargs.pop("model", self.model)
        temperature = kwargs.pop("temperature", 0.0)
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            **kwargs
        )
        
        choice = response.choices[0]
        usage = response.usage
        
        return GenerationResult(
            text=choice.message.content or "",
            model=response.model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            finish_reason=choice.finish_reason or "unknown"
        )

    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        model = kwargs.pop("model", self.model)
        temperature = kwargs.pop("temperature", 0.0)
        
        stream_response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
