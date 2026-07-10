from typing import Protocol
from domain.movement import Movement

class NotionException(Exception):
    """Raised when the Notion port encounters an unrecoverable error."""
    pass

class NotionPort(Protocol):
    """Interface for saving journey movements to Notion."""
    async def save_movement(self, movement: Movement) -> str:
        """Saves movement and returns the saved Notion page URL."""
        ...
