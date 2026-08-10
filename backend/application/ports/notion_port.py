from typing import Protocol, Optional
from domain.movement import Movement

class NotionException(Exception):
    """Raised when the Notion port encounters an unrecoverable error."""
    pass

class NotionPort(Protocol):
    """Interface for saving journey movements to Notion."""
    async def save_movement(self, movement: Movement, target_page_id: Optional[str] = None, legs: Optional[list] = None) -> dict:
        """Saves movement and returns a dict with notion_url, parent_page_id, child_page_ids."""
        ...
