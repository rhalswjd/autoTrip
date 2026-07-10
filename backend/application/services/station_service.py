from typing import List
from application.ports.station_repository_port import StationRepositoryPort
from domain.station import Station

class StationService:
    def __init__(self, repository: StationRepositoryPort):
        self.repository = repository
        
    async def search(self, query: str) -> List[Station]:
        return await self.repository.search_stations(query)
