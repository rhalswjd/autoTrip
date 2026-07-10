from domain.timetable import Timetable
from application.ports.scraper_port import ScraperPort

class TimetableService:
    def __init__(self, scraper_port: ScraperPort):
        self.scraper_port = scraper_port

    async def get_timetable(self, route_id: str) -> Timetable:
        return await self.scraper_port.get_timetable(route_id)
