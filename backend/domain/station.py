from pydantic import BaseModel, ConfigDict
from typing import Optional

class Station(BaseModel):
    """Represents a physical railway station with coordinates and facilities."""
    model_config = ConfigDict(frozen=True)
    
    id: str = ""
    name: str = ""
    name_jp: str = ""
    lat: float = 0.0
    lng: float = 0.0
    platform: Optional[str] = None
    has_midori_office: bool = False
