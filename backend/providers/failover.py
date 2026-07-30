import time
from typing import AsyncGenerator, Dict, List, Any, Optional
from enum import Enum
from backend.core.logging import logger
from backend.providers.base_provider import BaseLLMProvider, GenerationResult, StreamEvent
import asyncio

class CircuitState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class FailoverProviderWrapper(BaseLLMProvider):
    """
    Wraps multiple LLM providers to implement automatic failover, retries, and circuit breaking.
    """
    def __init__(self, providers: List[BaseLLMProvider], max_retries_per_provider: int = 2):
        self.providers = providers
        self.max_retries = max_retries_per_provider
        
        if not self.providers:
            raise ValueError("At least one provider must be configured for failover.")
            
        self._provider_health = {i: CircuitState.HEALTHY for i in range(len(self.providers))}
        
    @property
    def model(self) -> str:
        if self.providers:
            return getattr(self.providers[0], "model_name", getattr(self.providers[0], "model", "unknown_provider"))
        return "unknown_provider"

    @property
    def model_name(self) -> str:
        return self.model
        
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        last_error = None
        for i, provider in enumerate(self.providers):
            # Skip definitely unhealthy providers
            if self._provider_health[i] == CircuitState.UNHEALTHY:
                continue
                
            for attempt in range(self.max_retries):
                try:
                    result = await provider.generate(messages, **kwargs)
                    self._provider_health[i] = CircuitState.HEALTHY
                    return result
                except Exception as e:
                    last_error = e
                    logger.warning(f"[Failover] Provider {provider.__class__.__name__} failed (attempt {attempt+1}): {e}")
                    await asyncio.sleep(0.5 * (attempt + 1))
            
            # If all attempts fail, mark degraded/unhealthy and failover
            self._provider_health[i] = CircuitState.DEGRADED
            logger.error(f"[Failover] Provider {provider.__class__.__name__} exhausted retries. Failing over to next provider.")
            
        raise RuntimeError(f"All configured providers failed. Last error: {last_error}")

    async def stream(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[StreamEvent, None]:
        last_error = None
        for i, provider in enumerate(self.providers):
            if self._provider_health[i] == CircuitState.UNHEALTHY:
                continue
                
            for attempt in range(self.max_retries):
                try:
                    # Notify SSE about the active provider or failover
                    if i > 0 or attempt > 0:
                        yield StreamEvent(type="failover", content={
                            "event": "provider_failover_started",
                            "provider": provider.__class__.__name__,
                            "attempt": attempt + 1
                        })
                        
                    stream_gen = provider.stream(messages, **kwargs)
                    
                    # Yield tokens. If this succeeds without breaking, we're done
                    async for event in stream_gen:
                        yield event
                        
                    self._provider_health[i] = CircuitState.HEALTHY
                    return
                except Exception as e:
                    last_error = e
                    logger.warning(f"[Failover] Provider {provider.__class__.__name__} stream failed: {e}")
                    yield StreamEvent(type="failover", content={
                        "event": "provider_unhealthy",
                        "provider": provider.__class__.__name__,
                        "error": str(e)
                    })
                    await asyncio.sleep(0.5)
                    
            self._provider_health[i] = CircuitState.DEGRADED
            
        raise RuntimeError(f"All configured providers failed to stream. Last error: {last_error}")

    async def health_check(self) -> bool:
        # If at least one provider is healthy, the system is healthy
        for i, provider in enumerate(self.providers):
            if await provider.health_check():
                self._provider_health[i] = CircuitState.HEALTHY
                return True
            else:
                self._provider_health[i] = CircuitState.UNHEALTHY
        return False

    async def research_generate(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        # Same failover logic as generate
        last_error = None
        for i, provider in enumerate(self.providers):
            if self._provider_health[i] == CircuitState.UNHEALTHY:
                continue
            try:
                return await provider.research_generate(messages, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"[Failover] Provider {provider.__class__.__name__} research_generate failed: {e}")
        raise RuntimeError(f"All providers failed research_generate: {last_error}")

    def model_info(self) -> Dict[str, Any]:
        info = {
            "strategy": "failover",
            "providers": []
        }
        for i, p in enumerate(self.providers):
            p_info = p.model_info()
            p_info["circuit_state"] = self._provider_health[i].value
            p_info["priority"] = i
            info["providers"].append(p_info)
            
        # Determine overall state
        active_provider = next((p for i, p in enumerate(self.providers) if self._provider_health[i] != CircuitState.UNHEALTHY), None)
        if active_provider:
            info["current_provider"] = active_provider.__class__.__name__
        else:
            info["current_provider"] = "None"
            
        return info
