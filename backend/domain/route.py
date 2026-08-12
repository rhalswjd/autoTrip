from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from enum import Enum
from domain.station import Station
from domain.planner import ScheduleCandidate, PlannerMetadata

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
    is_through: bool = False
    schedule_candidates: Optional[List[ScheduleCandidate]] = None
    departure_platform: Optional[str] = None
    base_fare: Optional[int] = None
    express_fare: Optional[int] = None
    has_seat_selection: bool = False
    selected_seat: Optional[SeatPreference] = None

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
    total_fare: int
    transfer_count: int
    polyline: str
    stations: List[Station] = []
    segments: List[RouteSegment] = []
    planner_metadata: Optional[PlannerMetadata] = None
