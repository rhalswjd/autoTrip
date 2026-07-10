import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.search import SearchRequest
from application.services.search_service import SearchService
from application.ports.scraper_port import ScraperException
from infrastructure.scrapers.real_scraper import RealScraperAdapter
from infrastructure.cache.sqlite_cache import SqliteCacheAdapter
from infrastructure.exceptions import HttpClientException, HtmlParsingException
from core.exceptions import DomainException
import os

@pytest.fixture
def cache():
    db_path = "test_integration_cache.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    adapter = SqliteCacheAdapter(db_path=db_path)
    yield adapter
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def real_scraper():
    return RealScraperAdapter()

@pytest.fixture
def search_service(real_scraper, cache):
    return SearchService(scraper_port=real_scraper, cache_port=cache)

@pytest.mark.asyncio
async def test_search_integration_success_cache_miss_and_hit(search_service, real_scraper, monkeypatch):
    valid_html = '<html><div class="eki_name">Osaka</div><div class="icon_midori"></div><div class="platform_info">1</div></html>'
    mock_get = AsyncMock(return_value=valid_html)
    monkeypatch.setattr(real_scraper.http_client, "get", mock_get)
    
    req = SearchRequest(departure_station="Osaka", arrival_station="Kyoto")
    
    routes1 = await search_service.search(req)
    assert len(routes1) == 1
    assert routes1[0].departure_station == "Osaka"
    mock_get.assert_called_once()
    
    mock_get.reset_mock()
    routes2 = await search_service.search(req)
    assert len(routes2) == 1
    assert routes2[0].departure_station == "Osaka"
    mock_get.assert_not_called()

@pytest.mark.asyncio
async def test_search_integration_no_result(search_service, real_scraper, monkeypatch):
    no_route_html = '<html></html>'
    mock_get = AsyncMock(return_value=no_route_html)
    monkeypatch.setattr(real_scraper.http_client, "get", mock_get)
    
    req = SearchRequest(departure_station="Nowhere", arrival_station="NowhereElse")
    routes = await search_service.search(req)
    assert len(routes) == 0

@pytest.mark.asyncio
async def test_search_integration_http_failure(search_service, real_scraper, monkeypatch):
    mock_get = AsyncMock(side_effect=HttpClientException("Network Timeout"))
    monkeypatch.setattr(real_scraper.http_client, "get", mock_get)
    
    req = SearchRequest(departure_station="Osaka", arrival_station="Kyoto")
    with pytest.raises(ScraperException):
        await search_service.search(req)

@pytest.mark.asyncio
async def test_search_integration_parser_failure(search_service, real_scraper, monkeypatch):
    mock_parse = MagicMock(side_effect=HtmlParsingException("Invalid DOM structure"))
    monkeypatch.setattr(real_scraper.parser, "parse_routes", mock_parse)
    
    mock_get = AsyncMock(return_value="<html></html>")
    monkeypatch.setattr(real_scraper.http_client, "get", mock_get)
    
    req = SearchRequest(departure_station="Osaka", arrival_station="Kyoto")
    with pytest.raises(ScraperException):
        await search_service.search(req)

@pytest.mark.asyncio
async def test_search_integration_domain_exception(search_service):
    req = SearchRequest(departure_station="Osaka", arrival_station="Osaka")
    with pytest.raises(DomainException):
        await search_service.search(req)
