import pytest
import os
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository
from scripts.seed_station_db import seed_database

@pytest.fixture
def repo():
    db_path = "test_stations_api.db"
    csv_path = os.path.join(os.path.dirname(__file__), "data", "test_station.csv")
    
    # Generate test DB from test CSV
    seed_database(csv_path, db_path)
    
    r = SqliteStationRepository(db_path=db_path)
    yield r
    
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.mark.asyncio
async def test_search_empty(repo):
    res = await repo.search_stations("")
    assert len(res) == 0

@pytest.mark.asyncio
async def test_search_prefix(repo):
    res = await repo.search_stations("Osa")
    assert len(res) > 0
    assert any(s.name == "Osaka" for s in res)

@pytest.mark.asyncio
async def test_search_substring(repo):
    res = await repo.search_stations("saka")
    assert len(res) > 0
    assert any(s.name == "Osaka" for s in res)

@pytest.mark.asyncio
async def test_search_english(repo):
    res = await repo.search_stations("Kyoto")
    assert len(res) == 1
    assert res[0].name == "Kyoto"

@pytest.mark.asyncio
async def test_search_japanese(repo):
    res = await repo.search_stations("京都")
    assert len(res) == 1
    assert res[0].name == "Kyoto"

@pytest.mark.asyncio
async def test_search_no_result(repo):
    res = await repo.search_stations("Seoul")
    assert len(res) == 0
