import json
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import pytest

from application.services.search_service import SearchService
from core.exceptions import DomainException
from domain.route import Route
from domain.search import SearchRequest
from infrastructure.fakes.fake_cache import FakeCacheAdapter
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from tests.fixtures.yahoo_routes import route_page, route_spec


class FakeStationRepository:
    async def search_stations(self, _query):
        return []


class CapturingScraper:
    def __init__(self):
        self.calls = []

    async def search_routes(self, departure, arrival, time=None, date=None):
        self.calls.append({
            "departure": departure,
            "arrival": arrival,
            "time": time,
            "date": date,
        })
        return [
            Route(
                id="route-1",
                departure_station=departure,
                arrival_station=arrival,
                railway_name="Test Railway",
                total_duration="1h",
                total_fare=1000,
                transfer_count=0,
                polyline="test",
            )
        ]


@pytest.mark.asyncio
async def test_explicit_route_datetime_reaches_scraper_and_cached_route():
    scraper = CapturingScraper()
    cache = FakeCacheAdapter()
    service = SearchService(scraper, cache, FakeStationRepository())
    request = SearchRequest(
        departure_station="新大阪",
        arrival_station="敦賀",
        departure_date="2026-10-10",
        departure_time="06:00",
    )

    routes = await service.search(request)

    assert scraper.calls == [{
        "departure": "新大阪",
        "arrival": "敦賀",
        "time": "06:00",
        "date": "2026-10-10",
    }]
    assert routes[0].search_date == "2026-10-10"
    assert routes[0].search_time == "06:00"
    cached_route = await cache.get("route-1")
    assert cached_route.search_date == "2026-10-10"
    assert cached_route.search_time == "06:00"


@pytest.mark.asyncio
async def test_route_search_rejects_missing_date_or_time():
    scraper = CapturingScraper()
    service = SearchService(scraper, FakeCacheAdapter(), FakeStationRepository())

    with pytest.raises(DomainException, match="date and time"):
        await service.search(SearchRequest(
            departure_station="新大阪",
            arrival_station="敦賀",
            departure_date="2026-10-10",
        ))

    assert scraper.calls == []


class FakeYahooResponse:
    def __init__(self, text, url="https://transit.yahoo.co.jp/search/result"):
        self.text = text
        self.url = url
        self.status_code = 200

    def raise_for_status(self):
        return None


class PagedYahooClient:
    def __init__(self, first_page, second_page):
        self.first_page = first_page
        self.second_page = second_page
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append((url, kwargs.get("params")))
        if "fl=4" in url:
            return FakeYahooResponse(self.second_page, url)
        return FakeYahooResponse(self.first_page, url)


@pytest.mark.asyncio
async def test_yahoo_pagination_includes_page_two_and_preserves_source_rank():
    page_two_url = "/search/result?s=0&fl=4&tl=6"
    client = PagedYahooClient(
        route_page(
            [
                route_spec("Route 1", "06:00", "08:39"),
                route_spec("Route 2", "06:10", "08:49"),
                route_spec("Route 3", "06:20", "08:59"),
            ],
            start=1,
            end=3,
            count=6,
            next_url=page_two_url,
        ),
        route_page(
            [route_spec("ＪＲ東海道・山陽本線新快速", "07:49", "09:54", "2時間5分", "2時間5分", 0)],
            start=4,
            end=6,
            count=9,
            next_url="/search/result?s=0&fl=7&tl=9",
        ),
    )
    adapter = YahooTransitAdapter()

    routes = await adapter._fetch_yahoo_tab(
        {"from": "新大阪", "to": "敦賀", "s": "0"},
        client,
        search_date="2026-10-10",
        search_time="06:00",
        source="earliest",
    )

    assert len(client.calls) == 2
    assert any(route.transfer_count == 0 for route in routes)
    assert routes[-1].search_source == "earliest"
    assert routes[-1].source_rank == 4


