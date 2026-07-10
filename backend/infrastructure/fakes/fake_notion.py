from application.ports.notion_port import NotionPort, NotionException
from domain.movement import Movement
from core.logger import logger

class FakeNotionAdapter(NotionPort):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        
    async def save_movement(self, movement: Movement) -> str:
        if self.should_fail:
            raise NotionException("Fake Notion Failure")
        logger.info(f"[FakeNotion] Saved movement from {movement.route.departure_station}")
        return "https://notion.so/fake_movement_url"
