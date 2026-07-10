from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ScrapedStationDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    name_jp: str
    name_en: Optional[str] = None
    lat: float
    lng: float
    has_midori_madoguchi: bool = False

class ScrapedRouteDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    departure: str
    arrival: str
    railway_name: str
    total_time: str
    fare: int
    transfers: int
    polyline_str: str
    platform_info: Optional[str] = None
    stations: List[ScrapedStationDTO]
    
class ScrapedTimetableEntryDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    time: str
    train_name: str
    
class ScrapedTimetableDTO(BaseModel):
    model_config = ConfigDict(frozen=True)
    route_id: str
    first_train: str
    last_train: str
    entries: List[ScrapedTimetableEntryDTO]
