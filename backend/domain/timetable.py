from pydantic import BaseModel, ConfigDict, computed_field, model_validator
from domain.platform import PlatformStatus
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
    departure_datetime: str = ''
    arrival_datetime: str = ''
    arrival_platform: str = ""
    platform_status: PlatformStatus = PlatformStatus.LOOKUP_FAILED
    arrival_platform_status: PlatformStatus = PlatformStatus.LOOKUP_FAILED
    source: str = ""
    source_url: str = ""
    train_number: str = ""
    base_fare: int | None = None
    express_fare: int | None = None
    fare_status: str = "unknown"

    @model_validator(mode='before')
    @classmethod
    def legacy_platform_values(cls, values):
        # Concrete legacy values can be retained. A legacy blank has no omission
        # provenance and must never be upgraded to SOURCE_NOT_PROVIDED.
        if isinstance(values, dict):
            values = dict(values)
            for field in ('platform', 'arrival_platform'):
                if field + '_status' not in values and values.get(field):
                    values[field + '_status'] = PlatformStatus.KNOWN
        return values

class Timetable(BaseModel):
    """
    Represents the full schedule for a specific Route, divided by day type.
    """
    model_config = ConfigDict(frozen=True)

    route_id: str
    search_date: str = ''
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

    @computed_field
    @property
    def availability(self) -> str:
        return {'available': 'SUPPORTED', 'unsupported': 'UNSUPPORTED'}.get(self.status, 'PROVIDER_ERROR')

    def selected_departures(self) -> List[DepartureInfo]:
        return list(getattr(self, self.selected_calendar.value))