@pytest.mark.asyncio
async def test_elapsed_is_primary_and_onboard_is_retained():
    client = PagedYahooClient(
        route_page(
            [route_spec("Transfer Route", "06:00", "08:39")],
            start=1,
            end=1,
            count=1,
        ),
        "",
    )
    adapter = YahooTransitAdapter()

    routes = await adapter._fetch_yahoo_tab(
        {"from": "新大阪", "to": "敦賀", "s": "0"},
        client,
        search_date="2026-10-10",
        search_time="06:00",
        source="earliest",
    )

    assert routes[0].total_duration == "2h 39m"
    assert routes[0].onboard_duration == "2h 13m"
    assert routes[0].non_riding_duration == "26m"


class FakeAsyncClientContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


@pytest.mark.asyncio
async def test_one_yahoo_source_failure_preserves_other_sources(monkeypatch):
    adapter = YahooTransitAdapter()
    successful_route = Route(
        id="success",
        departure_station="新大阪",
        arrival_station="敦賀",
        railway_name="JR",
        total_duration="2h",
        total_fare=2310,
        transfer_count=0,
        polyline="direct",
        search_date="2026-10-10",
        search_time="06:00",
    )

    async def fetch_source(params, _client, **_kwargs):
        if params.get("s") == "1":
            raise RuntimeError("cheapest failed")
        return [successful_route.model_copy(update={"id": str(params.get("s", "0"))})]

    adapter._fetch_yahoo_tab = AsyncMock(side_effect=fetch_source)
    monkeypatch.setattr(
        "infrastructure.scrapers.yahoo_transit_adapter.httpx.AsyncClient",
        lambda **_kwargs: FakeAsyncClientContext(),
    )

    routes = await adapter.search_routes(
        "新大阪", "敦賀", time="06:00", date="2026-10-10"
    )

    assert routes
    assert all(route.polyline == "direct" for route in routes)


def structured_timetable_html(entries, kinds, destinations):
    payload = {
        "props": {"pageProps": {"timetableItem": {
            "railName": "ＪＲ東海道本線",
            "master": {
                "kind": [
                    {"id": str(index + 1), "name": name}
                    for index, name in enumerate(kinds)
                ],
                "destination": [
                    {"id": str(index + 1), "name": name}
                    for index, name in enumerate(destinations)
                ],
            },
            "hourTimeTable": [{"hour": "7", "minTimeTable": entries}],
        }}}
    }
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload)
        + "</script>"
    )


@pytest.mark.asyncio
async def test_sparse_target_train_at_position_ten_is_not_rejected():
    scraper = YahooTimetableScraper()
    entries = [
        {
            "minute": str(index),
            "kindId": "1",
            "destinationId": "1" if index < 9 else "2",
            "trainId": str(index + 1),
            "trainName": "新快速",
        }
        for index in range(10)
    ]
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeYahooResponse(
        structured_timetable_html(entries, ["新快速"], ["米原", "敦賀"])
    )
    scraper._fetch_train_details = AsyncMock()

    valid = await scraper._fast_check_direction_validity(
        "/timetable/25978/123?ym=202501&d=1&kind=1",
        "新大阪",
        "敦賀",
        "ＪＲ東海道・山陽本線新快速",
        search_date="2026-10-10",
    )

    assert valid is True
    scraper._fetch_train_details.assert_not_awaited()


def test_service_identity_does_not_admit_substring_service():
    item = {
        "railName": "ＪＲ東海道本線",
        "master": {
            "kind": [
                {"id": "1", "name": "快速"},
                {"id": "2", "name": "新快速"},
            ],
            "destination": [{"id": "1", "name": "敦賀"}],
        },
        "hourTimeTable": [{
            "hour": "7",
            "minTimeTable": [
                {"minute": "1", "kindId": "1", "destinationId": "1", "trainId": "rapid"},
                {"minute": "2", "kindId": "2", "destinationId": "1", "trainId": "special-rapid"},
            ],
        }],
    }

    entries = YahooTimetableScraper._selected_service_entries(
        item, "ＪＲ東海道・山陽本線新快速"
    )

    assert [entry["trainId"] for entry in entries] == ["special-rapid"]


