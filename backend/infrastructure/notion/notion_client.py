import httpx
import asyncio
from typing import Dict, Any
from core.config import settings
from infrastructure.exceptions import InfrastructureException
import logging

logger = logging.getLogger("autotrip")

class NotionClientException(InfrastructureException):
    pass

class NotionClient:
    """
    HTTP Wrapper exclusively for Notion API.
    Handles timeout, retry, auth headers, and versioning.
    No JSON body formatting logic resides here.
    """
    def __init__(self, retries: int = None, timeout: int = None):
        self.retries = retries or settings.request_retry
        self.timeout = timeout or settings.request_timeout
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.notion_api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    async def post_page(self, database_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/pages"
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        safe_headers = {k: ("***" if k.lower() == "authorization" else v) for k, v in self.headers.items()}
        logger.debug(f"HTTP Request: POST {url} with headers {safe_headers}")
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for attempt in range(self.retries):
                try:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    logger.debug(f"HTTP Response: {response.status_code} from {url}")
                    return response.json()
                except httpx.TimeoutException as e:
                    logger.warning(f"Notion HTTP Timeout (attempt {attempt + 1}/{self.retries}): {url}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Timeout: {e}")
                except httpx.HTTPError as e:
                    logger.warning(f"Notion HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - {e}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Failed to post page: {e}")
                        
                logger.debug(f"Retry Notion Request (attempt {attempt + 2}/{self.retries})")
                await asyncio.sleep(1)
                
        raise NotionClientException("Unknown NotionClient error")
