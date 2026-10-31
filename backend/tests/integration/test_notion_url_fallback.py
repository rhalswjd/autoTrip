import pytest
from fastapi.testclient import TestClient
from main import app
from api.dependencies import get_movement_service
from unittest.mock import AsyncMock

client = TestClient(app)

@pytest.fixture
def mock_movement_service():
    service = AsyncMock()
    # Mock create_movement to return a dummy movement and empty notion result
    
    class DummyRoute:
        id = "route_123"
        departure_station = "A"
        arrival_station = "B"
        
    class DummyContext:
        class SearchMode:
            value = "ROUTE_WITH_TIME"
        search_mode = SearchMode()

    class DummyMovement:
        route = DummyRoute()
        selected_departure_time = "10:00"
        selected_arrival_time = "11:00"
        search_context = DummyContext()
        
    service.create_movement.return_value = (DummyMovement(), {"notion_url": "http://notion.url"})
    return service

def test_priority_notion_page_url(mock_movement_service):
    app.dependency_overrides[get_movement_service] = lambda: mock_movement_service
    
    # Send both notion_page_url and target_page_id
    res = client.post("/api/v1/movements", json={
        "route_id": "route_123",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "11:00",
        "departure_station": "A",
        "arrival_station": "B",
        "notion_page_url": "https://www.notion.so/UrlTest-11111111111111111111111111111111",
        "target_page_id": "00000000000000000000000000000000"
    })
    
    assert res.status_code == 200
    
    # Check that create_movement was called with the URL's extracted ID
    call_args = mock_movement_service.create_movement.call_args[1]
    assert call_args["target_page_id"] == "11111111111111111111111111111111"
    
def test_fallback_target_page_id(mock_movement_service):
    app.dependency_overrides[get_movement_service] = lambda: mock_movement_service
    
    res = client.post("/api/v1/movements", json={
        "route_id": "route_123",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "11:00",
        "departure_station": "A",
        "arrival_station": "B",
        "target_page_id": "11111111111111111111111111111111"
    })
    
    assert res.status_code == 200
    call_args = mock_movement_service.create_movement.call_args[1]
    assert call_args["target_page_id"] == "11111111111111111111111111111111"
    
def test_fallback_empty(mock_movement_service):
    app.dependency_overrides[get_movement_service] = lambda: mock_movement_service
    
    res = client.post("/api/v1/movements", json={
        "route_id": "route_123",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "11:00",
        "departure_station": "A",
        "arrival_station": "B"
    })
    
    assert res.status_code == 200
    call_args = mock_movement_service.create_movement.call_args[1]
    assert call_args["target_page_id"] is None
