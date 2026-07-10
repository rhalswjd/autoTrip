from typing import Any, Optional
from application.ports.cache_port import CachePort

class FakeCacheAdapter(CachePort):
    def __init__(self):
        self._store = {}
        
    async def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)
        
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> None:
        self._store.clear()
