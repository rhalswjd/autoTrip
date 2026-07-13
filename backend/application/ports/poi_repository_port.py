from abc import ABC, abstractmethod
from typing import List
from domain.poi import Poi

class PoiRepositoryPort(ABC):
    @abstractmethod
    def search_pois(self, query: str) -> List[Poi]:
        pass
