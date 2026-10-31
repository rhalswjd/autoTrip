import pytest
from infrastructure.scrapers.real_scraper import RealScraperAdapter
from infrastructure.exceptions import HttpClientException
from application.ports.scraper_port import ScraperException

@pytest.mark.asyncio
async def test_real_scraper_http_client_failure(monkeypatch):
    scraper = RealScraperAdapter()
    
    # Mock http_client to always raise exception to avoid real network hit in CI
    async def mock_get(*args, **kwargs):
        raise HttpClientException("Mocked network failure")
        
    monkeypatch.setattr(scraper.http_client, "get", mock_get)
    
    with pytest.raises(ScraperException):
        await scraper.search_routes("Osaka", "Kyoto")
