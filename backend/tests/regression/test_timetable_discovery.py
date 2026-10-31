import pytest
import asyncio
import json
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse
from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper
from infrastructure.scrapers.yahoo_transit_adapter import YahooTransitAdapter
from domain.timetable import Timetable
from domain.timetable import DepartureInfo

@pytest.fixture
def scraper():
    s = YahooTimetableScraper()
    s.client = AsyncMock()
    return s


class FakeResponse:
    def __init__(self, text, url="http://fake"):
        self.text = text
        self.url = url


def departure(departure_id, time, train_name):
    return DepartureInfo(
        id=departure_id,
        time=time,
        arrival_time="07:00",
        train_name=train_name,
        train_type=train_name,
    )


def test_exact_date_url_preserves_ym_and_d_and_removes_time_filter(scraper):
    exact_url = scraper._exact_date_timetable_url(
        "/timetable/25978/1340?ym=202501&d=1&hh=6&m=2&kind=1",
        "2026-08-26",
    )

    query = parse_qs(urlparse(exact_url).query)
    assert query["ym"] == ["202608"]
    assert query["d"] == ["26"]
    assert query["kind"] == ["1"]
    assert "hh" not in query
    assert "m" not in query

    candidate_date_url = scraper._exact_date_timetable_url(
        "/timetable/25978/1340?ym=202608&d=26&hh=6&m=2&kind=1",
        None,
    )
    candidate_query = parse_qs(urlparse(candidate_date_url).query)
    assert candidate_query["ym"] == ["202608"]
    assert candidate_query["d"] == ["26"]


@pytest.mark.asyncio
async def test_exact_date_result_excludes_generic_weekday_only_train(scraper):
    scraper._get_station_id = AsyncMock(return_value="25978")
    scraper._get_timetable_urls = AsyncMock(
        return_value=["/timetable/25978/1340?ym=202501&d=1&hh=6&m=2&kind=1"]
    )

    async def parse_by_url(url, *_args, **_pagination):
        query = parse_qs(urlparse(url).query)
        if query.get("ym") == ["202608"] and query.get("d") == ["26"]:
            return [departure("hikari-634", "06:11", "Hikari 634")]
        return [
            departure("nozomi-300", "06:02", "Nozomi 300"),
            departure("hikari-634", "06:11", "Hikari 634"),
        ]

    scraper._parse_timetable_page = AsyncMock(side_effect=parse_by_url)

    timetable = await scraper.get_timetable(
        "route-1",
        "新大阪",
        "名古屋",
        railway_name_jp="ＪＲ東海道新幹線",
        search_date="2026-08-26",
    )

    assert [item.time for item in timetable.weekday] == ["06:11"]
    assert timetable.saturday == []
    assert timetable.holiday == []
    scraper._get_timetable_urls.assert_awaited_once_with(
        "25978",
        "新大阪",
        "名古屋",
        "ＪＲ東海道新幹線",
        "2026-08-26",
    )


@pytest.mark.asyncio
async def test_adapter_forwards_search_date_to_timetable_scraper():
    timetable_scraper = AsyncMock()
    timetable_scraper.get_timetable.return_value = Timetable(route_id="route-1")
    adapter = YahooTransitAdapter(timetable_scraper=timetable_scraper)

    await adapter.get_timetable(
        "route-1",
        "新大阪",
        "名古屋",
        railway_name_jp="ＪＲ東海道新幹線",
        search_date="2026-08-26",
    )

    timetable_scraper.get_timetable.assert_awaited_once_with(
        "route-1",
        "新大阪",
        "名古屋",
        timetable_id=None,
        railway_name_jp="ＪＲ東海道新幹線",
        search_date="2026-08-26",
    )


def test_station_canonicalization_removes_only_no_transfer_annotation(scraper):
    assert scraper._canonical_station_name("  大聖寺【乗換不要】  ") == "大聖寺"
    assert scraper._canonical_station_name("梅田（地下鉄）") == "梅田(地下鉄)"
    assert scraper._canonical_station_name("福岡空港（鉄道）") == "福岡空港(鉄道)"
    assert scraper._canonical_station_name("高崎【新幹線】") == "高崎【新幹線】"


def test_station_detail_matching_allows_only_geographic_disambiguation(scraper):
    assert scraper._station_names_match("福井(福井県)", "福井") is True
    assert scraper._station_names_match("梅田(地下鉄)", "梅田") is False
    assert scraper._station_names_match("福岡空港(鉄道)", "福岡空港") is False


