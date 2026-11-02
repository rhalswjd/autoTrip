"""Named services must reach compatible tabs before bounded detail work is spent."""
import json
from unittest.mock import AsyncMock
from urllib.parse import urlparse

import pytest

from domain.timetable import DepartureInfo, Timetable
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from infrastructure.scrapers.timetable.odekake_scraper import JROdekakeTimetableScraper
from infrastructure.adapters.transport_scraper import TransportScraperAdapter
from application.ports.scraper_port import UnsupportedTimetable
from tests.regression.test_odekake_integration import STATION_PAGE, TRAIN_PAGE


class Response:
    status_code = 200
    url = 'https://transit.yahoo.co.jp/timetable/1'

    def __init__(self, text):
        self.text = text


def table(names, terminal='Beyond', line='Published line'):
    item = {'railName': line, 'master': {'kind': [{'id': '1', 'name': '特急'}],
        'destination': [{'id': str(i), 'name': terminal + str(i)} for i in range(len(names))]},
        'hourTimeTable': [{'hour': '12', 'minTimeTable': [dict(minute=str(i), kindId='1',
            destinationId=str(i), trainId=f'train-{i}', trainName=name) for i, name in enumerate(names)]}]}
    return '<script id="__NEXT_DATA__">' + json.dumps({'props': {'pageProps': {'timetableItem': item}}}) + '</script>'


@pytest.mark.parametrize('name', ['特急Other1号', '特急SuperNamed1号', '特急NamedExtra1号'])
def test_named_service_rejects_other_names_despite_matching_generic_category(name):
    from bs4 import BeautifulSoup
    item = YahooTimetableScraper._timetable_item(BeautifulSoup(table([name]), 'html.parser'))
    assert YahooTimetableScraper._selected_service_entries(item, 'JR特急Named7号') == []


def test_matching_railway_does_not_admit_only_a_broader_train_class():
    from bs4 import BeautifulSoup
    html = table(['快速'], line='JR東海道本線')
    item = YahooTimetableScraper._timetable_item(BeautifulSoup(html, 'html.parser'))
    assert YahooTimetableScraper._selected_service_entries(item, 'JR東海道本線新快速') == []


@pytest.mark.asyncio
@pytest.mark.parametrize('early_specific', [False, True])
@pytest.mark.parametrize('reaches_target', [False, True])
async def test_later_named_metadata_precedes_unrelated_or_unidentified_tabs(early_specific, reaches_target):
    scraper = YahooTimetableScraper()
    await scraper.client.aclose()
    calls = []
    index = '<div id="main"><dl>' + ''.join(
        f'<dt>JR line {i}</dt><dd><a href="/timetable/1/{i}">Other direction</a></dd>' for i in range(5)) + \
        '<dt>JR branch</dt><dd><a href="/timetable/1/target">Beyond direction</a></dd></dl></div>'
    async def get(url, **kwargs):
        path = urlparse(url).path
        if path == '/timetable/1': return Response(index)
        if path.endswith('/target'): return Response(table(['特急Named7号']))
        return Response(table([f'特急Other{i}号' if early_specific else '' for i in range(15)]))
    scraper.client = AsyncMock(); scraper.client.get.side_effect = get
    async def detail(url, *_args):
        calls.append(url)
        if '/target/' in url:
            return {'arrival_time': '15:11' if reaches_target else '', 'train_name': '特急Named7号',
                    'stop_sequence': ['Origin', 'Target'] if reaches_target else ['Origin', 'Elsewhere']}
        return {'arrival_time': '', 'train_name': '特急Other1号'}
    scraper._fetch_train_details = AsyncMock(side_effect=detail)
    urls = await scraper._get_timetable_urls('1', 'Origin', 'Target', 'JR特急Named7号', '2026-11-02')
    if reaches_target:
        assert urls and '/target?' in urls[0]
        assert len(calls) == 1 and '/target/' in calls[0]
    else:
        assert urls == []
        assert '/target/' in calls[0]
    assert len(calls) <= 12
    if early_specific:
        assert len(calls) == 1
    assert scraper.CANDIDATE_DETAIL_REQUEST_BUDGET == 12
    assert scraper.CANDIDATE_TAB_VALIDATION_LIMIT == 8


@pytest.mark.asyncio
async def test_generic_metadata_requires_exact_named_service_and_target_proof():
    scraper = YahooTimetableScraper(); await scraper.client.aclose()
    scraper.client = AsyncMock(); scraper.client.get.return_value = Response(table(['']))
    scraper._fetch_train_details = AsyncMock(return_value={'arrival_time': '15:11',
        'train_name': '特急Other7号', 'stop_sequence': ['Origin', 'Target']})
    assert not await scraper._fast_check_direction_validity('/timetable/1/2', 'Origin', 'Target', 'JR特急Named7号')


