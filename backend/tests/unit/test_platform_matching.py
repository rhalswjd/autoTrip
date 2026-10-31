"""Platforms must come from the exact timetable option, never a nearby train."""
from unittest.mock import AsyncMock

import pytest

from application.services.timetable_service import TimetableService
from domain.timetable import DepartureInfo, Timetable
from tests.factories import journey


@pytest.mark.asyncio
@pytest.mark.parametrize(("requested_time", "requested_name", "expected"), [
    ("06:05", "Hikari 1", None),
    ("06:06", "Nozomi 1", None),
    ("06:06", "Hikari 1", "11"),
    ("", "Hikari 1", None),
])
async def test_exact_platform_matching(requested_time, requested_name, expected):
    route = journey(["A", "B"], ["新幹線"])
    cache, scraper = AsyncMock(), AsyncMock()
    cache.get.return_value = route
    scraper.get_timetable.return_value = Timetable(
        route_id=route.id, selected_calendar="saturday",
        saturday=[DepartureInfo(id="hikari-1", time="06:06", arrival_time="07:06",
            train_name="Hikari 1", platform="11", operating_date="2026-10-31")])
    platform = await TimetableService(scraper, cache).get_segment_platform(
        route.id, 0, requested_time, requested_name, "2026-10-31")
    assert platform == expected
    scraper.search_routes.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_platform_remains_unknown():
    route = journey(["A", "B"], ["新幹線"])
    cache, scraper = AsyncMock(), AsyncMock()
    cache.get.return_value = route
    scraper.get_timetable.return_value = Timetable(route_id=route.id, selected_calendar="saturday",
        saturday=[DepartureInfo(id="unknown", time="06:06", arrival_time="07:06", train_name="Hikari 1")])
    assert await TimetableService(scraper, cache).get_segment_platform(route.id, 0, "06:06", "Hikari 1") is None


@pytest.mark.asyncio
async def test_platform_date_cannot_drift_from_route():
    cache = AsyncMock()
    cache.get.return_value = journey(["A", "B"], ["新幹線"])
    with pytest.raises(ValueError, match="Route search date"):
        await TimetableService(AsyncMock(), cache).get_segment_platform("route", 0, "06:06", "Hikari 1", "2026-11-01")
