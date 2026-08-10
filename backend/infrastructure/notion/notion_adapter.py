from typing import Optional
from application.ports.notion_port import NotionPort, NotionException
from domain.movement import Movement
from infrastructure.notion.notion_client import NotionClient, NotionClientException
from infrastructure.notion.notion_mapper import NotionMapper
from core.config import settings

import logging

logger = logging.getLogger("autotrip")

class RealNotionAdapter(NotionPort):
    """
    Concrete Implementation of NotionPort.
    Acts as Facade, coordinating Mapper and Client.
    """
    def __init__(self):
        self.client = NotionClient()
        self.mapper = NotionMapper()
        self.database_id = settings.notion_database_id
        
    async def save_movement(self, movement: Movement, target_page_id: Optional[str] = None, legs: Optional[list] = None) -> dict:
        try:
            target_database_id = self.database_id
            if target_page_id:
                target_database_id = await self.client.get_child_database_id(target_page_id, "Transportation")
                
            # Step 2: Parent payload creation
            parent_properties = self.mapper.map_parent_movement(movement)
            
            # Step 3: Create Parent Page
            response = await self.client.post_page(
                database_id=target_database_id,
                properties=parent_properties
            )
            
            parent_page_url = response.get("url", "https://notion.so/fake_success_url")
            parent_page_id = response.get("id")
            
            # If no legs or no target_page_id (i.e. single row save), return just the parent info
            if not target_page_id or not legs:
                return {
                    "notion_url": parent_page_url,
                    "parent_page_id": parent_page_id,
                    "child_page_ids": []
                }
                
            # Step 4: Parent property verification
            parent_property_name = await self.client.get_parent_item_property(target_database_id)
            if not parent_property_name:
                logger.warning(f"Parent item relation property not found in database {target_database_id}. Saving parent only.")
                return {
                    "notion_url": parent_page_url,
                    "parent_page_id": parent_page_id,
                    "child_page_ids": []
                }
                
            # Step 5: Save Child Legs
            child_page_ids = []
            for leg in legs:
                try:
                    leg_properties = self.mapper.map_leg(leg, parent_page_id, parent_property_name)
                    child_response = await self.client.post_page(
                        database_id=target_database_id,
                        properties=leg_properties
                    )
                    child_page_ids.append(child_response.get("id"))
                except Exception as e:
                    logger.error(f"Failed to create child leg: segment_index={getattr(leg, 'segment_index', 'unknown')} parent_page_id={parent_page_id} error={e}")
                    # We don't rollback in Notion API, we just raise or log. 
                    # According to instructions: log and raise appropriate exception
                    raise NotionException(f"Failed to create child leg: {e}")
                    
            return {
                "notion_url": parent_page_url,
                "parent_page_id": parent_page_id,
                "child_page_ids": child_page_ids
            }
                
        except NotionClientException as e:
            raise NotionException(f"Failed to save movement to Notion: {e}") from e
