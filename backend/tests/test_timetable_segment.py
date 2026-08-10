import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import httpx
from main import app
from domain.route import Route, RouteSegment
from domain.station import Station
from domain.timetable import Timetable, DepartureInfo
from application.ports.scraper_port import ScraperException

client = TestClient(app)

def create_mock_route(route_id="route_123"):
    return Route(
        id=route_id,
        departure_station="Shin-Osaka",
        arrival_station="Hagi",
        railway_name="Mixed",
        total_duration="4h",
        total_fare=12000,
        transfer_count=1,
        polyline="",
        stations=[
            Station(id="st1", name="Shin-Osaka", name_jp="新大阪"),
            Station(id="st2", name="Shin-Yamaguchi", name_jp="新山口"),
            Station(id="st3", name="Hagi", name_jp="萩")
        ],
        segments=[
            RouteSegment(segment_type="train", railway_name="Shinkansen"),
            RouteSegment(segment_type="train", railway_name="Super Oki")
        ]
    )

def create_mock_timetable(route_id="route_123"):
    return Timetable(
        route_id=route_id,
        weekday=[
            DepartureInfo(id="dep1", time="08:00", train_name="Nozomi", train_type="Shinkansen", platform="21", direction="Hakata", metadata={})
        ],
        saturday=[],
        holiday=[]
    )

@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get.return_value = create_mock_route()
    return cache

@pytest.fixture
def mock_scraper():
    scraper = AsyncMock()
    scraper.get_timetable.return_value = create_mock_timetable()
    return scraper

def override_dependencies(mock_cache, mock_scraper):
    from application.services.timetable_service import TimetableService
    from api.dependencies import get_timetable_service
    app.dependency_overrides[get_timetable_service] = lambda: TimetableService(scraper_port=mock_scraper, cache_port=mock_cache)

def teardown_dependencies():
    app.dependency_overrides.clear()

def test_get_entire_timetable(mock_cache, mock_scraper):
    """TEST 1: 기존 전체 Route timetable API가 기존처럼 동작한다."""
    override_dependencies(mock_cache, mock_scraper)
    
    response = client.get("/api/v1/routes/route_123/timetable")
    assert response.status_code == 200
    
    # Assert scraper called with first segment and dynamic timetable lookup
    mock_scraper.get_timetable.assert_called_with("route_123", "新大阪", "新山口", timetable_id=None, railway_name_jp="")
    
    teardown_dependencies()

def test_get_segment_timetable_0(mock_cache, mock_scraper):
    """TEST 2: segment_index=0으로 요청하면 stations[0] -> stations[1] 구간을 조회한다."""
    override_dependencies(mock_cache, mock_scraper)
    
    response = client.get("/api/v1/routes/route_123/segments/0/timetable?timetable_id=12345")
    assert response.status_code == 200
    
    mock_scraper.get_timetable.assert_called_with("route_123", "新大阪", "新山口", timetable_id="12345", railway_name_jp="")
    
    teardown_dependencies()

def test_get_segment_timetable_1(mock_cache, mock_scraper):
    """TEST 3: segment_index=1이면 stations[1] -> stations[2] 구간을 조회한다."""
    override_dependencies(mock_cache, mock_scraper)
    
    response = client.get("/api/v1/routes/route_123/segments/1/timetable?timetable_id=67890")
    assert response.status_code == 200
    
    mock_scraper.get_timetable.assert_called_with("route_123", "新山口", "萩", timetable_id="67890", railway_name_jp="")
    
    teardown_dependencies()

def test_get_segment_invalid_index(mock_cache, mock_scraper):
    """TEST 4: 잘못된 segment_index에 대해 명확한 에러가 반환된다."""
    override_dependencies(mock_cache, mock_scraper)
    
    response = client.get("/api/v1/routes/route_123/segments/5/timetable")
    assert response.status_code == 400
    assert "Invalid segment_index" in response.json()["detail"]
    
    teardown_dependencies()

def test_get_segment_missing_timetable_id_raises_value_error():
    """TEST 6 & 7: 기존 hardcoded timetable_id가 무조건 사용되지 않는지 검증 및 에러처리."""
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    scraper = JROdekakeTimetableScraper()
    
    import asyncio
    with pytest.raises(ValueError, match="동적 탐색 불가"):
        asyncio.run(scraper.get_timetable("route_123", "Shin-Osaka", "Kyoto", timetable_id=None))

def test_scraper_failure_propagation(mock_cache, mock_scraper):
    """TEST 8: Scraper가 실패했을 때 적절한 예외가 API까지 전달된다."""
    mock_scraper.get_timetable.side_effect = ScraperException("Scraper failed")
    override_dependencies(mock_cache, mock_scraper)
    
    response = client.get("/api/v1/routes/route_123/segments/0/timetable?timetable_id=12345")
    assert response.status_code == 502  # Global exception handler maps ScraperException to 502
    
    teardown_dependencies()
