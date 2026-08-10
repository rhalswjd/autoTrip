from domain.timetable import Timetable
from application.ports.scraper_port import ScraperPort

from application.ports.cache_port import CachePort

class TimetableService:
    def __init__(self, scraper_port: ScraperPort, cache_port: CachePort = None):
        self.scraper_port = scraper_port
        self.cache_port = cache_port

    async def get_timetable(self, route_id: str) -> Timetable:
        if self.cache_port:
            route = await self.cache_port.get(route_id)
            if route:
                dep = route.stations[0].name_jp if route.stations and route.stations[0].name_jp else route.departure_station
                arr = route.stations[1].name_jp if route.stations and len(route.stations) > 1 and route.stations[1].name_jp else route.arrival_station
                
                railway_jp = route.segments[0].railway_name_jp if route.segments else ""
                
                timetable = await self.scraper_port.get_timetable(route_id, dep, arr, timetable_id=None, railway_name_jp=railway_jp)
                from core.logger import logger
                logger.info(f"[Service] Received from adapter (cache hit): type={type(timetable)}, weekday count={len(timetable.weekday)}")
                logger.info(f"[Service] Returning: type={type(timetable)}, weekday count={len(timetable.weekday)}")
                return timetable
        
        # If no cache, this shouldn't normally happen but we keep the old logic
        timetable = await self.scraper_port.get_timetable(route_id, timetable_id=None)
        from core.logger import logger
        logger.info(f"[Service] Received from adapter (no cache): type={type(timetable)}, weekday count={len(timetable.weekday)}")
        logger.info(f"[Service] Returning: type={type(timetable)}, weekday count={len(timetable.weekday)}")
        return timetable

    async def get_segment_timetable(self, route_id: str, segment_index: int, timetable_id: str | None = None) -> Timetable:
        if not self.cache_port:
            raise ValueError("Cache is required to get segments")
            
        route = await self.cache_port.get(route_id)
        if not route:
            raise ValueError(f"Route {route_id} not found")
            
        if not route.segments or segment_index < 0 or segment_index >= len(route.segments):
            raise ValueError(f"Invalid segment_index {segment_index}")
            
        dep = route.stations[segment_index].name_jp if route.stations[segment_index].name_jp else route.stations[segment_index].name
        arr = route.stations[segment_index+1].name_jp if route.stations[segment_index+1].name_jp else route.stations[segment_index+1].name
        segment = route.segments[segment_index]
        railway_jp = getattr(segment, "railway_name_jp", "")
        
        timetable = await self.scraper_port.get_timetable(route_id, dep, arr, timetable_id=timetable_id, railway_name_jp=railway_jp)
        return timetable
