from domain.timetable import Timetable, calendar_type_for_date
from application.ports.scraper_port import ScraperPort

from application.ports.cache_port import CachePort
from application.services.passenger_topology import PassengerTopologyClassifier
from core.logger import logger
from domain.journey import canonical_station, service_family
from domain.timetable import Timetable as TimetableModel
import hashlib

class TimetableService:
    def __init__(self, scraper_port: ScraperPort, cache_port: CachePort = None):
        self.scraper_port = scraper_port
        self.cache_port = cache_port
        self.topology_classifier = PassengerTopologyClassifier()

    async def get_leg_timetable(self, route_id: str, leg_index: int, cursor: int = 0) -> Timetable:
        route = await self.cache_port.get(route_id) if self.cache_port else None
        if not route:
            raise ValueError(f"Route {route_id} not found; search again")
        if leg_index < 0 or leg_index >= len(route.passenger_legs):
            raise ValueError(f"Invalid leg_index {leg_index}")
        leg = route.passenger_legs[leg_index]
        if leg.segment_type == "walk":
            raise ValueError("Walking segments do not have timetables")
        start = leg.raw_segment_indices[0]
        departure = canonical_station(leg.departure_station.name_jp or leg.departure_station.name)
        arrival = canonical_station(leg.arrival_station.name_jp or leg.arrival_station.name)
        railway = route.segments[start].railway_name_jp
        # Same physical leg/date can reuse exact platform data across parent Routes.
        raw_key = repr((departure, arrival, service_family(railway), route.search_date, cursor))
        key = "leg-timetable-v5:" + hashlib.sha256(raw_key.encode()).hexdigest()
        cached = await self.cache_port.get(key)
        if isinstance(cached, TimetableModel):
            logger.info('Timetable cache hit: date=%s leg=%s cursor=%d', route.search_date, leg_index, cursor)
            result = self._finalize_timetable(route, start, cached.model_copy(update={"route_id": route_id}))
            for option in result.selected_departures():
                await self.cache_port.set(exact_option_key(route_id, leg_index, option.id), option, ttl_seconds=3600)
            return result
        kwargs = {"timetable_id": None, "railway_name_jp": railway, "search_date": route.search_date}
        if cursor:
            kwargs["cursor"] = cursor
        timetable = await self.scraper_port.get_timetable(route_id, departure, arrival, **kwargs)
        await self.cache_port.set(key, timetable, ttl_seconds=3600)
        result = self._finalize_timetable(route, start, timetable)
        for option in result.selected_departures():
            await self.cache_port.set(exact_option_key(route_id, leg_index, option.id), option, ttl_seconds=3600)
        return result

    def _filter_for_route_topology(
        self,
        route,
        segment_index: int,
        timetable: Timetable,
    ) -> Timetable:
        if not route.segments or len(route.stations) <= segment_index + 1:
            return timetable
        return timetable.model_copy(update={
            "weekday": self.topology_classifier.filter_departures(
                route, segment_index, timetable.weekday
            ),
            "saturday": self.topology_classifier.filter_departures(
                route, segment_index, timetable.saturday
            ),
            "holiday": self.topology_classifier.filter_departures(
                route, segment_index, timetable.holiday
            ),
        })

    def _finalize_timetable(
        self,
        route,
        segment_index: int,
        timetable: Timetable,
    ) -> Timetable:
        selected_calendar = calendar_type_for_date(route.search_date)
        contextual_timetable = self._filter_for_route_topology(
            route,
            segment_index,
            timetable,
        ).model_copy(update={"selected_calendar": selected_calendar})
        logger.info(
            "Timetable ready: search_date=%s selected_calendar=%s "
            "weekday=%d saturday=%d holiday=%d selected=%d",
            route.search_date,
            selected_calendar.value,
            len(contextual_timetable.weekday),
            len(contextual_timetable.saturday),
            len(contextual_timetable.holiday),
            len(contextual_timetable.selected_departures()),
        )
        return contextual_timetable

    async def get_timetable(self, route_id: str) -> Timetable:
        route = await self.cache_port.get(route_id) if self.cache_port else None
        if not route:
            raise ValueError(f"Route {route_id} not found; search again")
        if route.passenger_legs:
            first_ride = next((leg for leg in route.passenger_legs if leg.segment_type != "walk"), None)
            if first_ride is None:
                raise ValueError("Walking segments do not have timetables")
            return await self.get_segment_timetable(route_id, first_ride.raw_segment_indices[0])
        timetable = await self.scraper_port.get_timetable(
            route_id, route.departure_station, route.arrival_station,
            timetable_id=None, railway_name_jp="", search_date=route.search_date)
        return self._finalize_timetable(route, 0, timetable)

    async def get_segment_timetable(self, route_id: str, segment_index: int, timetable_id: str | None = None) -> Timetable:
        if not self.cache_port:
            raise ValueError("Cache is required to get segments")

        route = await self.cache_port.get(route_id)
        if not route:
            raise ValueError(f"Route {route_id} not found")

        if not route.segments or segment_index < 0 or segment_index >= len(route.segments):
            raise ValueError(f"Invalid segment_index {segment_index}")

        segment = route.segments[segment_index]
        if segment.segment_type == 'walk' or getattr(segment, 'transport', '') == '徒歩':
            raise ValueError("Walking segments do not have timetables")

        dep = route.stations[segment_index].name_jp if route.stations[segment_index].name_jp else route.stations[segment_index].name
        leg = next((leg for leg in route.passenger_legs if segment_index in leg.raw_segment_indices), None)
        if leg and segment_index != leg.raw_segment_indices[0]:
            raise ValueError("Remain-on-board boundaries do not require a timetable selection")
        destination = leg.arrival_station if leg else route.stations[segment_index + 1]
        arr = canonical_station(destination.name_jp or destination.name)
        segment = route.segments[segment_index]
        railway_jp = getattr(segment, "railway_name_jp", "")

        timetable = await self.scraper_port.get_timetable(
            route_id,
            dep,
            arr,
            timetable_id=timetable_id,
            railway_name_jp=railway_jp,
            search_date=route.search_date,
        )
        return self._finalize_timetable(route, segment_index, timetable)

    async def get_segment_platform(self, route_id: str, segment_index: int, time: str, train_name: str, date: str | None = None) -> str | None:
        if not time:
            return None
        route = await self.cache_port.get(route_id) if self.cache_port else None
        if route and date and date != route.search_date:
            raise ValueError("Platform date must equal the Route search date")
        timetable = await self.get_segment_timetable(route_id, segment_index)
        matches = [item for item in timetable.selected_departures()
                   if item.time == time and item.train_name == train_name]
        return matches[0].platform or None if len(matches) == 1 else None


def exact_option_key(route_id: str, leg_index: int, departure_id: str) -> str:
    return "exact-option-v1:" + hashlib.sha256(repr((route_id, leg_index, departure_id)).encode()).hexdigest()
