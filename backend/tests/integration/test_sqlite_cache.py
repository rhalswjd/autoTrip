import pytest
import time
import os
from infrastructure.cache.sqlite_cache import SqliteCacheAdapter
from domain.route import Route
from domain.station import Station

@pytest.fixture
def cache():
    db_path = "test_cache.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    adapter = SqliteCacheAdapter(db_path=db_path)
    yield adapter
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.mark.asyncio
async def test_sqlite_cache_miss(cache):
    val = await cache.get("missing_key")
    assert val is None

@pytest.mark.asyncio
async def test_sqlite_cache_hit_and_domain_serialization(cache):
    route = Route(
        id="r1", departure_station="A", arrival_station="B",
        railway_name="Line", total_duration="1h", total_fare=100,
        transfer_count=0, polyline="", stations=[]
    )
    
    await cache.set("route_list", [route])
    
    cached_routes = await cache.get("route_list")
    assert cached_routes is not None
    assert len(cached_routes) == 1
    assert isinstance(cached_routes[0], Route)
    assert cached_routes[0].id == "r1"

@pytest.mark.asyncio
async def test_sqlite_cache_ttl_expiration(cache):
    await cache.set("short_lived", "value", ttl_seconds=0)
    time.sleep(0.1)  # Ensure expiry time passes
    
    val = await cache.get("short_lived")
    assert val is None

@pytest.mark.asyncio
async def test_sqlite_cache_delete(cache):
    await cache.set("to_delete", "val")
    await cache.delete("to_delete")
    
    assert await cache.get("to_delete") is None

@pytest.mark.asyncio
async def test_sqlite_cache_clear(cache):
    await cache.set("k1", "v1")
    await cache.set("k2", "v2")
    
    await cache.clear()
    
    assert await cache.get("k1") is None
    assert await cache.get("k2") is None
