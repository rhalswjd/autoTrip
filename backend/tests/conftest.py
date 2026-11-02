import pytest
import asyncio
import os
import httpx
from fastapi.testclient import TestClient
from main import create_app


@pytest.fixture(autouse=True)
def guard_external_test_io(monkeypatch):
    """Ordinary tests cannot use real HTTP; real Notion I/O is always forbidden."""
    async_send = httpx.AsyncHTTPTransport.handle_async_request
    sync_send = httpx.HTTPTransport.handle_request
    def check(request):
        if request.url.host == 'api.notion.com' or os.getenv('AUTOTRIP_LIVE_UI') != '1':
            pytest.fail('Real HTTP is disabled for this test; use fake transports. Real Notion I/O is never allowed.')
    async def guarded_async(transport, request):
        check(request)
        return await async_send(transport, request)
    def guarded_sync(transport, request):
        check(request)
        return sync_send(transport, request)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', guarded_async)
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', guarded_sync)

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
