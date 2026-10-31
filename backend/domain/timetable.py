from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import date as Date
from enum import Enum
import jpholiday


class CalendarType(str, Enum):
    WEEKDAY = "weekday"
    SATURDAY = "saturday"
    HOLIDAY = "holiday"


def calendar_type_for_date(search_date: str | None) -> CalendarType:
    """Resolve the operating calendar, including national/substitute holidays."""
    if not search_date:
        return CalendarType.WEEKDAY
    try:
        parsed_date = Date.fromisoformat(search_date)
        weekday = parsed_date.weekday()
    except ValueError as exc:
        raise ValueError(
            f"Invalid route search_date {search_date!r}; expected YYYY-MM-DD"
        ) from exc
    if weekday == 6 or jpholiday.is_holiday(parsed_date):
        return CalendarType.HOLIDAY
    if weekday == 5:
        return CalendarType.SATURDAY
    return CalendarType.WEEKDAY

class DepartureInfo(BaseModel):
    """
    Represents a single departure entry in a timetable.
    Supports future expansion (e.g., train type, specific platform).
    """
    model_config = ConfigDict(frozen=True)
    
    id: str
    time: str
    arrival_time: str = ""
    train_name: str
    train_type: str = ""
    platform: str = ""
    direction: str = ""
    metadata: dict = {}
    operating_date: str = ""
    arrival_platform: str = ""
    source: str = ""
    source_url: str = ""
    train_number: str = ""
    base_fare: int | None = None
    express_fare: int | None = None
    fare_status: str = "unknown"

class Timetable(BaseModel):
    """
    Represents the full schedule for a specific Route, divided by day type.
    """
    model_config = ConfigDict(frozen=True)

    route_id: str
    selected_calendar: CalendarType = CalendarType.WEEKDAY
    weekday: List[DepartureInfo] = []
    saturday: List[DepartureInfo] = []
    holiday: List[DepartureInfo] = []
    source: str = ""
    source_url: str = ""
    status: str = "available"
    message: str = ""
    complete: bool = True
    next_cursor: int | None = None
    total_candidates: int = 0

    def selected_departures(self) -> List[DepartureInfo]:
        return list(getattr(self, self.selected_calendar.value))
