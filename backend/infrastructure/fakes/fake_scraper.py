from typing import List
from application.ports.scraper_port import ScraperPort
from domain.route import Route
from domain.timetable import Timetable
from core.logger import logger

class FakeScraperAdapter(ScraperPort):
    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        logger.info(f"[FakeScraper] Searching routes from {departure} to {arrival}")
        dummy_route = Route(
            id="dummy_123",
            departure_station=departure,
            arrival_station=arrival,
            railway_name="Fake JR",
            total_duration="1h",
            total_fare=1000,
            transfer_count=0,
            polyline="fake_polyline",
            stations=[]
        )
        return [dummy_route]
        
    async def get_timetable(self, route_id: str) -> Timetable:
        return Timetable(
            route_id=route_id,
            first_train="05:00",
            last_train="23:30",
            departures=[]
        )
