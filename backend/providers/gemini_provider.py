import os
import asyncio
from typing import AsyncGenerator, Dict, List, Any
from backend.core.logging import logger
from .base_provider import BaseLLMProvider, GenerationResult, StreamEvent
from backend.observability.langfuse_config import safe_observe

try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    import google.generativeai as genai
    HAS_NEW_GENAI = False

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        
        if HAS_NEW_GENAI:
            self.client = genai.Client(api_key=api_key)
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            role = m["role"]
            if role == "system":
                role = "user"
            elif role == "assistant":
                role = "model"
            formatted.append({"role": role, "parts": [m["content"]]})
        return formatted

    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        formatted = self._convert_messages(messages)
        temp = kwargs.get("temperature", 0.0)
        
        if HAS_NEW_GENAI:
            prompt_text = "\n".join([p["parts"][0] for p in formatted])
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(temperature=temp)
            )
            return GenerationResult(
                text=response.text,
                model=self.model_name,
                prompt_tokens=getattr(getattr(response, 'usage_metadata', None), 'prompt_token_count', 0),
                completion_tokens=getattr(getattr(response, 'usage_metadata', None), 'candidates_token_count', 0),
                total_tokens=getattr(getattr(response, 'usage_metadata', None), 'total_token_count', 0),
                finish_reason="stop"
            )
        else:
            response = await self.model.generate_content_async(
                formatted,
                generation_config=genai.types.GenerationConfig(temperature=temp)
            )
            return GenerationResult(
                text=response.text,
                model=self.model_name,
                prompt_tokens=response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                completion_tokens=response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                total_tokens=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
                finish_reason="stop"
            )

    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        formatted = self._convert_messages(messages)
        temp = kwargs.get("temperature", 0.0)
        
        if HAS_NEW_GENAI:
            prompt_text = "\n".join([p["parts"][0] for p in formatted])
            # Synchronous generator wrapped for streaming
            def _sync_stream():
                return self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt_text,
                    config=types.GenerateContentConfig(temperature=temp)
                )
            
            stream_gen = await asyncio.to_thread(_sync_stream)
            for chunk in stream_gen:
                if chunk.text:
                    yield StreamEvent(type="token", content=chunk.text)
        else:
            response = await self.model.generate_content_async(
                formatted,
                stream=True,
                generation_config=genai.types.GenerationConfig(temperature=temp)
            )
            async for chunk in response:
                if chunk.text:
                    yield StreamEvent(type="token", content=chunk.text)

    async def health_check(self) -> bool:
        try:
            if HAS_NEW_GENAI:
                return self.client is not None
            else:
                model_info = genai.get_model(f"models/{self.model_name}")
                return model_info is not None
        except Exception:
            return False

    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        kwargs["temperature"] = kwargs.get("temperature", 0.2)
        return await self.generate(messages, **kwargs)

    def model_info(self) -> Dict[str, Any]:
        return {
            "provider": "gemini",
            "model": self.model_name,
            "status": "active"
        }

