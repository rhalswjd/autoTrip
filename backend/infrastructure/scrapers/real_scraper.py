from typing import List
from application.ports.scraper_port import ScraperPort, ScraperException
from domain.route import Route
from domain.timetable import Timetable
from infrastructure.scrapers.http_client import HttpClient
from infrastructure.scrapers.parser import RealHtmlParser
from infrastructure.scrapers.builder import DomainBuilder
from infrastructure.services.translation_service import TranslationService
from infrastructure.exceptions import InfrastructureException
from core.config import settings

class RealScraperAdapter(ScraperPort):
    """
    Implements ScraperPort via HttpClient -> Parser -> Builder pipeline.
    """
    def __init__(self):
        self.http_client = HttpClient()
        self.parser = RealHtmlParser()
        self.builder = DomainBuilder(translation_service=TranslationService())
        self.base_url = settings.scraper_base_url
        
    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        try:
            # 1. Fetch HTML
            html = await self.http_client.get(self.base_url, params={"q": departure})
            
            # 2. Parse HTML -> Intermediate DTO
            dtos = self.parser.parse_routes(html)
            
            # 3. Build DTO -> Domain Model
            return [self.builder.build_route(dto) for dto in dtos]
        except InfrastructureException as e:
            raise ScraperException(f"Route search failed: {str(e)}") from e
        
    async def get_timetable(self, route_id: str) -> Timetable:
        try:
            # 1. Fetch HTML
            html = await self.http_client.get(f"{self.base_url}timetable", params={"id": route_id})
            
            # 2. Parse HTML -> Intermediate DTO
            dto = self.parser.parse_timetable(html, route_id)
            
            # 3. Build DTO -> Domain Model
            return self.builder.build_timetable(dto)
        except InfrastructureException as e:
            raise ScraperException(f"Timetable search failed: {str(e)}") from e
