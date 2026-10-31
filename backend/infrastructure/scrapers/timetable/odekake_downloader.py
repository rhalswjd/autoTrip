"""Ordinary public HTTP access, with cache, low concurrency and no evasion."""
import asyncio
import hashlib
from urllib.parse import urlparse

import httpx

from application.ports.cache_port import CachePort
from application.ports.scraper_port import ScraperException


class JROdekakeDownloader:
    ALLOWED_HOSTS = {"eki.jr-odekake.net", "timetable.jr-odekake.net"}

    def __init__(self, cache: CachePort | None = None):
        self.cache = cache
        self._semaphore = asyncio.Semaphore(2)
        self.rate_limited = False
        self.requests = 0
        self.cache_hits = 0
        self.redirects = 0
        self.kinds = {"station": 0, "timetable": 0, "detail": 0}

    def statistics(self) -> dict[str, int]:
        return {**self.kinds, "total": self.requests, "cache_hits": self.cache_hits, "redirects": self.redirects}

    async def fetch_html(self, url: str) -> str:
        if urlparse(url).scheme != "https" or urlparse(url).hostname not in self.ALLOWED_HOSTS:
            raise ScraperException("JR Odekake returned an unsupported public URL")
        if self.rate_limited:
            raise ScraperException("JR Odekake HTTP 429: further requests stopped")
        key = "jr-html-v2:" + hashlib.sha256(url.encode()).hexdigest()
        if self.cache:
            cached = await self.cache.get(key)
            if isinstance(cached, str):
                self.cache_hits += 1
                return cached
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                    response = await client.get(url)
                    self.requests += 1 + len(response.history)
                    self.redirects += len(response.history)
                    for transaction in [*response.history, response]:
                        path = transaction.request.url.path
                        kind = 'detail' if '/train-timetable/' in path else 'timetable' if '/station-timetable/' in path else 'station'
                        self.kinds[kind] += 1
                    if response.status_code == 429:
                        self.rate_limited = True
                    response.raise_for_status()
                    encoding = response.encoding
                    if "charset=Shift_JIS" in response.text[:700]:
                        encoding = "shift_jis"
                    html = response.content.decode(encoding or "utf-8", errors="replace")
            except httpx.HTTPStatusError as exc:
                raise ScraperException(f"JR Odekake HTTP {exc.response.status_code}; official timetable unavailable") from exc
            except httpx.HTTPError as exc:
                raise ScraperException(f"JR Odekake network failure: {type(exc).__name__}") from exc
        if self.cache:
            await self.cache.set(key, html, ttl_seconds=3600)
        return html

    async def fetch_htmls(self, urls: dict[str, str]) -> dict[str, str]:
        return {key: await self.fetch_html(url) for key, url in urls.items()}
