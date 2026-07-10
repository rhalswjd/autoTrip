import pytest
from fastapi.testclient import TestClient
from main import app
from application.services.movement_service import MovementService
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.fakes.fake_notion import FakeNotionAdapter
from application.ports.notion_port import NotionException
from api.dependencies import get_movement_service, get_notion_port, get_cache_port

client = TestClient(app)

@pytest.mark.asyncio
async def test_movement_service_success():
    cache = FakeCacheAdapter()
    notion = FakeNotionAdapter(should_fail=False)
    service = MovementService(cache_port=cache, notion_port=notion)
    
    movement, url = await service.create_movement(
        route_id="r1", departure_station="A", arrival_station="B",
        search_time=None, search_date=None,
        selected_departure_time="10:00", selected_arrival_time="11:00"
    )
    
    assert url == "https://notion.so/fake_movement_url"
    assert movement.route.id == "r1"

@pytest.mark.asyncio
async def test_movement_service_notion_failure():
    cache = FakeCacheAdapter()
    notion = FakeNotionAdapter(should_fail=True)
    service = MovementService(cache_port=cache, notion_port=notion)
    
    with pytest.raises(NotionException):
        await service.create_movement(
            route_id="r1", departure_station="A", arrival_station="B",
            search_time=None, search_date=None,
            selected_departure_time="10:00", selected_arrival_time="11:00"
        )

def test_create_movement_api_success():
    fake_notion = FakeNotionAdapter(should_fail=False)
    fake_cache = FakeCacheAdapter()
    app.dependency_overrides[get_notion_port] = lambda: fake_notion
    app.dependency_overrides[get_cache_port] = lambda: fake_cache
    
    payload = {
        "route_id": "r1",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "11:00",
        "departure_station": "Osaka",
        "arrival_station": "Kyoto"
    }
    
    res = client.post("/api/v1/movements", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["notion_url"] == "https://notion.so/fake_movement_url"
    
    app.dependency_overrides.clear()

def test_create_movement_api_notion_failure_via_global_handler():
    fake_notion = FakeNotionAdapter(should_fail=True)
    fake_cache = FakeCacheAdapter()
    app.dependency_overrides[get_notion_port] = lambda: fake_notion
    app.dependency_overrides[get_cache_port] = lambda: fake_cache
    
    payload = {
        "route_id": "r1",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "11:00",
        "departure_station": "Osaka",
        "arrival_station": "Kyoto"
    }
    
    res = client.post("/api/v1/movements", json=payload)
    # Global exception handler should catch it and return 502
    assert res.status_code == 502
    assert "detail" in res.json()
    assert "Fake Notion Failure" in res.json()["detail"]
    
    app.dependency_overrides.clear()