@pytest.mark.asyncio
async def test_one_metadata_failure_preserves_later_named_candidate():
    scraper = YahooTimetableScraper(); await scraper.client.aclose()
    index = '<div id="main"><dl><dt>JR line</dt><dd><a href="/bad">Other</a></dd>' + \
            '<dt>JR branch</dt><dd><a href="/good">Beyond</a></dd></dl></div>'
    async def get(url, **kwargs):
        if urlparse(url).path == '/timetable/1': return Response(index)
        if '/bad' in url: raise RuntimeError('Provider page unavailable')
        return Response(table(['特急Named7号']))
    scraper.client = AsyncMock(); scraper.client.get.side_effect = get
    scraper._fetch_train_details = AsyncMock(return_value={'arrival_time': '15:11', 'train_name': '特急Named7号'})
    urls = await scraper._get_timetable_urls('1', 'Origin', 'Target', 'JR特急Named7号', '2026-11-02')
    assert '/good?' in urls[0] and scraper._fetch_train_details.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('complete', [True, False])
async def test_official_unknown_service_empty_result_falls_back_only_when_complete(complete):
    official, other = AsyncMock(), AsyncMock()
    official.get_timetable.return_value = Timetable(route_id='r', source='jr_odekake', complete=complete,
        next_cursor=None if complete else 24)
    other.get_timetable.return_value = Timetable(route_id='r', source='yahoo')
    result = await TransportScraperAdapter(AsyncMock(), official, other).get_timetable('r', 'Origin', 'Target',
        railway_name_jp='JR特急Named7号', search_date='2026-11-02')
    assert result.source == ('yahoo' if complete else 'jr_odekake')
    assert other.get_timetable.await_count == (1 if complete else 0)


@pytest.mark.asyncio
async def test_official_named_service_can_use_conventional_tab_even_with_express_heading():
    # The combined train label denotes two portions; target stop proof still
    # comes from the exact train's selected column, never from that label alone.
    index = '<table><tr><th>在来線特急</th><td><a href="/station-timetable/express">Other</a></td></tr>' + \
            '<tr><th>Branch line</th><td><a href="/station-timetable/branch">Beyond</a></td></tr></table>'
    unrelated = STATION_PAGE.replace('サンダーバード', 'Other')
    named = STATION_PAGE.replace('特急サンダーバード1号（全車指定席）', '特急Named7号（全車指定席）・特急Other5号（全車指定席）')
    exact = TRAIN_PAGE.replace('サンダーバード1号', 'Named7号')
    downloader = AsyncMock()
    async def fetch(url):
        if '/station-timetable/express?' in url: return unrelated
        if '/station-timetable/branch?' in url: return named
        if '/train-timetable/' in url: return exact
        return index
    downloader.fetch_html.side_effect = fetch
    official = JROdekakeTimetableScraper(downloader)
    official._station_index = AsyncMock(return_value=index)
    result = await official.get_timetable('r', '新大阪', '敦賀', railway_name_jp='JR特急Named7号', search_date='2026-10-31')
    assert len(result.selected_departures()) == 1
    details = [c for c in downloader.fetch_html.await_args_list if '/train-timetable/' in c.args[0]]
    assert len(details) == 1
    assert official.DETAILS_PER_PAGE == 24 and official.MAX_TABS == 8


@pytest.mark.asyncio
@pytest.mark.parametrize('official_supports', [True, False])
async def test_unregistered_jr_named_service_prefers_proven_official_coverage_and_falls_back(official_supports):
    official, other = AsyncMock(), AsyncMock()
    exact = DepartureInfo(id='one', time='12:25', arrival_time='15:11', train_name='Named 7')
    if official_supports:
        official.get_timetable.return_value = Timetable(route_id='r', source='jr_odekake', weekday=[exact])
    else:
        official.get_timetable.side_effect = UnsupportedTimetable('No complete published ride')
    other.get_timetable.return_value = Timetable(route_id='r', source='yahoo', weekday=[exact])
    result = await TransportScraperAdapter(AsyncMock(), official, other).get_timetable('r', 'Origin', 'Target',
        railway_name_jp='JR特急Named7号', search_date='2026-11-02')
    official.get_timetable.assert_awaited_once()
    assert result.source == ('jr_odekake' if official_supports else 'yahoo')
    assert other.get_timetable.await_count == (0 if official_supports else 1)
