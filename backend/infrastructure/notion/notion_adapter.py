from application.ports.notion_port import NotionPort, NotionException
from domain.movement import Movement
from infrastructure.notion.notion_client import NotionClient, NotionClientException
from infrastructure.notion.notion_mapper import NotionMapper
from core.config import settings

class RealNotionAdapter(NotionPort):
    """
    Concrete Implementation of NotionPort.
    Acts as Facade, coordinating Mapper and Client.
    """
    def __init__(self):
        self.client = NotionClient()
        self.mapper = NotionMapper()
        self.database_id = settings.notion_database_id
        
    async def save_movement(self, movement: Movement) -> str:
        properties = self.mapper.map_to_properties(movement)
        
        try:
            response = await self.client.post_page(
                database_id=self.database_id,
                properties=properties
            )
            return response.get("url", "https://notion.so/fake_success_url")
        except NotionClientException as e:
            raise NotionException(f"Failed to save movement to Notion: {e}") from e
