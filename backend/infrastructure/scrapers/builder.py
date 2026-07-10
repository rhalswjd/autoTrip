from domain.route import Route
from domain.station import Station
from domain.timetable import Timetable, DepartureInfo
from infrastructure.scrapers.dtos import ScrapedRouteDTO, ScrapedTimetableDTO
from infrastructure.services.translation_service import TranslationService

class DomainBuilder:
    """
    Converts Intermediate DTOs into pure Domain entities.
    No translation logic or string formatting logic resides here.
    """
    def __init__(self, translation_service: TranslationService):
        self.translation_service = translation_service

    def build_route(self, dto: ScrapedRouteDTO) -> Route:
        dep_en = self.translation_service.get_english_name(dto.departure)
        arr_en = self.translation_service.get_english_name(dto.arrival)
        
        stations = []
        for s in dto.stations:
            # Use provided english name from site if any, else TranslationService
            s_name = s.name_en if s.name_en else self.translation_service.get_english_name(s.name_jp)
            stations.append(
                Station(
                    name=s_name, 
                    lat=s.lat, 
                    lng=s.lng,
                    platform=dto.platform_info,
                    has_midori_office=s.has_midori_madoguchi
                )
            )

        return Route(
            id=dto.id,
            departure_station=dep_en,
            arrival_station=arr_en,
            railway_name=dto.railway_name,
            total_duration=dto.total_time,
            total_fare=dto.fare,
            transfer_count=dto.transfers,
            polyline=dto.polyline_str,
            stations=stations
        )
        
    def build_timetable(self, dto: ScrapedTimetableDTO) -> Timetable:
        return Timetable(
            route_id=dto.route_id,
            first_train=dto.first_train,
            last_train=dto.last_train,
            departures=[DepartureInfo(time=e.time, train_name=e.train_name) for e in dto.entries]
        )
