"""Passenger-visible invariants, independent of live providers and Notion."""
from unittest.mock import AsyncMock

import pytest

from application.services.timetable_service import TimetableService
from domain.timetable import DepartureInfo, Timetable
from tests.factories import journey


def test_through_operator_boundary_is_one_boarding_action():
    route = journey(["敦賀", "福井", "大聖寺【乗換不要】", "金沢"],
                    ["ハピラインふくい", "ハピラインふくい", "IRいしかわ鉄道"],
                    [False, False, True])
    assert len(route.passenger_legs) == 2
    assert route.passenger_legs[1].arrival_station.name_jp == "金沢"
    assert route.passenger_legs[1].raw_segment_indices == [1, 2]
    assert len(route.passenger_legs[1].through_boundaries) == 1


def test_family_identity_ignores_exact_train_number_time_fare():
    from application.services.route_families import group_route_families
    a = journey(["新大阪", "敦賀"], ["ＪＲ特急サンダーバード15号"], id="one")
    b = journey(["新大阪", "敦賀"], ["ＪＲ特急サンダーバード19号"], id="two")
    b = b.model_copy(update={"departure_time": "10:00", "total_fare": 1200})
    families = group_route_families([a, b])
    assert len(families) == 1
    assert "15" not in families[0].railway_name


def test_direct_and_transfer_families_remain_separate():
    from application.services.route_families import group_route_families
    direct = journey(["A", "B", "C"], ["Rail", "Rail"], [False, True])
    transfer = journey(["A", "B", "C"], ["Rail", "Rail"])
    assert len(group_route_families([direct, transfer])) == 2


def test_same_corridor_shinkansen_services_share_family():
    from application.services.route_families import group_route_families
    routes = [journey(["新大阪", "名古屋"], [f"ＪＲ東海道新幹線{name}1号"])
              for name in ("のぞみ", "ひかり", "こだま")]
    assert len(group_route_families(routes)) == 1


def test_local_and_special_rapid_do_not_merge_by_substring():
    from application.services.route_families import group_route_families
    routes = [journey(["A", "B"], [name]) for name in ("ＪＲ京都線快速", "ＪＲ京都線新快速")]
    assert len(group_route_families(routes)) == 2


def test_dominated_exact_sample_is_not_the_family_representative():
    from application.services.route_families import group_route_families
    slow = journey(["A", "B"], ["快速"], id="slow").model_copy(update={
        "arrival_time": "09:00", "total_duration": "159m"})
    fast = journey(["A", "B"], ["快速"], id="fast").model_copy(update={
        "arrival_time": "09:00", "total_duration": "133m"})
    assert group_route_families([slow, fast])[0].id == "fast"


@pytest.mark.asyncio
async def test_timetable_queries_end_of_continuous_passenger_leg():
    route = journey(["福井", "大聖寺【乗換不要】", "金沢"],
                    ["ハピラインふくい", "IRいしかわ鉄道"], [False, True])
    cache, scraper = AsyncMock(), AsyncMock()
    cache.get.return_value = route
    scraper.get_timetable.return_value = Timetable(route_id=route.id)
    service = TimetableService(scraper, cache)
    await service.get_timetable(route.id)
    assert scraper.get_timetable.await_args.args[2] == "金沢"


@pytest.mark.asyncio
async def test_platform_does_not_search_for_a_similar_train():
    route = journey(["A", "B"], ["新幹線"])
    cache, scraper = AsyncMock(), AsyncMock()
    cache.get.return_value = route
    scraper.get_timetable.return_value = Timetable(route_id=route.id, selected_calendar="saturday",
        saturday=[DepartureInfo(id="exact", time="06:06", train_name="Hikari 1", platform="11")])
    result = await TimetableService(scraper, cache).get_segment_platform(
        route.id, 0, "06:05", "Hikari 1", "2026-10-31")
    assert result is None
    scraper.search_routes.assert_not_awaited()


def test_public_holiday_does_not_use_weekday_bucket():
    from domain.timetable import calendar_type_for_date
    assert calendar_type_for_date("2026-11-03") == "holiday"


def test_response_exposes_passenger_legs_and_raw_railway_identity():
    from api.schemas import RouteResponseSchema
    route = journey(["梅田", "新大阪"], ["Osaka Metro Midosuji Line"])
    payload = RouteResponseSchema(**route.model_dump()).model_dump()
    assert payload["passenger_legs"][0]["raw_segment_indices"] == [0]
    assert payload["segments"][0]["railway_name_jp"] == "Osaka Metro Midosuji Line"


def test_explicitly_different_homonymous_station_regions_do_not_merge():
    from domain.journey import station_names_match
    assert not station_names_match('府中(東京都)', '府中(広島県)')


@pytest.mark.asyncio
async def test_expired_route_never_creates_a_fabricated_notion_journey():
    from application.services.movement_service import MovementService
    from core.exceptions import DomainException
    cache, notion = AsyncMock(), AsyncMock()
    cache.get.return_value = None
    with pytest.raises(DomainException, match="search again"):
        await MovementService(cache, notion).create_movement(
            "expired", "A", "B", None, None, "06:00", "07:00")
    notion.save_movement.assert_not_awaited()


@pytest.mark.asyncio
async def test_equivalent_exact_departure_reuses_platform_across_parent_routes():
    from infrastructure.fakes.fake_cache import FakeCacheAdapter
    from application.services.timetable_service import exact_option_key
    cache, scraper = FakeCacheAdapter(), AsyncMock()
    first = journey(['A', 'B'], ['JR Local'], id='direct')
    second = journey(['A', 'B', 'C'], ['JR Local', 'Other'], id='parent')
    await cache.set(first.id, first)
    await cache.set(second.id, second)
    scraper.get_timetable.return_value = Timetable(route_id=first.id, selected_calendar='saturday',
        saturday=[DepartureInfo(id='exact-train', time='08:00', arrival_time='09:00', train_name='Local',
            platform='5', operating_date=first.search_date, metadata={'stop_sequence': ['A', 'B']})])
    service = TimetableService(scraper, cache)
    a = await service.get_leg_timetable(first.id, 0)
    b = await service.get_leg_timetable(second.id, 0)
    assert a.saturday[0].platform == b.saturday[0].platform == '5'
    assert scraper.get_timetable.await_count == 1
    assert (await cache.get(exact_option_key(second.id, 0, 'exact-train'))).platform == '5'


@pytest.mark.asyncio
async def test_expired_route_timetable_never_queries_a_provider_without_context():
    cache, scraper = AsyncMock(), AsyncMock()
    cache.get.return_value = None
    with pytest.raises(ValueError, match='not found'):
        await TimetableService(scraper, cache).get_timetable('expired')
    scraper.get_timetable.assert_not_awaited()
