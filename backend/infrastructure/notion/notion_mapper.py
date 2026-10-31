from typing import Dict, Any
from domain.movement import Movement
from infrastructure.notion.properties import (
    build_title, build_rich_text, build_number, build_select
)
from infrastructure.notion.constants import NotionColumns

class NotionMapper:
    """
    Translates a pure Domain Movement entity into Notion-specific Property DTOs.
    Relies purely on the data values within Movement, ignoring Application workflows (SearchMode).
    """
    @staticmethod
    def map_to_properties(movement: Movement) -> Dict[str, Any]:
        return NotionMapper.map_parent_movement(movement)

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

        return railway_name if is_subway else transport_name

    @staticmethod
    def map_parent_movement(movement: Movement) -> Dict[str, Any]:
        route = movement.route
        
        properties: Dict[str, Any] = {
            NotionColumns.ROUTE: build_title(f"{route.departure_station} -> {route.arrival_station}"),
            NotionColumns.TRANSPORT_TYPE: build_select("Mixed" if route.transfer_count > 0 else route.railway_name),
        }
        if route.fare_status != "unknown":
            properties[NotionColumns.FARE] = build_number(route.total_fare)

        if movement.selected_departure_time:
            note = ' (도보·연결 추정 포함)' if route.timing_status == 'includes_estimated_walking' else ''
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text(movement.selected_departure_time + note)

        if movement.selected_arrival_time and not movement.selected_arrival_time.startswith("N/A"):
            note = ' (도보·연결 추정 포함)' if route.timing_status == 'includes_estimated_walking' else ''
            properties[NotionColumns.ARRIVAL_TIME] = build_rich_text(movement.selected_arrival_time + note)

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
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text(leg.departure_time)
            
        if leg.arrival_time and not leg.arrival_time.startswith("N/A"):
            properties[NotionColumns.ARRIVAL_TIME] = build_rich_text(leg.arrival_time)
            
        if leg.platform is not None:
            properties[NotionColumns.PLATFORM] = build_number(leg.platform)
            
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
