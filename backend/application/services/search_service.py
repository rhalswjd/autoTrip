import hashlib
from typing import List
from domain.search import SearchRequest, SearchContext
from domain.enums import SearchMode
from domain.route import Route
from application.ports.scraper_port import ScraperPort
from application.ports.cache_port import CachePort
from core.exceptions import DomainException

from core.logger import logger

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
        raw_key = f"{request.departure_station}_{request.arrival_station}_{request.departure_time or 'NONE'}_{request.departure_date or 'NONE'}"
        return hashlib.md5(raw_key.encode()).hexdigest()

    async def _get_jp_name(self, name_en: str) -> str:
        stations = await self.station_repo.search_stations(name_en)
        for s in stations:
            if s.name.lower() == name_en.lower():
                return s.name_jp
        return name_en

    async def search(self, request: SearchRequest) -> List[Route]:
        logger.info(f"Route Search Started: {request.departure_station} -> {request.arrival_station}")
        
        if request.departure_station == request.arrival_station:
            raise DomainException("Departure and arrival stations cannot be the same.")

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
            
        await self.cache_port.set(cache_key, routes, ttl_seconds=self.cache_ttl)
        return routes

    async def get_route(self, route_id: str) -> Route:
        return Route(
            id=route_id,
            departure_station="MockDep",
            arrival_station="MockArr",
            railway_name="Mock Railway",
            total_duration="1h",
            total_fare=500,
            transfer_count=0,
            polyline="mock_polyline",
            stations=[]
        )
