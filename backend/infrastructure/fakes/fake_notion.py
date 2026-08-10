from application.ports.notion_port import NotionPort, NotionException
from domain.movement import Movement
from core.logger import logger

class FakeNotionAdapter(NotionPort):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.saved_movements = []
        
    async def save_movement(self, movement: Movement, target_page_id: str | None = None, legs: list | None = None) -> dict:
        if self.should_fail:
            from application.ports.notion_port import NotionException
            raise NotionException("Fake Notion Failure")
        self.saved_movements.append(movement)
        return {
            "status": "saved",
            "notion_url": "https://notion.so/fake-page",
            "parent_page_id": "fake_parent",
            "child_page_ids": ["fake_child"]
        }
