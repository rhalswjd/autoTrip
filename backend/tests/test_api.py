from api.dependencies import get_scraper_port, get_cache_port, get_station_repository_port
from infrastructure.fakes.fake_scraper import FakeScraperAdapter
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from application.ports.station_repository_port import StationRepositoryPort

class FakeStationRepo(StationRepositoryPort):
    async def search_stations(self, query): return []

fake_scraper = FakeScraperAdapter()
fake_cache = FakeCacheAdapter()
fake_repo = FakeStationRepo()

def override_dependencies(app):
    app.dependency_overrides[get_scraper_port] = lambda: fake_scraper
    app.dependency_overrides[get_cache_port] = lambda: fake_cache
    app.dependency_overrides[get_station_repository_port] = lambda: fake_repo

def test_search_api(client):
    override_dependencies(client.app)
    response = client.get("/api/v1/search?departure_station=Tokyo&arrival_station=Kyoto")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "dummy_123"

def test_timetable_api(client):
    override_dependencies(client.app)
    response = client.get("/api/v1/routes/dummy_123/timetable")
    assert response.status_code == 200
    data = response.json()
    assert data["route_id"] == "dummy_123"
    assert data["first_train"] == "05:00"

def test_movements_api(client):
    override_dependencies(client.app)
    payload = {
        "route_id": "dummy_123",
        "departure_station": "Tokyo",
        "arrival_station": "Kyoto",
        "selected_departure_time": "10:00",
        "selected_arrival_time": "12:00"
    }
    response = client.post("/api/v1/movements", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["route_id"] == "dummy_123"
    assert data["search_mode"] == "ROUTE_ONLY"

def test_station_search_api(client):
    override_dependencies(client.app)
    response = client.get("/api/v1/stations/search?q=Tokyo")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
