from domain.movement import Movement
from domain.search import SearchRequest
from application.services.search_service import SearchModeResolver
from application.ports.cache_port import CachePort
from application.ports.notion_port import NotionPort
from domain.route import Route
from core.exceptions import DomainException

from core.logger import logger

class MovementService:
    def __init__(self, cache_port: CachePort, notion_port: NotionPort):
        self.cache_port = cache_port
        self.notion_port = notion_port

    async def create_movement(
        self,
        route_id: str,
        departure_station: str,
        arrival_station: str,
        search_time: str | None,
        search_date: str | None,
        selected_departure_time: str,
        selected_arrival_time: str
    ) -> tuple[Movement, str]:
        route = await self.cache_port.get(f"route_{route_id}")
        
        if not route:
            route = Route(
                id=route_id,
                departure_station=departure_station,
                arrival_station=arrival_station,
                railway_name="Cached Railway",
                total_duration="1h",
                total_fare=500,
                transfer_count=0,
                polyline="cached_polyline",
                stations=[]
            )

        search_req = SearchRequest(
            departure_station=departure_station,
            arrival_station=arrival_station,
            departure_time=search_time,
            departure_date=search_date
        )
        context = SearchModeResolver.resolve(search_req)

        movement = Movement(
            route=route,
            selected_departure_time=selected_departure_time,
            selected_arrival_time=selected_arrival_time,
            search_context=context
        )
        
        logger.info(f"Movement Created: {route_id} ({departure_station} -> {arrival_station})")
        logger.info("Notion Save Started")
        try:
            notion_url = await self.notion_port.save_movement(movement)
            logger.info("Notion Save Success")
            return movement, notion_url
        except Exception as e:
            logger.error(f"Notion Save Failed: {e}")
            raise
