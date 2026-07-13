import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
from application.services.search_service import SearchService
from domain.search import SearchRequest

async def main():
    scraper = YahooTransitAdapter()
    from infrastructure.fakes.fake_cache import FakeCacheAdapter
    cache = FakeCacheAdapter()
    repo = SqliteStationRepository(db_path="/app/backend/autotrip_stations.db")
    service = SearchService(scraper, cache, repo)
    
    req = SearchRequest(departure_station="Shin-Osaka", arrival_station="Nagoya")
    routes = await service.search(req)
    for i, r in enumerate(routes):
        print(f"Route {i}: {r.departure_station} -> {r.arrival_station}, Duration: {r.total_duration}, Railway: {r.railway_name}")
        
asyncio.run(main())
