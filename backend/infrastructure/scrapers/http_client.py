import httpx
import asyncio
from typing import Optional
from infrastructure.exceptions import HttpClientException
from core.config import settings
import logging
import time

logger = logging.getLogger("autotrip")

class HttpClient:
    """
    HTTP Wrapper to encapsulate httpx logic.
    Handles timeout, retry, user-agent settings, and rate limiting.
    """
    def __init__(self, timeout: int = None, retries: int = None, rate_limit_delay: float = None):
        self.timeout = timeout or settings.request_timeout
        self.retries = retries or settings.request_retry
        self.rate_limit_delay = rate_limit_delay or settings.request_delay
        self.last_request_time = 0.0
        self.headers = {
            "User-Agent": settings.user_agent
        }
        
    async def _rate_limit(self):
        """Enforces a short delay between consecutive requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
        
    async def get(self, url: str, params: Optional[dict] = None) -> str:
        logger.debug(f"HTTP Request: GET {url}")
        await self._rate_limit()
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for attempt in range(self.retries):
                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    logger.debug(f"HTTP Response: {response.status_code} from {url}")
                    return response.text
                except httpx.TimeoutException as e:
                    logger.warning(f"HTTP Timeout (attempt {attempt + 1}/{self.retries}): {url}")
                    if attempt == self.retries - 1:
                        raise HttpClientException(f"Timeout: {e}")
                except httpx.HTTPError as e:
                    logger.warning(f"HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - {e}")
                    if attempt == self.retries - 1:
                        raise HttpClientException(f"Failed to fetch {url} after {self.retries} retries: {e}")
                
                logger.debug(f"Retry HTTP Request: {url} (attempt {attempt + 2}/{self.retries})")
                await asyncio.sleep(1)
        raise HttpClientException("Unknown HttpClient error")
