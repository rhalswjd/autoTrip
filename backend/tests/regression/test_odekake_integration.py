"""Official-provider discovery and exact train data; no network required."""
from unittest.mock import AsyncMock

import pytest

from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser
from tests.fixtures.odekake import STATION_PAGE, TRAIN_PAGE


def test_exact_train_parser_excludes_pass_through_stops_and_preserves_tracks():
    details = JROdekakeParser().parse_train(TRAIN_PAGE, "新大阪", "敦賀")
    assert details["departure_time"] == "06:34"
    assert details["arrival_time"] == "07:54"
    assert details["platform"] == "4"
    assert details["arrival_platform"] == "31"
    assert details["stop_sequence"] == ["新大阪", "敦賀"]


def test_provider_railway_qualifier_does_not_hide_a_real_haruka_stop():
    html = TRAIN_PAGE.replace("敦賀", "関西空港")
    details = JROdekakeParser().parse_train(html, "新大阪", "関西空港(鉄道)")
    assert details["arrival_time"] == "07:54"


def test_official_unqualified_stop_matches_selected_station_region():
    details = JROdekakeParser().parse_train(TRAIN_PAGE.replace('新大阪', '福井'), '福井(福井県)', '敦賀')
    assert details['departure_time'] == '06:34'


def test_empty_first_train_name_span_does_not_hide_the_service():
    items = JROdekakeParser().parse(STATION_PAGE)
    assert len(items) == 1
    assert items[0]['train_name'] == '特急サンダーバード1号（全車指定席）'


def test_http_200_train_detail_must_operate_on_requested_day():
    calendar = '<table><tr class="month"><th>2026年10月</th></tr><tr class="day"><td>31</td></tr></table>'
    assert JROdekakeParser().parse_train(calendar + TRAIN_PAGE, '新大阪', '敦賀', '2026-10-31') == {}


def test_through_train_detail_can_continue_in_the_next_column():
    html = '''<tbody class="train-details"><tr><th>列車番号</th><td>3410M</td><td>3110M</td></tr></tbody>
    <table><tbody class="time-details">
    <tr><td>新大阪</td><td>07:49発</td><td>5</td><td></td><td></td></tr>
    <tr><td>途中境界</td><td>09:05着 直通</td><td></td><td>直通 09:22発</td><td></td></tr>
    <tr><td>敦賀</td><td></td><td></td><td>09:54着</td><td>5</td></tr>
    </tbody></table>'''
    details = JROdekakeParser().parse_train(html, '新大阪', '敦賀')
    assert details['arrival_time'] == '09:54'
    assert details['platform'] == '5'
    assert details['arrival_platform'] == '5'
    assert details['through_boundaries'] == ['途中境界']


def test_parallel_train_column_is_not_assumed_to_be_through_service():
    html = '''<table><tbody class="time-details">
    <tr><td>A</td><td>07:49発</td><td>5</td><td></td><td></td></tr>
    <tr><td>B</td><td>09:05着</td><td></td><td>09:22発</td><td></td></tr>
    <tr><td>C</td><td></td><td></td><td>09:54着</td><td>5</td></tr>
    </tbody></table>'''
    assert JROdekakeParser().parse_train(html, 'A', 'C') == {}


@pytest.mark.asyncio
async def test_official_timetable_discovers_station_and_follows_provider_links():
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = [
        '<a href="/top?id=station">新大阪駅</a>',
        '<a href="https://timetable.jr-odekake.net/station-timetable/line">京都・北陸方面</a>',
        STATION_PAGE, TRAIN_PAGE,
    ]
    scraper = JROdekakeTimetableScraper(downloader=downloader)
    timetable = await scraper.get_timetable("route", "新大阪", "敦賀",
        railway_name_jp="ＪＲ特急サンダーバード15号", search_date="2026-10-31")
    assert timetable.source == "jr_odekake"
    assert len(timetable.saturday) == 1
    exact = timetable.saturday[0]
    assert exact.arrival_time == "07:54"
    assert exact.arrival_platform == "31"
    assert exact.operating_date == "2026-10-31"
    assert exact.fare_status == "unknown"
    assert "date=20261031" in exact.source_url


@pytest.mark.asyncio
async def test_official_access_denied_is_explicit_not_an_empty_success():
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    from application.ports.scraper_port import ScraperException
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = ScraperException("JR Odekake HTTP 403")
    scraper = JROdekakeTimetableScraper(downloader=downloader)
    with pytest.raises(ScraperException, match="403"):
        await scraper.get_timetable("r", "A", "B", search_date="2026-10-31")


@pytest.mark.asyncio
async def test_sparse_official_train_at_position_ten_is_not_rejected():
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    items = ''.join(STATION_PAGE.replace('/100?', f'/{i}?') for i in range(12))
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = [items] + [
        TRAIN_PAGE if i == 9 else TRAIN_PAGE.replace('敦賀', 'short-termination') for i in range(12)]
    scraper = JROdekakeTimetableScraper(downloader)
    timetable = await scraper.get_timetable('route', '新大阪', '敦賀', timetable_id='verified-tab',
        railway_name_jp='ＪＲ特急サンダーバード15号', search_date='2026-10-31')
    assert len(timetable.saturday) == 1
    assert '/9?' in timetable.saturday[0].source_url


@pytest.mark.asyncio
async def test_official_details_paginate_without_silently_losing_later_candidates():
    from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
    items = ''.join(STATION_PAGE.replace('/100?', f'/{i}?') for i in range(30))
    downloader = AsyncMock()
    downloader.fetch_html.side_effect = [items] + [TRAIN_PAGE] * 24 + [items] + [TRAIN_PAGE] * 6
    scraper = JROdekakeTimetableScraper(downloader)
    first = await scraper.get_timetable('r', '新大阪', '敦賀', timetable_id='verified-tab',
        railway_name_jp='ＪＲ特急サンダーバード15号', search_date='2026-10-31')
    assert len(first.saturday) == 24
    assert first.next_cursor == 24
    assert downloader.fetch_html.await_count == 25
    last = await scraper.get_timetable('r', '新大阪', '敦賀', timetable_id='verified-tab',
        railway_name_jp='ＪＲ特急サンダーバード15号', search_date='2026-10-31', cursor=first.next_cursor)
    assert len(last.saturday) == 6
    assert last.complete and last.next_cursor is None
    assert len({d.id for d in first.saturday + last.saturday}) == 30
