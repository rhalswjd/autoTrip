from pydantic import BaseModel, ConfigDict
from typing import List

class DepartureInfo(BaseModel):
    """
    Represents a single departure entry in a timetable.
    Supports future expansion (e.g., train type, specific platform).
    """
    model_config = ConfigDict(frozen=True)
    
    time: str
    train_name: str

class Timetable(BaseModel):
    """
    Represents the full schedule for a specific Route.
    """
    model_config = ConfigDict(frozen=True)

    route_id: str
    first_train: str
    last_train: str
    departures: List[DepartureInfo]
