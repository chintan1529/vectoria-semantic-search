import asyncio
from typing import Any, Optional
from cachetools import TTLCache

class CacheService:
    """
    Abstract caching layer to allow future Redis migration.
    Currently uses an in-memory TTLCache.
    """
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: Any) -> None:
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

# Global singleton (Redis-ready abstraction)
cache_service = CacheService()