@pytest.mark.asyncio
async def test_timetable_validation_fetches_the_requested_date():
    scraper = YahooTimetableScraper()
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeYahooResponse(
        structured_timetable_html(
            [{
                "minute": "49",
                "kindId": "1",
                "destinationId": "1",
                "trainId": "direct",
                "trainName": "新快速",
            }],
            ["新快速"],
            ["敦賀"],
        )
    )

    valid = await scraper._fast_check_direction_validity(
        "/timetable/25978/123?ym=202501&d=1&kind=1",
        "新大阪",
        "敦賀",
        "ＪＲ東海道・山陽本線新快速",
        search_date="2026-10-10",
    )

    assert valid is True
    requested_url = scraper.client.get.await_args.args[0]
    query = parse_qs(urlparse(requested_url).query)
    assert query["ym"] == ["202610"]
    assert query["d"] == ["10"]


@pytest.mark.asyncio
async def test_timetable_detail_validation_has_a_global_request_bound():
    scraper = YahooTimetableScraper()
    entries = [
        {
            "minute": str(index),
            "kindId": "1",
            "destinationId": str(index + 1),
            "trainId": str(index + 1),
            "trainName": "普通",
        }
        for index in range(30)
    ]
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeYahooResponse(
        structured_timetable_html(
            entries,
            ["普通"],
            [f"終点{index}" for index in range(30)],
        )
    )
    scraper._fetch_train_details = AsyncMock(return_value={"arrival_time": ""})

    valid = await scraper._fast_check_direction_validity(
        "/timetable/1/2",
        "出発",
        "到着",
        "普通",
        search_date="2026-10-10",
    )

    assert valid is False
    assert scraper._fetch_train_details.await_count <= scraper.CANDIDATE_DETAIL_REQUEST_BUDGET


@pytest.mark.asyncio
async def test_timetable_candidate_tab_validation_is_bounded():
    scraper = YahooTimetableScraper()
    candidates = "".join(
        f'<dt>ＪＲ東海道本線</dt><dd><a href="/tab-{index}">方面{index}</a></dd>'
        for index in range(20)
    )
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeYahooResponse(
        f'<div id="main"><dl>{candidates}</dl></div>'
    )
    scraper._fast_check_direction_validity = AsyncMock(return_value=False)

    urls = await scraper._get_timetable_urls(
        "1",
        "出発",
        "到着",
        "ＪＲ東海道本線",
        "2026-10-10",
    )

    assert urls == []
    assert (
        scraper._fast_check_direction_validity.await_count
        == scraper.CANDIDATE_TAB_VALIDATION_LIMIT
    )


@pytest.mark.asyncio
async def test_final_timetable_uses_destination_groups_before_detail_fanout():
    scraper = YahooTimetableScraper()
    direct_count = 10
    unrelated_count = 20
    entries = [
        {
            "minute": str(index),
            "kindId": "1",
            "destinationId": "1",
            "trainId": f"direct-{index}",
            "trainName": "新快速",
        }
        for index in range(direct_count)
    ] + [
        {
            "minute": str(direct_count + index),
            "kindId": "1",
            "destinationId": str(index + 2),
            "trainId": f"unrelated-{index}",
            "trainName": "新快速",
        }
        for index in range(unrelated_count)
    ]
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeYahooResponse(
        structured_timetable_html(
            entries,
            ["新快速"],
            ["到着"] + [f"別方面{index}" for index in range(unrelated_count)],
        )
    )

    async def details_for_target(train_url, *_args):
        if "direct-" in train_url:
            return {
                "arrival_time": "09:00",
                "train_name": "新快速",
                "stop_sequence": ["出発", "到着"],
                "final_destination": "到着",
            }
        return {"arrival_time": "", "train_name": "新快速"}

    scraper._fetch_train_details = AsyncMock(side_effect=details_for_target)

    departures = await scraper._parse_timetable_page(
        "/timetable/1/2?kind=1&ym=202610&d=10",
        "出発",
        "到着",
        "新快速",
    )

    assert len(departures) == direct_count
    assert scraper._fetch_train_details.await_count <= (
        direct_count + scraper.CANDIDATE_DETAIL_REQUEST_BUDGET
    )
