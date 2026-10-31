from unittest.mock import AsyncMock

import pytest

from infrastructure.adapters.transport_scraper import TransportScraperAdapter
from application.ports.scraper_port import ScraperException


@pytest.mark.asyncio
async def test_jr_bus_does_not_use_a_railway_station_timetable():
    official, other = AsyncMock(), AsyncMock()
    adapter = TransportScraperAdapter(AsyncMock(), official, other)
    result = await adapter.get_timetable('bus-route', 'A', 'B',
        railway_name_jp='高速バス・西日本ＪＲバス', search_date='2026-10-31')
    assert result.status == 'unsupported'
    assert result.selected_calendar == 'saturday'
    official.get_timetable.assert_not_awaited()
    other.get_timetable.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_jr_provider_unavailable_is_explicit_and_calendar_preserved():
    official, other = AsyncMock(), AsyncMock()
    other.get_timetable.side_effect = ValueError('Direction not published')
    adapter = TransportScraperAdapter(AsyncMock(), official, other)
    result = await adapter.get_timetable('metro-route', 'A', 'B',
        railway_name_jp='OsakaMetro御堂筋線', search_date='2026-11-03')
    assert result.status == 'unsupported'
    assert result.source == 'yahoo'
    assert result.selected_calendar == 'holiday'
    assert 'Direction' in result.message
    official.get_timetable.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_jr_later_departures_remain_accessible_after_detail_budget():
    from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
    import httpx
    scraper = YahooTimetableScraper()
    await scraper.client.aclose()
    scraper.client = AsyncMock()
    items = ''.join(f'<li><a href="/train/{i}"><dt>{i:02}</dt><dd class="trainType">普通</dd><dd class="trainFor">B</dd></a></li>' for i in range(60))
    html = f'<table class="tblDiaDetail"><tr><td class="hour">10</td><td><ul>{items}</ul></td></tr></table>'
    scraper.client.get.return_value = httpx.Response(200, text=html, request=httpx.Request('GET', 'https://transit.yahoo.co.jp/timetable/example'))
    scraper._fetch_train_details = AsyncMock(return_value={'arrival_time': '12:00', 'train_name': '普通', 'stop_sequence': ['A', 'B']})
    first_state = {}
    first = await scraper._parse_timetable_page('/example', 'A', 'B', page_state=first_state)
    assert len(first) == scraper.FINAL_DEPARTURE_DETAIL_BUDGET
    assert first_state['next_cursor'] == len(first)
    last_state = {}
    last = await scraper._parse_timetable_page('/example', 'A', 'B', cursor=first_state['next_cursor'], page_state=last_state)
    assert len(first + last) == 60
    assert last_state['next_cursor'] is None
