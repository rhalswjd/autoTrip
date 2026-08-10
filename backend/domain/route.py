from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from domain.station import Station
from domain.planner import ScheduleCandidate, PlannerMetadata

class RouteSegment(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    segment_type: str  # 'train', 'bus', 'walk'
    railway_name: str
    railway_name_jp: str = ""
    duration: str = ""
    is_through: bool = False
    schedule_candidates: Optional[List[ScheduleCandidate]] = None

class Route(BaseModel):
    """
    Represents a pure, physical railway route.
    """
    model_config = ConfigDict(frozen=True)

    id: str
    departure_station: str
    arrival_station: str
    railway_name: str
    total_duration: str
    total_fare: int
    transfer_count: int
    polyline: str
    stations: List[Station] = []
    segments: List[RouteSegment] = []
    planner_metadata: Optional[PlannerMetadata] = None
