from domain.movement import Movement
from domain.route import Route
from domain.search import SearchContext
from domain.enums import SearchMode
from infrastructure.notion.notion_mapper import NotionMapper
from infrastructure.notion.constants import NotionColumns

def _build_dummy_movement(date: str = None, time: str = "") -> Movement:
    route = Route(
        id="test_id", departure_station="Osaka", arrival_station="Kyoto",
        railway_name="JR Kyoto", total_duration="30m", total_fare=580,
        transfer_count=0, polyline="", stations=[]
    )
    context = SearchContext(
        departure_station="Osaka", arrival_station="Kyoto",
        departure_time=time if time else None,
        departure_date=date,
        search_mode=SearchMode.ROUTE_ONLY # This Enum should be completely ignored by Mapper now
    )
    return Movement(
        route=route, selected_departure_time=time, selected_arrival_time=time,
        search_context=context
    )

def test_mapper_no_time_no_date():
    movement = _build_dummy_movement()
    props = NotionMapper.map_to_properties(movement)
    
    assert props[NotionColumns.NAME]["title"][0]["text"]["content"] == "Osaka -> Kyoto"
    assert props[NotionColumns.CONFIRMED]["checkbox"] is False
    assert props[NotionColumns.DEPARTURE_TIME]["rich_text"][0]["text"]["content"] == "Not Specified"
    assert NotionColumns.DATE not in props

def test_mapper_with_datetime():
    movement = _build_dummy_movement(date="2024-10-01", time="10:00")
    props = NotionMapper.map_to_properties(movement)
    
    assert props[NotionColumns.CONFIRMED]["checkbox"] is True
    assert props[NotionColumns.DATE]["date"]["start"] == "2024-10-01T10:00:00"
    assert NotionColumns.DEPARTURE_TIME not in props