@pytest.mark.asyncio
async def test_station_lookup_uses_canonical_route_station_name(scraper):
    scraper.client.get.return_value = FakeResponse(
        '<a href="/timetable/23040">大聖寺</a>',
        "https://transit.yahoo.co.jp/station/time/search?q=%E5%A4%A7%E8%81%96%E5%AF%BA",
    )

    station_id = await scraper._get_station_id(" 大聖寺【乗換不要】 ")

    assert station_id == "23040"
    assert scraper.client.get.await_args.kwargs["params"] == {"q": "大聖寺"}


@pytest.mark.asyncio
async def test_annotated_station_succeeds_through_timetable_lookup(scraper):
    scraper.client.get.return_value = FakeResponse(
        '<a href="/timetable/23040">大聖寺</a>',
        "https://transit.yahoo.co.jp/station/time/search?q=%E5%A4%A7%E8%81%96%E5%AF%BA",
    )
    scraper._get_timetable_urls = AsyncMock(
        return_value=["/timetable/23040/999?ym=202608&d=26&kind=1"]
    )
    scraper._parse_timetable_page = AsyncMock(
        return_value=[departure("local-1", "07:00", "Local")]
    )

    timetable = await scraper.get_timetable(
        "route-annotated",
        "大聖寺【乗換不要】",
        "金沢",
        railway_name_jp="IRいしかわ鉄道線",
        search_date="2026-08-26",
    )

    assert [item.time for item in timetable.weekday] == ["07:00"]
    assert scraper.client.get.await_args.kwargs["params"] == {"q": "大聖寺"}


def train_detail_html(display_name, station_names):
    payload = {
        "props": {
            "pageProps": {
                "timetableStationTrainResult": {
                    "timetable": {
                        "displayName": display_name,
                        "stopStation": [
                            {
                                "stationName": station_name,
                                "arrivalTime": str(1000 + index * 10),
                                "departureTime": str(1000 + index * 10),
                            }
                            for index, station_name in enumerate(station_names)
                        ],
                    }
                }
            }
        }
    }
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'


def test_score_line_match(scraper):
    assert scraper._score_line_match("ＪＲ京都線", "ＪＲ京都線") == 2
    assert scraper._score_line_match("東海道新幹線", "東海道・山陽新幹線") >= 10
    assert scraper._score_line_match("ＪＲ特急サンダーバード", "特急サンダーバード") > 0

@pytest.mark.asyncio
async def test_fast_check_direction_validity(scraper):
    html = """
    <div class="tblDiaDetail">
        <table><tr><td><ul><li><a href="/timetable/fake_train">10:00</a></li></ul></td></tr></table>
    </div>
    """
    train_html = """
    <div class="station">
        <h1 class="title">大阪</h1>
    </div>
    <div class="station">
        <h1 class="title">京都</h1>
        <ul class="time"><li>10:30着</li></ul>
    </div>
    """
    scraper.client.get.side_effect = [
        FakeResponse(html, "http://fake"),
        FakeResponse(train_html, "http://fake")
    ]
    is_valid = await scraper._fast_check_direction_validity("fake_url", "大阪", "京都")
    assert is_valid == True
    assert scraper.client.get.call_count == 2


@pytest.mark.asyncio
async def test_fast_check_tries_later_train_when_first_misses_arrival(scraper):
    timetable_html = """
    <div class="tblDiaDetail"><table><tr><td><ul>
      <li><a href="/timetable/train-1">10:00</a></li>
      <li><a href="/timetable/train-2">10:30</a></li>
    </ul></td></tr></table></div>
    """
    scraper.client.get.side_effect = [
        FakeResponse(timetable_html),
        FakeResponse(train_detail_html("のぞみ", ["新大阪", "京都"])),
        FakeResponse(train_detail_html("ひかり", ["新大阪", "米原", "東京"])),
    ]

    is_valid = await scraper._fast_check_direction_validity(
        "/timetable/25978/1340", "新大阪", "米原"
    )

    assert is_valid is True
    assert scraper.client.get.call_count == 3


@pytest.mark.asyncio
async def test_fast_check_detail_request_budget_is_bounded(scraper):
    anchors = "".join(
        f'<li><a href="/timetable/train-{index}">{index:02d}:00</a></li>'
        for index in range(20)
    )
    timetable_html = (
        '<div class="tblDiaDetail"><table><tr><td><ul>'
        f'{anchors}'
        '</ul></td></tr></table></div>'
    )
    scraper.client.get.side_effect = [FakeResponse(timetable_html)] + [
        FakeResponse(train_detail_html("普通", ["出発", "途中"]))
        for _ in range(scraper.CANDIDATE_DETAIL_REQUEST_BUDGET)
    ]

    is_valid = await scraper._fast_check_direction_validity(
        "/timetable/123/456", "出発", "到着"
    )

    assert is_valid is False
    assert scraper.client.get.call_count == 1 + scraper.CANDIDATE_DETAIL_REQUEST_BUDGET

