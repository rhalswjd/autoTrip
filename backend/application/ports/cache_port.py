from typing import Protocol, Any, Optional

class CachePort(Protocol):
    """Interface for caching mechanisms in the application."""
    async def get(self, key: str) -> Optional[Any]:
        ...
        
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        ...

    async def delete(self, key: str) -> None:
        ...

    async def clear(self) -> None:
        ...
