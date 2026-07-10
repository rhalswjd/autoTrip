from pydantic import BaseModel, ConfigDict
from typing import List
from domain.station import Station

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
