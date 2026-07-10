from typing import Protocol, List
from domain.route import Route
from domain.timetable import Timetable

class ScraperException(Exception):
    """Raised when the scraper port encounters an unrecoverable external error."""
    pass

class ScraperPort(Protocol):
    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        ...
        
    async def get_timetable(self, route_id: str) -> Timetable:
        ...
