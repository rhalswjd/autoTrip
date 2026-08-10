import httpx
import asyncio
from typing import Dict, Any, Optional
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
                except httpx.HTTPStatusError as e:
                    error_body = e.response.text
                    logger.error(f"Notion HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - Status {e.response.status_code} - Body: {error_body}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Failed to post page: {error_body}")
                except httpx.HTTPError as e:
                    logger.warning(f"Notion HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - {e}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Failed to post page: {e}")
                        
                logger.debug(f"Retry Notion Request (attempt {attempt + 2}/{self.retries})")
                await asyncio.sleep(1)
                
        raise NotionClientException("Unknown NotionClient error")

    async def get_child_database_id(self, page_id: str, database_title: str = "Transportation") -> str:
        """Finds a child database with the specified title within a page."""
        url = f"{self.base_url}/blocks/{page_id}/children"
        
        has_more = True
        next_cursor = None
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            while has_more:
                params = {}
                if next_cursor:
                    params["start_cursor"] = next_cursor
                    
                for attempt in range(self.retries):
                    try:
                        response = await client.get(url, params=params)
                        if response.status_code in (400, 401, 403, 404):
                            error_body = response.text
                            logger.error(f"Notion API Error {response.status_code} for page {page_id}. Body: {error_body}")
                            raise NotionClientException(f"Failed to access page {page_id}. Please check ID and Notion integration permissions. Error: {error_body}")
                        response.raise_for_status()
                        data = response.json()
                        
                        for block in data.get("results", []):
                            if block.get("type") == "child_database":
                                child_db = block.get("child_database", {})
                                title = child_db.get("title", "")
                                if database_title.strip().lower() in title.strip().lower():
                                    return block.get("id")
                        
                        has_more = data.get("has_more", False)
                        next_cursor = data.get("next_cursor")
                        break # Break retry loop on success
                    except httpx.TimeoutException as e:
                        logger.warning(f"Notion HTTP Timeout (attempt {attempt + 1}/{self.retries}): {url}")
                        if attempt == self.retries - 1:
                            raise NotionClientException(f"Timeout: {e}")
                    except httpx.HTTPError as e:
                        logger.warning(f"Notion HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - {e}")
                        if attempt == self.retries - 1:
                            raise NotionClientException(f"Failed to fetch page children: {e}")
                            
                    await asyncio.sleep(1)

        raise NotionClientException(f"Child database '{database_title}' not found in page {page_id}")

    async def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Fetches the schema (properties) of a Notion database."""
        url = f"{self.base_url}/databases/{database_id}"
        
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            for attempt in range(self.retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    return data.get("properties", {})
                except httpx.TimeoutException as e:
                    logger.warning(f"Notion HTTP Timeout (attempt {attempt + 1}/{self.retries}): {url}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Timeout: {e}")
                except httpx.HTTPError as e:
                    logger.warning(f"Notion HTTP Error (attempt {attempt + 1}/{self.retries}): {url} - {e}")
                    if attempt == self.retries - 1:
                        raise NotionClientException(f"Failed to fetch database schema: {e}")
                        
                await asyncio.sleep(1)

        raise NotionClientException(f"Unknown error fetching database schema for {database_id}")

    async def get_parent_item_property(self, database_id: str) -> Optional[str]:
        """Finds the '상위 항목' relation property name if it exists."""
        schema = await self.get_database_schema(database_id)
        
        for prop_name, prop_data in schema.items():
            if prop_name == "상위 항목" and prop_data.get("type") == "relation":
                return prop_name
                
        return None
