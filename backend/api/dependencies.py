from fastapi import Request, Depends
from application.ports.scraper_port import ScraperPort
from application.ports.notion_port import NotionPort
from application.ports.cache_port import CachePort
from application.ports.station_repository_port import StationRepositoryPort

from infrastructure.fakes.fake_scraper import FakeScraperAdapter
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from infrastructure.fakes.fake_notion import FakeNotionAdapter
from infrastructure.notion.notion_adapter import RealNotionAdapter
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.cache.sqlite_cache import SqliteCacheAdapter
from infrastructure.repositories.sqlite_station_repository import SqliteStationRepository

from application.services.search_service import SearchService
from application.services.timetable_service import TimetableService
from application.services.movement_service import MovementService
from application.services.station_service import StationService
from application.services.planner_query_service import PlannerQueryService
from application.ports.timetable_source_port import TimetableSourcePort

from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
from infrastructure.adapters.yahoo_timetable_source import YahooTimetableSource

from core.config import settings

# --- Configuration Toggle for Dependency Injection ---
USE_REAL_SCRAPER = settings.use_real_scraper
USE_REAL_NOTION = settings.use_real_notion
USE_SQLITE_CACHE = settings.use_sqlite_cache


# Dependency instantiation (Using singletons)
fake_scraper = FakeScraperAdapter()
fake_notion = FakeNotionAdapter()
real_notion = RealNotionAdapter()
fake_cache = FakeCacheAdapter()
sqlite_cache = SqliteCacheAdapter(db_path=settings.sqlite_cache_path)
sqlite_station_repo = SqliteStationRepository(db_path=settings.sqlite_station_db_path)

from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper

def get_scraper_port() -> ScraperPort:
    if USE_REAL_SCRAPER:
        timetable_scraper_facade = YahooTimetableScraper()
        return YahooTransitAdapter(timetable_scraper_facade)
    return fake_scraper

def get_notion_port() -> NotionPort:
    return real_notion if USE_REAL_NOTION else fake_notion

def get_cache_port() -> CachePort:
    return sqlite_cache if USE_SQLITE_CACHE else fake_cache

def get_station_repository_port() -> StationRepositoryPort:
    return sqlite_station_repo

def get_search_service(
    scraper: ScraperPort = Depends(get_scraper_port),
    cache: CachePort = Depends(get_cache_port),
    station_repo: StationRepositoryPort = Depends(get_station_repository_port)
) -> SearchService:
    return SearchService(
        scraper_port=scraper, 
        cache_port=cache,
        station_repo=station_repo,
        cache_ttl=settings.cache_ttl_seconds
    )

def get_timetable_service(
    scraper: ScraperPort = Depends(get_scraper_port),
    cache: CachePort = Depends(get_cache_port)
) -> TimetableService:
    return TimetableService(scraper_port=scraper, cache_port=cache)

def get_movement_service(
    cache: CachePort = Depends(get_cache_port),
    notion: NotionPort = Depends(get_notion_port),
    search_service: SearchService = Depends(get_search_service)
) -> MovementService:
    return MovementService(cache_port=cache, notion_port=notion, search_service=search_service)

def get_station_service(
    repo: StationRepositoryPort = Depends(get_station_repository_port)
) -> StationService:
    return StationService(repository=repo)

from functools import lru_cache

@lru_cache
def get_timetable_source_port() -> TimetableSourcePort:
    timetable_scraper_facade = JROdekakeTimetableScraper()
    return YahooTimetableSource(timetable_scraper_facade)

def get_planner_query_service(
    source: TimetableSourcePort = Depends(get_timetable_source_port)
) -> PlannerQueryService:
    return PlannerQueryService(timetable_source=source)
