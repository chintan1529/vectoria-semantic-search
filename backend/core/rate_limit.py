import asyncio
from typing import Dict
from aiolimiter import AsyncLimiter
from fastapi import HTTPException

class RateLimiterService:
    """
    Abstract Rate Limiter to allow future Redis migration.
    Currently uses an in-memory aiolimiter per client.
    """
    def __init__(self, max_requests: int = 20, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self._limiters: Dict[str, AsyncLimiter] = {}
        self._lock = asyncio.Lock()

    async def _get_limiter(self, key: str) -> AsyncLimiter:
        async with self._lock:
            if key not in self._limiters:
                self._limiters[key] = AsyncLimiter(self.max_requests, self.time_window)
            return self._limiters[key]

    async def check_rate_limit(self, client_id: str) -> None:
        """
        Check if the client has exceeded the rate limit.
        Raises HTTP 429 if exceeded.
        """
        limiter = await self._get_limiter(client_id)
        if not limiter.has_capacity():
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
        # Consume 1 token
        await limiter.acquire()

# Global singleton
rate_limiter = RateLimiterService()
