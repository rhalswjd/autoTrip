from domain.timetable import Timetable, calendar_type_for_date
from application.ports.scraper_port import ScraperPort, ScraperException

from application.ports.cache_port import CachePort
from application.services.passenger_topology import PassengerTopologyClassifier
from core.logger import logger
from domain.journey import canonical_station, service_family
from domain.timetable import Timetable as TimetableModel
import hashlib
from datetime import date, timedelta, datetime
from domain.chronology import stamp_departure

class TimetableService:
    def __init__(self, scraper_port: ScraperPort, cache_port: CachePort = None):
        self.scraper_port = scraper_port
        self.cache_port = cache_port
        self.topology_classifier = PassengerTopologyClassifier()

    async def get_leg_timetable(self, route_id: str, leg_index: int, cursor: int = 0, service_date: str | None = None, not_before: str | None = None) -> Timetable:
        route = await self.cache_port.get(route_id) if self.cache_port else None
        if not route:
            raise ValueError(f"Route {route_id} not found; search again")
        if leg_index < 0 or leg_index >= len(route.passenger_legs):
            raise ValueError(f"Invalid leg_index {leg_index}")
        leg = route.passenger_legs[leg_index]
        if leg.segment_type == "walk":
            raise ValueError("Walking segments do not have timetables")
        lookup_date = service_date or route.search_date
        if lookup_date and route.search_date:
            offset = (date.fromisoformat(lookup_date) - date.fromisoformat(route.search_date)).days
            if not 0 <= offset <= len(route.passenger_legs):
                raise ValueError('Timetable date is outside this journey continuation window')
        route = route.model_copy(update={'search_date': lookup_date})
        if not_before and datetime.fromisoformat(not_before).tzinfo is None:
            raise ValueError('Transfer boundary must include a timezone')
        start = leg.raw_segment_indices[0]
        departure = canonical_station(leg.departure_station.name_jp or leg.departure_station.name)
        arrival = canonical_station(leg.arrival_station.name_jp or leg.arrival_station.name)
        railway = route.segments[start].railway_name_jp
        # Same physical leg/date can reuse exact platform data across parent Routes.
        raw_key = repr((leg.departure_station.identity_key(), leg.arrival_station.identity_key(),
                        service_family(railway), route.search_date, cursor, not_before))
        key = "leg-timetable-v10:" + hashlib.sha256(raw_key.encode()).hexdigest()
        cached = await self.cache_port.get(key)
        if isinstance(cached, TimetableModel):
            logger.info('Timetable cache hit: date=%s leg=%s cursor=%d', route.search_date, leg_index, cursor)
            result = self._finalize_timetable(route, start, cached.model_copy(update={"route_id": route_id}), not_before)
            for option in result.selected_departures():
                await self.cache_port.set(exact_option_key(route_id, leg_index, option.id, lookup_date), option, ttl_seconds=3600)
            return result
        kwargs = {"timetable_id": None, "railway_name_jp": railway, "search_date": route.search_date,
                  "station_context": (leg.departure_station, leg.arrival_station)}
        if cursor:
            kwargs["cursor"] = cursor
        if not_before:
            kwargs['not_before'] = not_before
        try:
            timetable = await self.scraper_port.get_timetable(route_id, departure, arrival, **kwargs)
        except ScraperException as exc:
            logger.warning('Passenger leg provider failed: leg=%d error=%s', leg_index, exc)
            return Timetable(route_id=route_id, status='provider_error',
                             selected_calendar=calendar_type_for_date(route.search_date),
                             message='이 구간의 시간표 공급자에 일시적인 오류가 있습니다. 다른 구간은 독립적으로 조회할 수 있습니다.')
        await self.cache_port.set(key, timetable, ttl_seconds=3600)
        result = self._finalize_timetable(route, start, timetable, not_before)
        for option in result.selected_departures():
            await self.cache_port.set(exact_option_key(route_id, leg_index, option.id, lookup_date), option, ttl_seconds=3600)
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
        not_before: str | None = None,
    ) -> Timetable:
        selected_calendar = calendar_type_for_date(route.search_date)
        contextual_timetable = self._filter_for_route_topology(
            route,
            segment_index,
            timetable,
        ).model_copy(update={"selected_calendar": selected_calendar, 'search_date': route.search_date or ''})
        if route.search_date:
            contextual_timetable = contextual_timetable.model_copy(update={bucket: [stamp_departure(item, route.search_date)
                for item in getattr(contextual_timetable, bucket)] for bucket in ('weekday','saturday','holiday')})
        if not_before:
            boundary = datetime.fromisoformat(not_before)
            contextual_timetable = contextual_timetable.model_copy(update={bucket: [item
                for item in getattr(contextual_timetable,bucket) if datetime.fromisoformat(item.departure_datetime) >= boundary]
                for bucket in ('weekday','saturday','holiday')})
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
            station_context=(route.stations[segment_index], destination),
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


def exact_option_key(route_id: str, leg_index: int, departure_id: str, service_date: str | None = None) -> str:
    return "exact-option-v3:" + hashlib.sha256(repr((route_id, leg_index, departure_id, service_date)).encode()).hexdigest()
