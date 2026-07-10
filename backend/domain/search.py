from pydantic import BaseModel, ConfigDict
from typing import Optional
from domain.enums import SearchMode

class SearchRequest(BaseModel):
    """
    Represents the raw input provided by the user.
    Strictly a DTO, contains no business logic or mode resolution.
    """
    model_config = ConfigDict(frozen=True)

    departure_station: str
    arrival_station: str
    departure_time: Optional[str] = None
    departure_date: Optional[str] = None


class SearchContext(BaseModel):
    """
    Represents the context of the user's search.
    Used by Movement and NotionMapper to understand the original intent.
    """
    model_config = ConfigDict(frozen=True)

    departure_station: str
    arrival_station: str
    departure_time: Optional[str]
    departure_date: Optional[str]
    search_mode: SearchMode
