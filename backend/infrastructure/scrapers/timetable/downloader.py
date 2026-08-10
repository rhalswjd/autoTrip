import httpx
import asyncio

class TimetableDownloader:
    """
    HTTP 통신만을 담당하는 클래스.
    URL 완성본을 받아서 HTML을 가져오는 역할만 하며 파라미터 조합이나 파싱은 절대로 하지 않습니다.
    """
    def __init__(self, timeout: int = 15, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        
    async def fetch_html(self, url: str) -> str:
        from core.logger import logger
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"[TimetableDownloader] Requesting URL: {url}")
                    response = await client.get(url)
                    response.raise_for_status()
                    logger.info(f"[TimetableDownloader] Final response.url: {response.url}")
                    return response.text
                except httpx.RequestError as exc:
                    if attempt == self.max_retries - 1:
                        # TODO: Replace generic Exception with 
                        # TimetableDownloadError / TimetableParseError
                        # when project-wide scraper exception hierarchy is introduced.
                        raise Exception(f"Failed to fetch HTML after {self.max_retries} attempts: {exc}")
                    await asyncio.sleep(1 * (attempt + 1))
            raise Exception("Unexpected error in TimetableDownloader")
