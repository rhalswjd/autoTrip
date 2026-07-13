import pytest
from unittest.mock import patch
from domain.search import SearchRequest
from application.services.search_service import SearchService
from application.services.movement_service import MovementService
from infrastructure.fakes.fake_scraper import FakeScraperAdapter
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.fakes.fake_notion import FakeNotionAdapter
from application.ports.notion_port import NotionException

@pytest.mark.asyncio
@patch("application.services.search_service.logger")
async def test_search_service_logging(mock_logger):
    scraper = FakeScraperAdapter()
    cache = FakeCacheAdapter()
    from application.ports.station_repository_port import StationRepositoryPort
    class FakeStationRepo(StationRepositoryPort):
        async def search_stations(self, query): return []
    service = SearchService(scraper_port=scraper, cache_port=cache, station_repo=FakeStationRepo())
    
    req = SearchRequest(departure_station="Tokyo", arrival_station="Kyoto")
    
    # 1. Miss
    await service.search(req)
    mock_logger.info.assert_any_call("Route Search Started: Tokyo -> Kyoto")
    mock_logger.info.assert_any_call("Cache Miss for Tokyo -> Kyoto")
    mock_logger.info.assert_any_call("Scraper Started: Tokyo (Tokyo) -> Kyoto (Kyoto)")
    mock_logger.info.assert_any_call("Scraper Finished: Found 1 routes")
    
    # 2. Hit
    mock_logger.reset_mock()
    await service.search(req)
    mock_logger.info.assert_any_call("Route Search Started: Tokyo -> Kyoto")
    mock_logger.info.assert_any_call("Cache Hit for Tokyo -> Kyoto")


@pytest.mark.asyncio
@patch("application.services.movement_service.logger")
async def test_movement_service_logging_success(mock_logger):
    cache = FakeCacheAdapter()
    notion = FakeNotionAdapter(should_fail=False)
    service = MovementService(cache_port=cache, notion_port=notion)
    
    await service.create_movement(
        route_id="r1", departure_station="A", arrival_station="B",
        search_time=None, search_date=None,
        selected_departure_time="10:00", selected_arrival_time="11:00"
    )
    
    mock_logger.info.assert_any_call("Movement Created: r1 (A -> B)")
    mock_logger.info.assert_any_call("Notion Save Started")
    mock_logger.info.assert_any_call("Notion Save Success")

@pytest.mark.asyncio
@patch("application.services.movement_service.logger")
async def test_movement_service_logging_failure(mock_logger):
    cache = FakeCacheAdapter()
    notion = FakeNotionAdapter(should_fail=True)
    service = MovementService(cache_port=cache, notion_port=notion)
    
    with pytest.raises(NotionException):
        await service.create_movement(
            route_id="r1", departure_station="A", arrival_station="B",
            search_time=None, search_date=None,
            selected_departure_time="10:00", selected_arrival_time="11:00"
        )
    
    mock_logger.info.assert_any_call("Movement Created: r1 (A -> B)")
    mock_logger.info.assert_any_call("Notion Save Started")
    # Using substring match for error because exception string might vary
    error_call = mock_logger.error.call_args[0][0]
    assert "Notion Save Failed" in error_call
