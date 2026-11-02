from typing import Protocol, List
from domain.route import Route
from domain.timetable import Timetable
from domain.station import Station

class ScraperException(Exception):
    """Raised when the scraper port encounters an unrecoverable external error."""
    pass


class UnsupportedTimetable(ScraperException):
    """The provider publishes no unambiguous station/direction for this identity."""

class ScraperPort(Protocol):
    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        ...
        
    async def get_timetable(
        self,
        route_id: str,
        departure: str = "",
        arrival: str = "",
        timetable_id: str | None = None,
        railway_name_jp: str = "",
        search_date: str | None = None,
        station_context: tuple[Station, Station] | None = None,
        not_before: str | None = None,
    ) -> Timetable:
        ...
