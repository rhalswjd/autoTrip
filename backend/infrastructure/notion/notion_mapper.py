from typing import Dict, Any
from domain.movement import Movement
from infrastructure.notion.properties import (
    build_title, build_select, build_rich_text, build_number, build_checkbox, build_date
)
from infrastructure.notion.constants import NotionColumns

class NotionMapper:
    """
    Translates a pure Domain Movement entity into Notion-specific Property DTOs.
    Relies purely on the data values within Movement, ignoring Application workflows (SearchMode).
    """
    @staticmethod
    def map_to_properties(movement: Movement) -> Dict[str, Any]:
        route = movement.route
        context = movement.search_context
        
        properties: Dict[str, Any] = {
            NotionColumns.NAME: build_title(f"{route.departure_station} -> {route.arrival_station}"),
            NotionColumns.RAILWAY: build_select(route.railway_name),
            NotionColumns.DURATION: build_rich_text(route.total_duration),
            NotionColumns.FARE: build_number(route.total_fare),
            NotionColumns.TRANSFERS: build_number(route.transfer_count)
        }

        # Data-driven decision logic (No Enum checks)
        has_time = bool(movement.selected_departure_time)
        has_date = bool(context.departure_date)

        if has_date and has_time:
            properties[NotionColumns.CONFIRMED] = build_checkbox(True)
            # Notion Date Property requires ISO-8601 formatting
            date_str = f"{context.departure_date}T{movement.selected_departure_time}:00"
            properties[NotionColumns.DATE] = build_date(start_date=date_str)
        elif has_time:
            properties[NotionColumns.CONFIRMED] = build_checkbox(False)
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text(movement.selected_departure_time)
        else:
            properties[NotionColumns.CONFIRMED] = build_checkbox(False)
            properties[NotionColumns.DEPARTURE_TIME] = build_rich_text("Not Specified")

        return properties