@pytest.mark.asyncio
async def test_get_timetable_urls(scraper):
    # Test that multiple valid URLs can be discovered
    html = """
    <div id="main">
        <dl>
            <dt>ＪＲ京都線</dt>
            <dd>
                <ul>
                    <li><a href="/url1">京都方面</a></li>
                    <li><a href="/url2">高槻方面</a></li>
                </ul>
            </dd>
            <dt>ＪＲ特急サンダーバード</dt>
            <dd>
                <ul>
                    <li><a href="/url3">金沢方面</a></li>
                </ul>
            </dd>
        </dl>
    </div>
    """
    scraper.client.get.return_value = FakeResponse(html)

    # 1. Exact text match in 'dir'
    urls = await scraper._get_timetable_urls("123", "大阪", "京都", "ＪＲ京都線")
    assert "/url1" in urls

    # 2. Fast check fallback for high score tabs
    scraper._fast_check_direction_validity = AsyncMock(return_value=True)
    urls = await scraper._get_timetable_urls("123", "大阪", "金沢", "ＪＲ特急サンダーバード")
    assert "/url3" in urls

@pytest.mark.asyncio
async def test_get_timetable_urls_identity_coupling(scraper):
    """CASE T5: Ensure score 0 tabs (like JR Kyoto Line) are checked if searched for Thunderbird."""
    html = """
    <div id="main">
        <dl>
            <dt>ＪＲ京都線</dt>
            <dd><ul><li><a href="/url1">高槻方面</a></li></ul></dd>
            <dt>ＪＲ関西空港線特急</dt>
            <dd><ul><li><a href="/url2">関西空港方面</a></li></ul></dd>
        </dl>
    </div>
    """
    scraper.client.get.return_value = FakeResponse(html)

    # Mock fast check: url1 goes to destination, url2 does not.
    async def mock_fast_check(url, dep, arr, *_args):
        return url == "/url1"
    scraper._fast_check_direction_validity = AsyncMock(side_effect=mock_fast_check)

    # Score for JR Kyoto Line against Thunderbird is 0. Score for Kansai Airport Express is > 0.
    urls = await scraper._get_timetable_urls("123", "新大阪", "敦賀", "ＪＲ特急サンダーバード")

    # Before fix, /url1 would be skipped because its score is 0.
    # After fix, /url1 MUST be included because fast check returns True.
    assert "/url1" in urls, "Score 0 tabs must be checked for validity"


@pytest.mark.asyncio
async def test_selected_shinkansen_service_excludes_local_candidate(scraper):
    scraper.client.get.return_value = FakeResponse(
        """
        <div id="main"><dl>
          <dt>ＪＲ東海道新幹線</dt>
          <dd><a href="/shinkansen">東京・名古屋 方面</a></dd>
          <dt>ＪＲ京都線</dt>
          <dd><a href="/local">米原 方面</a></dd>
        </dl></div>
        """
    )
    scraper._fast_check_direction_validity = AsyncMock(return_value=True)

    urls = await scraper._get_timetable_urls(
        "25978", "新大阪", "米原", "ＪＲ新幹線ひかり(東京−博多)"
    )

    assert urls == ["/shinkansen"]


def test_structured_timetable_keeps_only_selected_service(scraper):
    item = {
        "railName": "ＪＲ東海道新幹線",
        "master": {
            "kind": [
                {"id": "1", "name": "のぞみ"},
                {"id": "2", "name": "ひかり"},
            ],
            "destination": [{"id": "1", "name": "東京"}],
        },
        "hourTimeTable": [{
            "hour": "6",
            "minTimeTable": [
                {"minute": "0", "kindId": "1", "destinationId": "1", "trainId": "1", "trainName": "のぞみ230号"},
                {"minute": "11", "kindId": "2", "destinationId": "1", "trainId": "2", "trainName": "ひかり634号"},
            ],
        }],
    }

    departures = scraper._structured_departures(
        item,
        "/timetable/25978/1340?kind=1",
        "ＪＲ新幹線ひかり(東京−博多)",
    )

    assert len(departures) == 1
    assert departures[0].id == "2"
    assert departures[0].time == "06:11"

    generic_line_departures = scraper._structured_departures(
        item,
        "/timetable/25978/1340?kind=1",
        "ＪＲ東海道新幹線",
    )
    assert len(generic_line_departures) == 2

    unrelated_service_departures = scraper._structured_departures(
        item,
        "/timetable/25978/1340?kind=1",
        "ＪＲ特急サンダーバード",
    )
    assert unrelated_service_departures == []


