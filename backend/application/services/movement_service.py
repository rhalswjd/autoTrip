from typing import Optional
from domain.movement import Movement
from domain.search import SearchRequest
from application.services.search_service import SearchModeResolver
from application.ports.cache_port import CachePort
from application.ports.notion_port import NotionPort
from domain.route import Route
from domain.exceptions import DomainException

from core.logger import logger
from application.services.timetable_service import exact_option_key
from domain.timetable import DepartureInfo
from domain.journey import elapsed_minutes, shift_time

class MovementService:
    def __init__(self, cache_port: CachePort, notion_port: NotionPort, search_service=None):
        self.cache_port = cache_port
        self.notion_port = notion_port
        self.search_service = search_service

    async def create_movement(
        self,
        route_id: str,
        departure_station: str,
        arrival_station: str,
        search_time: Optional[str],
        search_date: Optional[str],
        selected_departure_time: str,
        selected_arrival_time: str,
        target_page_id: Optional[str] = None,
        legs: Optional[list] = None
    ) -> tuple[Movement, dict]:
        route = await self.cache_port.get(route_id)
        
        if not route:
            raise DomainException("Route expired or missing; search again before saving")

        if legs and route.passenger_legs:
            expected = [leg for leg in route.passenger_legs if leg.segment_type != "walk"]
            if len(legs) != len(expected):
                raise DomainException("Select one exact departure for each PassengerLeg")
            validated = []
            total_fare = 0
            finalized_fare = True
            for selection, leg in zip(legs, expected):
                if selection.segment_index != leg.raw_segment_indices[0]:
                    raise DomainException("A through boundary cannot create a separate passenger selection")
                if not selection.exact_departure_id:
                    raise DomainException("An exact timetable departure is required before saving")
                exact = await self.cache_port.get(exact_option_key(route_id, leg.index, selection.exact_departure_id))
                if not isinstance(exact, DepartureInfo) or exact.operating_date not in ("", route.search_date):
                    raise DomainException("Selected departure expired or has a different date; reload its timetable")
                numeric_platform = int(exact.platform) if exact.platform.isdigit() else None
                validated.append(selection.model_copy(update={
                    "passenger_leg_index": leg.index,
                    "departure_station": leg.departure_station.name,
                    "arrival_station": leg.arrival_station.name,
                    "departure_time": exact.time, "arrival_time": exact.arrival_time,
                    "transport_name": exact.train_name, "railway_name": " / ".join(leg.railway_names),
                    "platform": numeric_platform,
                    "base_fare": exact.base_fare if exact.fare_status == "exact" else None,
                    "express_fare": exact.express_fare if exact.fare_status == "exact" else None,
                }))
                finalized_fare = finalized_fare and exact.fare_status == "exact"
                total_fare += (exact.base_fare or 0) + (exact.express_fare or 0)
            legs = validated
            selected_departure_time, selected_arrival_time = legs[0].departure_time, legs[-1].arrival_time
            has_access_walk = expected[0].index > 0
            has_egress_walk = expected[-1].index < len(route.passenger_legs) - 1
            if has_access_walk:
                offset = elapsed_minutes(route.departure_time, expected[0].departure_time)
                selected_departure_time = shift_time(selected_departure_time, -offset) if offset is not None else ''
            if has_egress_walk:
                offset = elapsed_minutes(expected[-1].arrival_time, route.arrival_time)
                selected_arrival_time = shift_time(selected_arrival_time, offset) if offset is not None else ''
            route = route.model_copy(update={"total_fare": total_fare if finalized_fare else 0,
                                              "fare_status": "exact" if finalized_fare else "unknown",
                                              "timing_status": 'includes_estimated_walking' if has_access_walk or has_egress_walk else 'exact'})

        search_req = SearchRequest(
            departure_station=departure_station,
            arrival_station=arrival_station,
            departure_time=route.search_time or search_time,
            departure_date=route.search_date or search_date
        )
        context = SearchModeResolver.resolve(search_req)

        movement = Movement(
            route=route,
            selected_departure_time=selected_departure_time,
            selected_arrival_time=selected_arrival_time,
            search_context=context
        )
        
        logger.info(f"Movement Created: {route_id} ({departure_station} -> {arrival_station})")
        
        logger.info("Notion Save Started")
        try:
            notion_result = await self.notion_port.save_movement(movement, target_page_id=target_page_id, legs=legs)
            logger.info("Notion Save Success")
            return movement, notion_result
        except Exception as e:
            logger.error(f"Notion Save Failed: {e}")
            raise
