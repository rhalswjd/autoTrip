"""On-demand official JR West station and exact-train timetable adapter."""
import re
from urllib.parse import urlencode, urljoin, urlparse, parse_qsl, urlunparse

from bs4 import BeautifulSoup

from application.ports.scraper_port import ScraperException
from domain.journey import canonical_station, service_family, unqualified_station_name
from domain.timetable import Timetable, DepartureInfo, calendar_type_for_date
from infrastructure.scrapers.timetable.odekake_downloader import JROdekakeDownloader
from infrastructure.scrapers.timetable.odekake_parser import JROdekakeParser


def service_identity(value: str) -> str:
    value = service_family(value).replace("ＪＲ", "").replace("JR", "")
    if "新幹線" in value:
        return "新幹線"
    if "特急" in value:
        return value.split("特急", 1)[1].strip() or "特急"
    for label in ("通勤特快", "特別快速", "通勤快速", "区間快速", "新快速", "快速", "普通", "急行"):
        if value.endswith(label):
            return label
    return value.strip()


def destination_identity(value: str) -> str:
    # Direction notes such as a via-line annotation are not part of the terminal.
    # This only prioritizes cheap metadata; exact stop details decide eligibility.
    value = service_family(value).removesuffix("行")
    return canonical_station(value)


class JROdekakeTimetableScraper:
    MAX_TABS = 8
    DETAILS_PER_PAGE = 24
    HOST = "https://timetable.jr-odekake.net"
    STATION_HOST = "https://eki.jr-odekake.net"

    def __init__(self, downloader=None):
        self.downloader = downloader or JROdekakeDownloader()
        self.parser = JROdekakeParser()

    @staticmethod
    def exact_date_url(url: str, search_date: str) -> str:
        parsed = urlparse(url)
        query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "date"]
        query.append(("date", search_date.replace("-", "")))
        return urlunparse(parsed._replace(query=urlencode(query)))

    async def _station_index(self, departure: str) -> str:
        station_query = unqualified_station_name(departure)
        url = self.STATION_HOST + "/search_free?" + urlencode({"keyword": station_query})
        html = await self.downloader.fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        timetable = next((a.get("href", "") for a in soup.select("a[href]")
                          if "時刻表" == a.get_text(strip=True)
                          and "timetable.jr-odekake.net" in a.get("href", "")), None)
        if timetable:
            return await self.downloader.fetch_html(timetable)
        station_links = list(dict.fromkeys(a.get("href", "") for a in soup.select("a[href]")
                             if "/top?" in a.get("href", "")
                             and canonical_station(a.get_text(strip=True).removesuffix("駅")) == station_query))
        if len(station_links) != 1:
            raise ScraperException(f"JR Odekake does not publish a matching station timetable for {departure}")
        html = await self.downloader.fetch_html(urljoin(self.STATION_HOST, station_links[0]))
        soup = BeautifulSoup(html, "html.parser")
        timetable = next((a.get("href", "") for a in soup.select("a[href]")
                          if a.get_text(strip=True) == "時刻表"), None)
        if timetable:
            return await self.downloader.fetch_html(urljoin(self.STATION_HOST, timetable))
        return html

    def _tabs(self, html: str, railway: str, arrival: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        result = []
        is_shinkansen = "新幹線" in railway
        is_express = "特急" in railway or "急行" in railway
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            match = re.fullmatch(r"link\((\d+)\)", link.get("onclick", "").strip().rstrip(";"))
            if match:
                href = "/station-timetable/" + match[1]
            if "/station-timetable/" not in href:
                continue
            row = link.find_parent("tr")
            heading = row.find("th").get_text(strip=True) if row and row.find("th") else ""
            if heading:
                if is_shinkansen != ("新幹線" in heading):
                    continue
                if not is_shinkansen and is_express != ("特急" in heading or "急行" in heading):
                    continue
            priority = 0 if canonical_station(arrival) in link.get_text(strip=True) else 1
            result.append((priority, urljoin(self.HOST, href)))
        return list(dict.fromkeys(url for _, url in sorted(result, key=lambda pair: pair[0])))[:self.MAX_TABS]

    async def get_timetable(self, route_id: str, departure: str, arrival: str,
                            timetable_id=None, railway_name_jp: str = "",
                            search_date: str | None = None, cursor: int = 0) -> Timetable:
        if not search_date:
            raise ValueError("Official timetable requires the Route search date")
        selected_calendar = calendar_type_for_date(search_date)
        if timetable_id:
            tabs = [self.HOST + "/station-timetable/" + str(timetable_id)]
        else:
            tabs = self._tabs(await self._station_index(departure), railway_name_jp, arrival)
        if not tabs:
            return Timetable(route_id=route_id, source="jr_odekake", selected_calendar=selected_calendar,
                             status="unsupported", message="JR Odekake has no compatible published direction for this leg")
        entries = []
        expected_identity = service_identity(railway_name_jp)
        for tab in tabs:
            url = self.exact_date_url(tab, search_date)
            html = await self.downloader.fetch_html(url)
            soup = BeautifulSoup(html, "html.parser")
            displayed = soup.select_one(".select-date .emphasis, .select-date span")
            if displayed:
                actual = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", displayed.get_text())
                if actual and f"{int(actual[1]):04}-{int(actual[2]):02}-{int(actual[3]):02}" != search_date:
                    raise ScraperException("JR Odekake returned a different operating date")
            for item in self.parser.parse(html):
                actual_identity = service_identity(item["train_name"])
                if expected_identity == "新幹線":
                    pass  # The verified direction tab supplies the Shinkansen corridor.
                elif expected_identity and actual_identity != expected_identity:
                    if not any(marker in expected_identity for marker in ("線", "鉄道")):
                        continue
                link = item["metadata"].get("link")
                if not link:
                    continue
                item["source_url"] = self.exact_date_url(urljoin(self.HOST, link), search_date)
                entries.append(item)
        unique = {item["source_url"]: item for item in entries}
        entries = sorted(unique.values(), key=lambda item: (
            destination_identity(item["destination"]) != canonical_station(arrival), item["time"]))
        page = entries[cursor:cursor + self.DETAILS_PER_PAGE]
        departures = []
        for item in page:
            details = self.parser.parse_train(await self.downloader.fetch_html(item["source_url"]), departure, arrival, search_date)
            if not details or details["departure_time"] != item["time"]:
                continue
            departures.append(DepartureInfo(
                id=item["source_url"], time=details["departure_time"], arrival_time=details["arrival_time"],
                train_name=details["train_name"] or item["train_name"], train_type=service_identity(item["train_name"]),
                platform=details["platform"], arrival_platform=details["arrival_platform"],
                direction=item["destination"], source="jr_odekake", source_url=item["source_url"],
                operating_date=search_date, train_number=details["train_number"],
                metadata={"stop_sequence": details["stop_sequence"], "stops": details["stops"]},
            ))
        next_cursor = cursor + len(page)
        complete = next_cursor >= len(entries)
        departures.sort(key=lambda entry: entry.time)
        return Timetable(route_id=route_id, source="jr_odekake", source_url=self.exact_date_url(tabs[0], search_date),
                         selected_calendar=selected_calendar,
                         **{selected_calendar.value: departures}, complete=complete,
                         next_cursor=None if complete else next_cursor,
                         total_candidates=len(entries),
                         message="" if complete else "More official departures are available; load the next page")