@pytest.mark.asyncio
async def test_train_detail_cache_reuses_same_url(scraper):
    scraper.client.get.return_value = FakeResponse(
        train_detail_html("ひかり634号", ["新大阪", "米原"])
    )
    semaphore = asyncio.Semaphore(1)

    first = await scraper._fetch_train_details("/train/2", "新大阪", "米原", semaphore)
    second = await scraper._fetch_train_details("/train/2", "新大阪", "米原", semaphore)

    assert first == second
    assert scraper.client.get.call_count == 1


@pytest.mark.asyncio
async def test_candidate_validation_concurrency_is_bounded(scraper):
    candidates = "".join(
        f"<dt>ＪＲ路線{index}</dt><dd><a href='/line-{index}'>方面{index}</a></dd>"
        for index in range(5)
    )
    scraper.client.get.return_value = FakeResponse(f"<div id='main'><dl>{candidates}</dl></div>")
    active = 0
    max_active = 0

    async def track_concurrency(*_args):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return True

    scraper._fast_check_direction_validity = AsyncMock(side_effect=track_concurrency)

    await scraper._get_timetable_urls("123", "出発", "到着", "")

    assert max_active <= 2

@pytest.mark.asyncio
async def test_merge_departures(scraper):
    deps1 = [
        DepartureInfo(id="1", time="10:00", arrival_time="10:30", train_name="Thunderbird", train_type="Thunderbird", direction="Kanazawa", metadata={"original_train_name": "Thunderbird"}),
        DepartureInfo(id="2", time="11:00", arrival_time="", train_name="Thunderbird", train_type="Thunderbird", direction="Kanazawa", metadata={"original_train_name": "Thunderbird"}),
    ]
    deps2 = [
        DepartureInfo(id="3", time="10:00", arrival_time="", train_name="Thunderbird", train_type="Thunderbird", direction="Kanazawa", metadata={"original_train_name": "Thunderbird"}),
        DepartureInfo(id="4", time="12:00", arrival_time="", train_name="Shirasagi", train_type="Shirasagi", direction="Kanazawa", metadata={"original_train_name": "Shirasagi"}),
    ]

    merged = scraper._merge_departures(deps1 + deps2)
    assert len(merged) == 3
    assert merged[0].time == "10:00"
    assert merged[0].arrival_time == "10:30"  # preferred the one with arrival time
    assert merged[1].time == "11:00"
    assert merged[2].time == "12:00"

@pytest.mark.asyncio
async def test_empty_candidates_returns_empty(scraper):
    scraper.client.get.return_value = FakeResponse("<div id='main'></div>")
    urls = await scraper._get_timetable_urls("123", "A", "B", "C")
    assert urls == []

@pytest.mark.asyncio
async def test_parse_timetable_page(scraper):
    # Trains with the same type/direction still require their own detail arrival.
    html = """
    <table class="tblDiaDetail">
        <tr>
            <td class="hour">10</td>
            <td>
                <ul>
                    <li>
                        <a href="/t1">
                            <dt>00</dt>
                            <dd class="trainType">特急サンダーバード</dd>
                            <dd class="trainFor">金沢</dd>
                        </a>
                    </li>
                    <li>
                        <a href="/t2">
                            <dt>30</dt>
                            <dd class="trainType">特急サンダーバード</dd>
                            <dd class="trainFor">金沢</dd>
                        </a>
                    </li>
                </ul>
            </td>
        </tr>
    </table>
    """
    scraper.client.get.return_value = FakeResponse(html)
    scraper._fetch_train_details = AsyncMock(side_effect=[
        {
            "arrival_time": "12:00",
            "train_name": "Thunderbird",
            "stop_sequence": ["大阪", "京都", "金沢"],
            "final_destination": "金沢",
        },
        {
            "arrival_time": "12:45",
            "train_name": "Thunderbird",
            "stop_sequence": ["大阪", "京都", "金沢"],
            "final_destination": "金沢",
        },
    ])

    deps = await scraper._parse_timetable_page("/test", "大阪", "金沢")
    assert len(deps) == 2
    assert deps[0].time == "10:00"
    assert deps[0].arrival_time == "12:00"
    assert deps[1].time == "10:30"
    assert deps[1].arrival_time == "12:45"
    assert deps[0].metadata["stop_sequence"] == ["大阪", "京都", "金沢"]
    assert deps[0].metadata["final_destination"] == "金沢"
    assert scraper._fetch_train_details.call_count == 2
