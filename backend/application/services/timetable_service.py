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

    async def get_segment_platform(self, route_id: str, segment_index: int, time: str, train_name: str, date: str | None = None) -> str | None:
        if not self.cache_port:
            raise ValueError("Cache is required to get segments")
            
        route = await self.cache_port.get(route_id)
        if not route:
            raise ValueError(f"Route {route_id} not found")
            
        if not route.segments or segment_index < 0 or segment_index >= len(route.segments):
            raise ValueError(f"Invalid segment_index {segment_index}")
            
        dep = route.stations[segment_index].name_jp if route.stations[segment_index].name_jp else route.stations[segment_index].name
        arr = route.stations[segment_index+1].name_jp if route.stations[segment_index+1].name_jp else route.stations[segment_index+1].name
        
        if not date:
            import datetime
            jst = datetime.timezone(datetime.timedelta(hours=9))
            date = datetime.datetime.now(jst).strftime('%Y-%m-%d')
            
        from core.logger import logger
        logger.info(f"Platform Lookup: searching {dep}->{arr} at {time} on {date} for train {train_name}")
        
        routes = await self.scraper_port.search_routes(
            departure=dep,
            arrival=arr,
            time=time,
            date=date
        )
        
        if not routes:
            return None
            
        train_name_lower = train_name.lower().replace(" ", "")
        
        for r in routes:
            if not r.segments:
                continue
            
            # Match departure time
            if r.departure_time != time:
                continue
                
            for seg in r.segments:
                rn_jp = seg.railway_name_jp.lower().replace(" ", "")
                rn_en = seg.railway_name.lower().replace(" ", "")
                
                if (train_name_lower in rn_jp or rn_jp in train_name_lower or 
                    train_name_lower in rn_en or rn_en in train_name_lower):
                    logger.info(f"Platform Lookup: matched {seg.railway_name}, returning platform {seg.departure_platform}")
                    return seg.departure_platform
                    
        return None
