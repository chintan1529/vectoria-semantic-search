import os
from typing import AsyncGenerator, Dict, List, Any
from backend.core.logging import logger
from .base_provider import BaseLLMProvider, GenerationResult, StreamEvent
from backend.observability.langfuse_config import safe_observe
from huggingface_hub import AsyncInferenceClient
import httpx

class HuggingFaceProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "microsoft/Phi-3-mini-4k-instruct"):
        self.api_key = api_key
        self.model_name = model_name
        self.client = AsyncInferenceClient(model=self.model_name, token=self.api_key)

    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        response = await self.client.chat_completion(
            messages=messages,
            stream=False,
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.1)
        )
        
        return GenerationResult(
            text=response.choices[0].message.content,
            model=self.model_name,
            prompt_tokens=response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
            completion_tokens=response.usage.completion_tokens if hasattr(response, 'usage') else 0,
            total_tokens=response.usage.total_tokens if hasattr(response, 'usage') else 0,
            finish_reason=response.choices[0].finish_reason if hasattr(response.choices[0], 'finish_reason') else "stop"
        )

    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        stream = await self.client.chat_completion(
            messages=messages,
            stream=True,
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.1)
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamEvent(type="token", content=chunk.choices[0].delta.content)

    async def health_check(self) -> bool:
        # Ping the HF Inference API endpoint directly to see if model is loaded/available
        url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                return res.status_code in (200, 503)
        except Exception:
            return False

    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        kwargs["temperature"] = kwargs.get("temperature", 0.3)
        return await self.generate(messages, **kwargs)

    def model_info(self) -> Dict[str, Any]:
        return {
            "provider": "huggingface",
            "model": self.model_name,
            "status": "active"
        }
