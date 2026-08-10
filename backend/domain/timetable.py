from pydantic import BaseModel, ConfigDict
from typing import List

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

class Timetable(BaseModel):
    """
    Represents the full schedule for a specific Route, divided by day type.
    """
    model_config = ConfigDict(frozen=True)

    route_id: str
    weekday: List[DepartureInfo] = []
    saturday: List[DepartureInfo] = []
    holiday: List[DepartureInfo] = []
