from typing import AsyncGenerator, Dict, List, Optional, Any
import time
from openai import AsyncOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import openai
from .base_provider import BaseLLMProvider, GenerationResult, StreamEvent
from backend.core.logging import logger
from backend.observability.langfuse_config import safe_langfuse_context, safe_observe

class OpenAIProvider(BaseLLMProvider):
    """Provider adapter for OpenAI and OpenAI-compatible APIs (vLLM, Ollama, Groq, Together)."""

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: Optional[str] = None):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _update_langfuse(self, messages: List[Dict[str, str]], result: GenerationResult):
        """Helper to sync telemetry context if Langfuse is active."""
        if safe_langfuse_context:
            try:
                safe_langfuse_context.update_current_observation(
                    input=messages,
                    model=result.model,
                    usage={
                        "input": result.prompt_tokens,
                        "output": result.completion_tokens,
                        "total": result.total_tokens
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update Langfuse context: {e}")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying LLM generation due to {retry_state.outcome.exception()}... Attempt {retry_state.attempt_number}")
    )
    @safe_observe(as_type="generation")
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        try:
            start = time.perf_counter()
            
            model = kwargs.pop("model", self.model)
            temperature = kwargs.pop("temperature", 0.0)
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=False,
                **kwargs
            )
            
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            
            result = GenerationResult(
                text=response.choices[0].message.content or "",
                model=response.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                finish_reason=response.choices[0].finish_reason
            )
            
            self._update_langfuse(messages, result)
            return result
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError)),
        before_sleep=lambda retry_state: logger.warning(f"Retrying LLM stream due to {retry_state.outcome.exception()}... Attempt {retry_state.attempt_number}")
    )
    @safe_observe(as_type="generation")
    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamEvent(type="token", content=chunk.choices[0].delta.content)
                    
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise

    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        # Optimized for longer context or reasoning
        kwargs["temperature"] = kwargs.get("temperature", 0.3)
        return await self.generate(messages, **kwargs)

    def model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "status": "active"
        }
