from unittest.mock import AsyncMock

import pytest

from application.services.timetable_service import TimetableService
from domain.route import Route, RouteSegment
from domain.station import Station
from domain.timetable import DepartureInfo, Timetable


def station(index: int, name: str) -> Station:
    return Station(id=f"station-{index}", name=name, name_jp=name)


def route_with_segments(
    station_names: list[str],
    through_flags: list[bool],
    transfer_count: int,
) -> Route:
    return Route(
        id="route-topology",
        departure_station=station_names[0],
        arrival_station=station_names[-1],
        railway_name="Rail",
        total_duration="1h",
        total_fare=1000,
        transfer_count=transfer_count,
        polyline="",
        search_date="2026-08-26",
        stations=[station(index, name) for index, name in enumerate(station_names)],
        segments=[
            RouteSegment(
                segment_type="train",
                railway_name=f"Rail {index}",
                railway_name_jp=f"路線{index}",
                is_through=is_through,
            )
            for index, is_through in enumerate(through_flags)
        ],
    )


def departure(
    departure_id: str,
    time: str,
    service: str,
    stops: list[str],
) -> DepartureInfo:
    return DepartureInfo(
        id=departure_id,
        time=time,
        arrival_time="07:00",
        train_name=service,
        train_type=service,
        metadata={"stop_sequence": stops},
    )


@pytest.mark.asyncio
async def test_direct_train_is_removed_from_transfer_route_timetable():
    route = route_with_segments(
        ["敦賀", "福井", "金沢"],
        [False, False],
        transfer_count=1,
    )
    terminating = departure("terminating", "05:32", "Local", ["敦賀", "福井"])
    direct = departure("direct", "06:05", "Local", ["敦賀", "福井", "金沢"])
    scraper = AsyncMock()
    scraper.get_timetable.return_value = Timetable(
        route_id=route.id,
        weekday=[terminating, direct],
    )
    cache = AsyncMock()
    cache.get.return_value = route
    service = TimetableService(scraper_port=scraper, cache_port=cache)

    timetable = await service.get_segment_timetable(route.id, 0)

    assert [item.id for item in timetable.weekday] == ["terminating"]
    assert service.topology_classifier.classify(route, 0, direct) == "ALTERNATIVE_TOPOLOGY"
    scraper.get_timetable.assert_awaited_once()


def test_logical_boundary_is_not_a_passenger_transfer():
    route = route_with_segments(
        ["福井", "大聖寺【乗換不要】", "金沢"],
        [False, True],
        transfer_count=0,
    )
    service = TimetableService(scraper_port=AsyncMock(), cache_port=AsyncMock())

    assert service.topology_classifier.passenger_transfer_stations(route) == ()
    candidate = departure("through", "06:27", "Local", ["福井", "大聖寺", "金沢"])
    assert service.topology_classifier.classify(route, 0, candidate) == "COMPATIBLE"


def test_real_train_change_remains_a_passenger_transfer():
    route = route_with_segments(
        ["敦賀", "福井", "金沢"],
        [False, False],
        transfer_count=1,
    )
    service = TimetableService(scraper_port=AsyncMock(), cache_port=AsyncMock())

    assert service.topology_classifier.passenger_transfer_stations(route) == ("福井",)


def test_different_services_can_share_the_same_passenger_topology():
    route = route_with_segments(
        ["新大阪", "名古屋"],
        [False],
        transfer_count=0,
    )
    service = TimetableService(scraper_port=AsyncMock(), cache_port=AsyncMock())
    hikari = departure("hikari", "06:11", "Hikari", ["新大阪", "京都", "名古屋", "東京"])
    nozomi = departure("nozomi", "06:15", "Nozomi", ["新大阪", "名古屋", "東京"])

    assert service.topology_classifier.classify(route, 0, hikari) == "COMPATIBLE"
    assert service.topology_classifier.classify(route, 0, nozomi) == "COMPATIBLE"


def test_candidate_that_does_not_stop_at_required_destination_is_not_compatible():
    route = route_with_segments(
        ["新大阪", "名古屋"],
        [False],
        transfer_count=0,
    )
    service = TimetableService(scraper_port=AsyncMock(), cache_port=AsyncMock())
    pass_through = departure("pass-through", "06:20", "Express", ["新大阪", "東京"])

    assert service.topology_classifier.classify(route, 0, pass_through) == "NOT_COMPATIBLE"


def test_candidate_reaching_later_passenger_leg_bypasses_current_transfer():
    route = route_with_segments(
        ["A", "B", "C", "D"],
        [False, False, False],
        transfer_count=2,
    )
    service = TimetableService(scraper_port=AsyncMock(), cache_port=AsyncMock())
    bypass = departure("bypass", "08:00", "Local", ["A", "B", "C"])

    assert service.topology_classifier.classify(route, 0, bypass) == "ALTERNATIVE_TOPOLOGY"
