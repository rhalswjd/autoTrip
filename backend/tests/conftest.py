import pytest
import asyncio
from fastapi.testclient import TestClient
from main import create_app

@pytest.fixture
def movement_cache():
    from infrastructure.fakes.fake_cache import FakeCacheAdapter
    from domain.route import Route
    cache = FakeCacheAdapter()
    asyncio.run(cache.set("r1", Route(id="r1", departure_station="A", arrival_station="B",
        railway_name="Test railway", total_duration="1h", total_fare=1000,
        transfer_count=0, polyline="")))
    return cache

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
