import json
import httpx
from typing import AsyncGenerator, Dict, List, Any
from backend.core.logging import logger
from .base_provider import BaseLLMProvider, GenerationResult, StreamEvent
from backend.observability.langfuse_config import safe_observe

class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "qwen2.5:3b-instruct"):
        self.base_url = base_url
        self.model_name = model_name
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.0)
            }
        }
        
        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return GenerationResult(
            text=data.get("message", {}).get("content", ""),
            model=self.model_name,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            finish_reason="stop" if data.get("done") else "unknown"
        )

    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.0)
            }
        }
        
        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content")
                    if content:
                        yield StreamEvent(type="token", content=content)
                except json.JSONDecodeError:
                    continue

    async def health_check(self) -> bool:
        try:
            res = await self.client.get("/api/tags", timeout=5.0)
            if res.status_code == 200:
                # Check if model is actually pulled
                tags = res.json().get("models", [])
                return any(m.get("name") == self.model_name or m.get("name") == f"{self.model_name}:latest" for m in tags)
            return False
        except Exception:
            return False

    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        # Tweak options for research (e.g. num_ctx)
        kwargs["temperature"] = kwargs.get("temperature", 0.2)
        return await self.generate(messages, **kwargs)

    def model_info(self) -> Dict[str, Any]:
        return {
            "provider": "ollama",
            "model": self.model_name,
            "base_url": self.base_url
        }
