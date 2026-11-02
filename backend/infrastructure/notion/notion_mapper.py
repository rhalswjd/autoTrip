from typing import Dict, Any
from domain.movement import Movement
from infrastructure.notion.properties import (
    build_title, build_rich_text, build_number, build_select
)
from infrastructure.notion.constants import NotionColumns
from infrastructure.services.translation_service import TranslationService
from functools import lru_cache
from domain.platform import PlatformStatus


@lru_cache(maxsize=1)
def _translator():
    return TranslationService()

class NotionMapper:
    """
    Translates a pure Domain Movement entity into Notion-specific Property DTOs.
    Relies purely on the data values within Movement, ignoring Application workflows (SearchMode).
    """
    @staticmethod
    def map_to_properties(movement: Movement) -> Dict[str, Any]:
        return NotionMapper.map_parent_movement(movement)

    @staticmethod
    def _time_with_platform(time: str, leg, *, arrival: bool) -> str:
        field = 'arrival_platform' if arrival else 'platform'
        value = getattr(leg, field, None)
        status = getattr(leg, field + '_status', None) or (PlatformStatus.KNOWN if value is not None else PlatformStatus.LOOKUP_FAILED)
        label = '도착 플랫폼' if arrival else '출발 플랫폼'
        if status == PlatformStatus.KNOWN and value is not None and str(value).strip():
            # The existing Platform property is numeric. Text values and arrival
            # evidence belong in existing rich-text fields, without schema edits.
            if not arrival and str(value).isdecimal():
                return time
            wording = str(value)
        elif status == PlatformStatus.SOURCE_NOT_PROVIDED:
            wording = '공식 정보 미제공' if getattr(leg, 'source', '') == 'jr_odekake' else '출처 정보 미제공'
        else:
            wording = '조회 실패'
        return f'{time} ({label}: {wording})'

    @staticmethod
    def _numeric_platform(leg):
        value = getattr(leg, 'platform', None)
        status = getattr(leg, 'platform_status', None) or (PlatformStatus.KNOWN if value is not None else PlatformStatus.LOOKUP_FAILED)
        return int(value) if status == PlatformStatus.KNOWN and value is not None and str(value).isdecimal() else None

    @staticmethod
    def _resolve_leg_transport_type(leg) -> str:
        transport_name = leg.transport_name or ""
        railway_name = getattr(leg, "railway_name", None) or ""
        normalized_railway = railway_name.lower()

        subway_markers = ("metro", "subway", "toei", "地下鉄", "メトロ", "市営")
        bus_markers = ("bus", "バス")
        is_subway = (
            railway_name
            and any(marker in normalized_railway for marker in subway_markers)
            and not any(marker in normalized_railway for marker in bus_markers)
        )

        if is_subway:
            return railway_name
        # Keep provider identity untouched; translate only at the presentation boundary.
        translated = _translator().translate_train(transport_name)
        if translated != transport_name:
            for category in ('Shinkansen', 'Limited Express'):
                if category in railway_name and category not in translated:
                    return f"{'JR ' if railway_name.startswith('JR') else ''}{category} {translated}"
        return translated

    @staticmethod
    def map_parent_movement(movement: Movement, selected_leg=None) -> Dict[str, Any]:
        route = movement.route
        
        properties: Dict[str, Any] = {
            NotionColumns.ROUTE: build_title(f"{route.departure_station} -> {route.arrival_station}"),
            NotionColumns.TRANSPORT_TYPE: build_select("Mixed" if route.transfer_count > 0 else route.railway_name),
        }
        if route.fare_status != "unknown" and (selected_leg is None or route.fare_status == 'exact'):
            properties[NotionColumns.FARE] = build_number(route.total_fare)
        if selected_leg is not None:
            properties[NotionColumns.TRANSPORT_TYPE] = build_select(NotionMapper._resolve_leg_transport_type(selected_leg))
            numeric = NotionMapper._numeric_platform(selected_leg)
            if numeric is not None:
                properties[NotionColumns.PLATFORM] = build_number(numeric)

        if movement.selected_departure_time:
            note = ' (도보·연결 추정 포함)' if route.timing_status == 'includes_estimated_walking' else ''
            time = movement.selected_departure_time + note
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text(
                NotionMapper._time_with_platform(time, selected_leg, arrival=False) if selected_leg is not None else time)

        if movement.selected_arrival_time and not movement.selected_arrival_time.startswith("N/A"):
            note = ' (도보·연결 추정 포함)' if route.timing_status == 'includes_estimated_walking' else ''
            time = movement.selected_arrival_time + note
            properties[NotionColumns.ARRIVAL_TIME] = build_rich_text(
                NotionMapper._time_with_platform(time, selected_leg, arrival=True) if selected_leg is not None else time)

        import logging
        logger = logging.getLogger("autotrip")
        logger.debug("Notion parent properties prepared: %d fields", len(properties))

        return properties

    @staticmethod
    def map_leg(leg, parent_page_id: str, parent_property_name: str) -> Dict[str, Any]:
        properties: Dict[str, Any] = {
            NotionColumns.ROUTE: build_title(f"{leg.departure_station} -> {leg.arrival_station}")
        }
        
        transport_type = NotionMapper._resolve_leg_transport_type(leg)
        if transport_type:
            properties[NotionColumns.TRANSPORT_TYPE] = build_select(transport_type)
            
        if leg.departure_time:
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text(NotionMapper._time_with_platform(leg.departure_time, leg, arrival=False))
            
        if leg.arrival_time and not leg.arrival_time.startswith("N/A"):
            properties[NotionColumns.ARRIVAL_TIME] = build_rich_text(NotionMapper._time_with_platform(leg.arrival_time, leg, arrival=True))
            
        numeric = NotionMapper._numeric_platform(leg)
        if numeric is not None:
            properties[NotionColumns.PLATFORM] = build_number(numeric)
            
        has_fare = False
        total_leg_fare = 0
        if getattr(leg, 'base_fare', None) is not None:
            total_leg_fare += leg.base_fare
            has_fare = True
        if getattr(leg, 'express_fare', None) is not None:
            total_leg_fare += leg.express_fare
            has_fare = True
            
        if has_fare and total_leg_fare > 0:
            properties[NotionColumns.FARE] = build_number(total_leg_fare)
            
        properties[parent_property_name] = {"relation": [{"id": parent_page_id}]}
        
        return properties
