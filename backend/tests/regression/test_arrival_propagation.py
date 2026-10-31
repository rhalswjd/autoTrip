import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from infrastructure.scrapers.timetable.yahoo_timetable_scraper import YahooTimetableScraper


class FakeResponse:
    def __init__(self, text: str, url: str = "https://transit.yahoo.co.jp/fake"):
        self.text = text
        self.url = url


def train_detail_html(display_name: str, stops: list[dict[str, str | None]]) -> str:
    payload = {
        "props": {
            "pageProps": {
                "timetableStationTrainResult": {
                    "timetable": {
                        "displayName": display_name,
                        "stopStation": stops,
                    }
                }
            }
        }
    }
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'


@pytest.mark.asyncio
async def test_arrival_target_uses_exact_station_name():
    scraper = YahooTimetableScraper()
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeResponse(
        train_detail_html(
            "普通",
            [
                {"stationName": "敦賀", "departureTime": "605"},
                {"stationName": "西金沢", "arrivalTime": "824", "departureTime": "825"},
                {"stationName": "金沢", "arrivalTime": "830", "departureTime": None},
            ],
        )
    )

    details = await scraper._fetch_train_details(
        "/timetable/23831/8661/41206?kind=1&hh=6&mm=5",
        "敦賀",
        "金沢",
        asyncio.Semaphore(1),
    )

    assert details["arrival_time"] == "08:30"
    assert details["train_name"] == "普通"


@pytest.mark.asyncio
async def test_each_departure_uses_its_own_detail_duration():
    scraper = YahooTimetableScraper()
    scraper.client = AsyncMock()
    scraper.client.get.return_value = FakeResponse(
        """
        <table class="tblDiaDetail">
          <tr><td class="hour">10</td><td><ul>
            <li><a href="/t1"><dt>00</dt><dd class="trainType">普通</dd><dd class="trainFor">金沢</dd></a></li>
            <li><a href="/t2"><dt>30</dt><dd class="trainType">普通</dd><dd class="trainFor">金沢</dd></a></li>
          </ul></td></tr>
        </table>
        """
    )
    scraper._fetch_train_details = AsyncMock(
        side_effect=[
            {"arrival_time": "12:00", "train_name": "普通"},
            {"arrival_time": "12:45", "train_name": "普通"},
        ]
    )

    departures = await scraper._parse_timetable_page("/test", "大阪", "金沢")

    assert [departure.arrival_time for departure in departures] == ["12:00", "12:45"]
    assert scraper._fetch_train_details.call_count == 2
