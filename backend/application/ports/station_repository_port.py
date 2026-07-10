from typing import Protocol, List
from domain.station import Station

class StationRepositoryPort(Protocol):
    """Interface for querying station information."""
    async def search_stations(self, query: str) -> List[Station]:
        ...
