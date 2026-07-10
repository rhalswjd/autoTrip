import pytest
from domain.search import SearchRequest
from domain.enums import SearchMode
from domain.route import Route
from application.services.search_service import SearchModeResolver, SearchService
from application.services.movement_service import MovementService
from infrastructure.fakes.fake_scraper import FakeScraperAdapter
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.fakes.fake_notion import FakeNotionAdapter

def test_search_mode_resolver():
    req1 = SearchRequest(departure_station="A", arrival_station="B")
    ctx1 = SearchModeResolver.resolve(req1)
    assert ctx1.search_mode == SearchMode.ROUTE_ONLY
    
    req2 = SearchRequest(departure_station="A", arrival_station="B", departure_time="10:00")
    ctx2 = SearchModeResolver.resolve(req2)
    assert ctx2.search_mode == SearchMode.ROUTE_WITH_TIME
    
    req3 = SearchRequest(departure_station="A", arrival_station="B", departure_time="10:00", departure_date="2024-10-01")
    ctx3 = SearchModeResolver.resolve(req3)
    assert ctx3.search_mode == SearchMode.ROUTE_WITH_DATETIME

@pytest.mark.asyncio
async def test_search_service_cache_hit_miss():
    scraper = FakeScraperAdapter()
    cache = FakeCacheAdapter()
    service = SearchService(scraper_port=scraper, cache_port=cache)
    
    req = SearchRequest(departure_station="Tokyo", arrival_station="Kyoto")
    
    routes_miss = await service.search(req)
    assert len(routes_miss) == 1
    assert routes_miss[0].id == "dummy_123"
    
    routes_hit = await service.search(req)
    assert routes_hit == routes_miss
    
@pytest.mark.asyncio
async def test_movement_service():
    cache = FakeCacheAdapter()
    notion = FakeNotionAdapter()
    service = MovementService(cache_port=cache, notion_port=notion)
    
    movement, url = await service.create_movement(
        route_id="r1", 
        departure_station="A", 
        arrival_station="B", 
        search_time=None, 
        search_date=None, 
        selected_departure_time="10:00", 
        selected_arrival_time="11:00"
    )
    
    assert movement.route.id == "r1"
    assert movement.selected_departure_time == "10:00"
    assert movement.search_context.search_mode == SearchMode.ROUTE_ONLY
