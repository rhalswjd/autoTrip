from pydantic import BaseModel, ConfigDict, computed_field
from typing import List, Optional
from enum import Enum
from domain.station import Station
from domain.planner import ScheduleCandidate, PlannerMetadata
from domain.journey import PassengerLeg, passenger_legs

class SeatPreference(str, Enum):
    RESERVED = "RESERVED"
    NON_RESERVED = "NON_RESERVED"
    GREEN = "GREEN"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class RouteSegment(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    segment_type: str  # 'train', 'bus', 'walk'
    railway_name: str
    railway_name_jp: str = ""
    duration: str = ""
    departure_time: str = ""
    arrival_time: str = ""
    railway_id: str = ""
    is_through: bool = False
    schedule_candidates: Optional[List[ScheduleCandidate]] = None
    departure_platform: Optional[str] = None
    base_fare: Optional[int] = None
    express_fare: Optional[int] = None
    has_seat_selection: bool = False
    selected_seat: Optional[SeatPreference] = None

class FareBreakdown(BaseModel):
    """Source-proven quote; seat basis is not a separate seat surcharge."""
    base: Optional[int] = None
    surcharge: Optional[int] = None
    seat_supplement: Optional[int] = None
    total: Optional[int] = None
    seat_basis: str = ''


class Route(BaseModel):
    """
    Represents a pure, physical railway route.
    """
    model_config = ConfigDict(frozen=True)

    id: str
    departure_station: str
    arrival_station: str
    railway_name: str
    departure_time: str = ""
    arrival_time: str = ""
    total_duration: str
    departure_datetime: str = ""
    arrival_datetime: str = ""
    onboard_duration: str = ""
    non_riding_duration: str = ""
    total_fare: int
    transfer_count: int
    polyline: str
    search_date: Optional[str] = None
    search_time: Optional[str] = None
    search_source: Optional[str] = None
    source_rank: Optional[int] = None
    stations: List[Station] = []
    segments: List[RouteSegment] = []
    planner_metadata: Optional[PlannerMetadata] = None
    family_key: str = ""
    categories: List[str] = []
    waiting_duration: str = ""
    fare_status: str = "indicative"
    fare_breakdown: Optional[FareBreakdown] = None
    timing_status: str = "indicative"
    result_kind: str = 'requested'
    alternative_reason: str = ''
    evidence_url: str = ''

    @computed_field
    @property
    def passenger_legs(self) -> List[PassengerLeg]:
        return passenger_legs(self)
