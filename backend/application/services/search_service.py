import hashlib
from typing import List
from domain.search import SearchRequest, SearchContext
from domain.enums import SearchMode
from domain.route import Route
from application.ports.scraper_port import ScraperPort
from application.ports.cache_port import CachePort
from domain.exceptions import DomainException

from core.logger import logger
from application.services.route_families import group_route_families, categorize_routes

class SearchModeResolver:
    @staticmethod
    def resolve(request: SearchRequest) -> SearchContext:
        if request.departure_date and request.departure_time:
            mode = SearchMode.ROUTE_WITH_DATETIME
        elif request.departure_time and not request.departure_date:
            mode = SearchMode.ROUTE_WITH_TIME
        else:
            mode = SearchMode.ROUTE_ONLY
            
        return SearchContext(
            departure_station=request.departure_station,
            arrival_station=request.arrival_station,
            departure_time=request.departure_time,
            departure_date=request.departure_date,
            search_mode=mode
        )

class SearchService:
    def __init__(self, scraper_port: ScraperPort, cache_port: CachePort, station_repo, cache_ttl: int = 3600):
        self.scraper_port = scraper_port
        self.cache_port = cache_port
        self.station_repo = station_repo
        self.cache_ttl = cache_ttl
        
    def _generate_cache_key(self, request: SearchRequest) -> str:
        raw_key = f"families-v2_{request.departure_station}_{request.arrival_station}_{request.departure_time or 'NONE'}_{request.departure_date or 'NONE'}"
        return hashlib.md5(raw_key.encode()).hexdigest()

    async def _get_jp_name(self, name_en: str) -> str:
        stations = await self.station_repo.search_stations(name_en)
        for s in stations:
            if s.name.lower() == name_en.lower():
                return s.name_jp
        return name_en

    async def _populate_independent_fares(self, routes: List[Route], departure_time: str, departure_date: str):
        import asyncio
        from core.logger import logger
        
        async def fetch_fare(route_idx, seg_idx, seg, dep_station: str, arr_station: str):
            try:
                dep_jp = await self._get_jp_name(dep_station)
                arr_jp = await self._get_jp_name(arr_station)
                
                indep_routes = await self.scraper_port.search_routes(
                    departure=dep_jp,
                    arrival=arr_jp,
                    time=departure_time,
                    date=departure_date
                )
                if indep_routes:
                    for r in indep_routes:
                        for s in r.segments:
                            if seg.railway_name and (seg.railway_name in s.railway_name or s.railway_name in seg.railway_name):
                                return route_idx, seg_idx, seg.model_copy(update={"base_fare": s.base_fare, "express_fare": s.express_fare})
                    if indep_routes[0].segments:
                        first_seg = indep_routes[0].segments[0]
                        return route_idx, seg_idx, seg.model_copy(update={"base_fare": first_seg.base_fare, "express_fare": first_seg.express_fare})
            except Exception as e:
                logger.error(f"Failed to fetch independent fare for {dep_station} -> {arr_station}: {e}")
            return route_idx, seg_idx, seg

        tasks = []
        for route_idx, r in enumerate(routes):
            if len(r.segments) > 1:
                for seg_idx, seg in enumerate(r.segments):
                    dep_station = r.stations[seg_idx].name
                    arr_station = r.stations[seg_idx+1].name
                    tasks.append(fetch_fare(route_idx, seg_idx, seg, dep_station, arr_station))
                    
        if tasks:
            logger.info(f"Fetching {len(tasks)} independent fares concurrently...")
            results = await asyncio.gather(*tasks)
            
            updates = {}
            for r_idx, s_idx, new_seg in results:
                if r_idx not in updates:
                    updates[r_idx] = list(routes[r_idx].segments)
                updates[r_idx][s_idx] = new_seg
                
            for r_idx, new_segments in updates.items():
                routes[r_idx] = routes[r_idx].model_copy(update={"segments": new_segments})

    async def search(self, request: SearchRequest) -> List[Route]:
        logger.info(f"Route Search Started: {request.departure_station} -> {request.arrival_station}")
        
        if request.departure_station == request.arrival_station:
            raise DomainException("Departure and arrival stations cannot be the same.")
        if not request.departure_date or not request.departure_time:
            raise DomainException("Route search requires an explicit departure date and time.")

        cache_key = self._generate_cache_key(request)
        cached_routes = await self.cache_port.get(cache_key)
        
        if cached_routes is not None:
            logger.info(f"Cache Hit for {request.departure_station} -> {request.arrival_station}")
            return cached_routes
            
        logger.info(f"Cache Miss for {request.departure_station} -> {request.arrival_station}")
        
        dep_jp = await self._get_jp_name(request.departure_station)
        arr_jp = await self._get_jp_name(request.arrival_station)
        
        logger.info(f"Scraper Started: {dep_jp} ({request.departure_station}) -> {arr_jp} ({request.arrival_station})")
        
        routes = await self.scraper_port.search_routes(
            departure=dep_jp,
            arrival=arr_jp,
            time=request.departure_time,
            date=request.departure_date
        )
        
        logger.info(f"Scraper Finished: Found {len(routes)} routes")
        
        if not routes:
            return []

        # The application request is the source of truth for both the cached route
        # and every later exact-date timetable lookup.
        routes = [
            route.model_copy(update={
                "search_date": request.departure_date,
                "search_time": request.departure_time,
            })
            for route in routes
        ]
            
        # Route fares describe the discovery sample only. Re-searching every raw
        # segment amplified requests and still could not price a later selected train.
        routes = categorize_routes(group_route_families(routes))
            
        await self.cache_port.set(cache_key, routes, ttl_seconds=self.cache_ttl)
        for r in routes:
            await self.cache_port.set(r.id, r, ttl_seconds=self.cache_ttl)
            
        return routes

    async def get_route(self, route_id: str) -> Route:
        route = await self.cache_port.get(route_id)
        if not isinstance(route, Route):
            raise DomainException("Route expired or missing; search again")
        return route
