from pydantic import BaseModel, ConfigDict, Field
from domain.station_identity import qualified_station_name
from typing import Optional

class Station(BaseModel):
    """Represents a physical railway station with coordinates and facilities."""
    model_config = ConfigDict(frozen=True)
    
    id: str = ""
    name: str = ""
    display_name_en: str = ""
    name_jp: str = ""
    prefecture: str = ""
    railway_company: str = ""
    lat: float = 0.0
    lng: float = 0.0
    platform: Optional[str] = None
    has_midori_office: bool = False
    provider_ids: dict[str, str] = Field(default_factory=dict)
    provider_aliases: dict[str, str] = Field(default_factory=dict)

    def identity_key(self) -> tuple[str, str, str]:
        return self.id, self.prefecture, qualified_station_name(self.name_jp or self.name)
