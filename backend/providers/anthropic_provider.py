from typing import AsyncGenerator, Dict, List
import anthropic
from .base_provider import BaseLLMProvider, GenerationResult

class AnthropicProvider(BaseLLMProvider):
    """Provider adapter for Anthropic Claude models."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        self.model = model
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple[str, List[Dict[str, str]]]:
        """Convert standard messages to Anthropic's format (extracts system prompt)."""
        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                anthropic_messages.append(msg)
        return system_prompt.strip(), anthropic_messages

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        model = kwargs.pop("model", self.model)
        temperature = kwargs.pop("temperature", 0.0)
        max_tokens = kwargs.pop("max_tokens", 1024)
        
        system, formatted_messages = self._convert_messages(messages)
        
        response = await self.client.messages.create(
            model=model,
            system=system,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        return GenerationResult(
            text=response.content[0].text,
            model=response.model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            finish_reason=response.stop_reason or "unknown"
        )

    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        model = kwargs.pop("model", self.model)
        temperature = kwargs.pop("temperature", 0.0)
        max_tokens = kwargs.pop("max_tokens", 1024)
        
        system, formatted_messages = self._convert_messages(messages)
        
        async with self.client.messages.stream(
            model=model,
            system=system,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text
