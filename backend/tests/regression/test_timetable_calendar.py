from unittest.mock import AsyncMock

import pytest

from api.schemas import TimetableResponseSchema
from api.dependencies import get_timetable_service
from application.services.timetable_service import TimetableService
from domain.route import Route, RouteSegment
from domain.station import Station
from domain.timetable import DepartureInfo, Timetable


def departure(departure_id: str, time: str) -> DepartureInfo:
    return DepartureInfo(
        id=departure_id,
        time=time,
        arrival_time="09:54",
        train_name="Special Rapid",
        train_type="Special Rapid",
    )


def route(route_id: str, search_date: str) -> Route:
    return Route(
        id=route_id,
        departure_station="Shin-Osaka",
        arrival_station="Tsuruga",
        railway_name="JR Kyoto Line Special Rapid",
        total_duration="2h 5m",
        total_fare=2310,
        transfer_count=0,
        polyline="direct",
        search_date=search_date,
        search_time="06:00",
        stations=[
            Station(id="shin-osaka", name="Shin-Osaka", name_jp="新大阪"),
            Station(id="tsuruga", name="Tsuruga", name_jp="敦賀"),
        ],
        segments=[
            RouteSegment(
                segment_type="train",
                railway_name="JR Kyoto Line Special Rapid",
                railway_name_jp="ＪＲ京都線新快速",
            )
        ],
    )


class RouteCache:
    def __init__(self, routes):
        self.routes = {item.id: item for item in routes}

    async def get(self, key):
        return self.routes.get(key)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search_date", "expected_calendar", "bucket_name"),
    [
        ("2026-10-10", "saturday", "saturday"),
        ("2026-10-13", "weekday", "weekday"),
        ("2026-10-12", "holiday", "holiday"),
        ("2026-10-11", "holiday", "holiday"),
    ],
)
async def test_service_selects_calendar_bucket_for_route_date(
    search_date,
    expected_calendar,
    bucket_name,
):
    selected = departure(f"{expected_calendar}-1", "07:49")
    timetable = Timetable(
        route_id="route-1",
        weekday=[selected] if bucket_name == "weekday" else [],
        saturday=[selected] if bucket_name == "saturday" else [],
        holiday=[selected] if bucket_name == "holiday" else [],
    )
    scraper = AsyncMock()
    scraper.get_timetable.return_value = timetable
    service = TimetableService(
        scraper_port=scraper,
        cache_port=RouteCache([route("route-1", search_date)]),
    )

    result = await service.get_timetable("route-1")

    assert result.selected_calendar == expected_calendar
    assert [item.id for item in result.selected_departures()] == [selected.id]


@pytest.mark.asyncio
async def test_empty_saturday_does_not_fall_back_to_weekday():
    weekday_only = departure("weekday-only", "07:49")
    scraper = AsyncMock()
    scraper.get_timetable.return_value = Timetable(
        route_id="route-saturday",
        weekday=[weekday_only],
        saturday=[],
        holiday=[],
    )
    service = TimetableService(
        scraper_port=scraper,
        cache_port=RouteCache([route("route-saturday", "2026-10-10")]),
    )

    result = await service.get_timetable("route-saturday")

    assert result.selected_calendar == "saturday"
    assert result.selected_departures() == []
    assert [item.id for item in result.weekday] == [weekday_only.id]


@pytest.mark.asyncio
async def test_selected_calendar_survives_api_serialization():
    saturday_departure = departure("saturday-0749", "07:49")
    scraper = AsyncMock()
    scraper.get_timetable.return_value = Timetable(
        route_id="route-saturday",
        weekday=[],
        saturday=[saturday_departure],
        holiday=[],
    )
    service = TimetableService(
        scraper_port=scraper,
        cache_port=RouteCache([route("route-saturday", "2026-10-10")]),
    )

    result = await service.get_timetable("route-saturday")
    payload = TimetableResponseSchema(**result.model_dump()).model_dump()

    assert payload["selected_calendar"] == "saturday"
    assert payload["saturday"][0]["id"] == "saturday-0749"
    assert payload["weekday"] == []


def test_route_timetable_endpoint_serializes_selected_calendar(client):
    service = AsyncMock()
    service.get_timetable.return_value = Timetable(
        route_id="route-saturday",
        selected_calendar="saturday",
        saturday=[departure("saturday-0749", "07:49")],
    )
    client.app.dependency_overrides[get_timetable_service] = lambda: service
    try:
        response = client.get("/api/v1/routes/route-saturday/timetable")
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["selected_calendar"] == "saturday"
    assert response.json()["saturday"][0]["id"] == "saturday-0749"
    assert response.json()["weekday"] == []


@pytest.mark.asyncio
async def test_different_route_dates_do_not_share_timetable_context():
    scraper = AsyncMock()
    scraper.get_timetable.side_effect = [
        Timetable(route_id="route-saturday", saturday=[departure("sat", "07:49")]),
        Timetable(route_id="route-weekday", weekday=[departure("weekday", "07:49")]),
    ]
    cache = RouteCache([
        route("route-saturday", "2026-10-10"),
        route("route-weekday", "2026-10-13"),
    ])
    service = TimetableService(scraper_port=scraper, cache_port=cache)

    saturday = await service.get_timetable("route-saturday")
    weekday = await service.get_timetable("route-weekday")

    assert saturday.selected_calendar == "saturday"
    assert [item.id for item in saturday.selected_departures()] == ["sat"]
    assert weekday.selected_calendar == "weekday"
    assert [item.id for item in weekday.selected_departures()] == ["weekday"]
    assert scraper.get_timetable.await_args_list[0].kwargs["search_date"] == "2026-10-10"
    assert scraper.get_timetable.await_args_list[1].kwargs["search_date"] == "2026-10-13"
