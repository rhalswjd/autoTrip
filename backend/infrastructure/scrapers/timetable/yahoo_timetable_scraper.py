import asyncio
import json
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
import unicodedata
from datetime import date as Date
from urllib.parse import parse_qsl, urlencode, urlunparse

from domain.timetable import Timetable, DepartureInfo, calendar_type_for_date
from domain.station_identity import qualified_station_name
from domain.service_identity import has_named_service, service_match_strength, service_identities
from core.logger import logger
from application.ports.scraper_port import ScraperException
from domain.platform import PlatformStatus
from infrastructure.services.platform_information import read_platform

class YahooTimetableScraper:
    CANDIDATE_VALIDATION_CONCURRENCY = 2
    CANDIDATE_TAB_VALIDATION_LIMIT = 8
    CANDIDATE_DETAIL_REQUEST_BUDGET = 12
    TRAIN_DETAIL_CONCURRENCY = 3
    FINAL_DEPARTURE_DETAIL_BUDGET = 48

    def __init__(self):
        self.base_url = "https://transit.yahoo.co.jp"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._requests = {'station': 0, 'timetable': 0, 'detail': 0, 'total': 0, 'cache_hits': 0}
        self.client = httpx.AsyncClient(follow_redirects=True, headers=self.headers, timeout=15.0,
            event_hooks={'response': [self._record_response]})
        from infrastructure.services.translation_service import TranslationService
        self.translation_service = TranslationService()
        self._train_detail_cache: Dict[tuple[str, str, str], dict] = {}
        self._rate_limited = False

    async def _record_response(self, response: httpx.Response) -> None:
        path = response.url.path
        is_detail = '/train/' in path or re.fullmatch(r'/timetable/\d+/\d+/\d+/?', path)
        kind = 'station' if '/station/' in path else 'detail' if is_detail else 'timetable'
        self._requests[kind] += 1
        self._requests['total'] += 1
        status = f'http_{response.status_code}'
        self._requests[status] = self._requests.get(status, 0) + 1
        if response.status_code == 429:
            self._rate_limited = True

    def statistics(self) -> dict:
        return dict(self._requests)

    def _raise_for_rate_limit(self, response: Any) -> None:
        if getattr(response, "status_code", None) == 429:
            self._rate_limited = True
            raise RuntimeError("Yahoo Transit rate limit (HTTP 429)")

    async def _get_station_id(self, station_name: str) -> Optional[str]:
        canonical_station_name = self._canonical_station_name(station_name)
        url = f"{self.base_url}/station/time/search"
        params = {"q": canonical_station_name}
        try:
            r = await self.client.get(url, params=params)
            self._raise_for_rate_limit(r)
            if "/timetable/" in str(r.url):
                match = re.search(r'/timetable/(\d+)', str(r.url))
                if match:
                    return match.group(1)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if '/timetable/' in href and self._station_names_match(canonical_station_name, a.text):
                    match = re.search(r'/timetable/(\d+)', href)
                    if match:
                        return match.group(1)
            return None
        except Exception as e:
            if self._rate_limited:
                raise
            logger.error(f"Error getting station ID for {station_name}: {e}")
            return None

    def _score_line_match(self, dt_text: str, railway_name_jp: str) -> int:
        if not railway_name_jp:
            return 0
        generics = ["ＪＲ", "線", "号"]
        clean_dt = dt_text
        clean_railway = railway_name_jp
        for g in generics:
            clean_dt = clean_dt.replace(g, "")
            clean_railway = clean_railway.replace(g, "")

        score = 0
        for char in clean_dt:
            if char in clean_railway:
                score += 1
        if "新幹線" in dt_text and "新幹線" in railway_name_jp:
            score += 10
        return score

    @staticmethod
    def _canonical_station_name(station_name: str) -> str:
        normalized = qualified_station_name(station_name)
        normalized = re.sub(r"\s*【\s*乗換不要\s*】\s*", "", normalized)
        return normalized.strip()

    @staticmethod
    def _date_query_params(search_date: str | None) -> Dict[str, str]:
        if not search_date:
            return {}
        try:
            parsed_date = Date.fromisoformat(search_date)
        except ValueError as exc:
            raise ValueError(
                f"Invalid route search_date {search_date!r}; expected YYYY-MM-DD"
            ) from exc
        return {
            "ym": parsed_date.strftime("%Y%m"),
            "d": str(parsed_date.day),
        }

    @staticmethod
    def _day_category(search_date: str | None) -> str:
        return calendar_type_for_date(search_date).value

    @classmethod
    def _exact_date_timetable_url(
        cls,
        timetable_url: str,
        search_date: str | None,
    ) -> str:
        parsed = urlparse(timetable_url)
        replaced_date_keys = {"ym", "d"} if search_date else set()
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in {"hh", "m", "mm"} | replaced_date_keys
        ]
        existing_keys = {key for key, _ in query}
        query.extend(cls._date_query_params(search_date).items())
        if "kind" not in existing_keys:
            kind_by_category = {"weekday": "1", "saturday": "2", "holiday": "4"}
            query.append(("kind", kind_by_category[cls._day_category(search_date)]))
        return urlunparse(parsed._replace(query=urlencode(query)))

    @classmethod
    def _station_names_match(cls, expected: str, actual: str) -> bool:
        from domain.station_identity import station_orthography_matches
        return station_orthography_matches(cls._canonical_station_name(expected), cls._canonical_station_name(actual))

    @staticmethod
    def _normalize_identity(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value or "").lower()
        return re.sub(r"[\s・()（）\-−ー]", "", normalized)

    @classmethod
    def _transport_mode(cls, value: str) -> str:
        normalized = cls._normalize_identity(value)
        if "新幹線" in normalized:
            return "shinkansen"
        if any(marker in normalized for marker in ("metro", "subway", "地下鉄", "メトロ", "都営")):
            return "subway"
        if "バス" in normalized or "bus" in normalized:
            return "bus"
        return "rail"

    @classmethod
    def _is_candidate_mode_compatible(cls, line_name: str, railway_name_jp: str) -> bool:
        if not railway_name_jp:
            return True
        return cls._transport_mode(line_name) == cls._transport_mode(railway_name_jp)

    @staticmethod
    def _next_data(soup: BeautifulSoup) -> dict:
        script = soup.select_one("script#__NEXT_DATA__")
        if not script or not script.string:
            return {}
        try:
            return json.loads(script.string)
        except (TypeError, json.JSONDecodeError) as exc:
            logger.warning(f"Failed to parse Yahoo __NEXT_DATA__: {exc}")
            return {}

    @classmethod
    def _timetable_item(cls, soup: BeautifulSoup) -> dict:
        return cls._next_data(soup).get("props", {}).get("pageProps", {}).get("timetableItem", {})

    @classmethod
    def _selected_service_entries(cls, item: dict, railway_name_jp: str) -> List[dict]:
        kind_names = {
            str(kind.get("id", "")): str(kind.get("name", ""))
            for kind in item.get("master", {}).get("kind", [])
        }
        destination_names = {
            str(destination.get("id", "")): str(destination.get("name", ""))
            for destination in item.get("master", {}).get("destination", [])
        }
        selected_identity = cls._normalize_identity(railway_name_jp)
        entries = []
        for hour_item in item.get("hourTimeTable", []):
            hour = str(hour_item.get("hour", ""))
            for raw_entry in hour_item.get("minTimeTable", []):
                entry = dict(raw_entry)
                entry["hour"] = hour
                entry["kind_name"] = kind_names.get(str(entry.get("kindId", "")), "")
                entry["destination_name"] = destination_names.get(str(entry.get("destinationId", "")), "")
                entries.append(entry)

        if not selected_identity:
            return entries

        matching_entries = []
        for entry in entries:
            # A supplied train name outranks the broad kind field: a different
            # named 特急 must never fall back to its generic 特急 category.
            label = str(entry.get('trainName') or entry.get('kind_name') or '')
            strength = service_match_strength(railway_name_jp, label)
            if strength:
                matching_entries.append((entry, strength))
        if matching_entries:
            # Exact identities outrank category-only evidence. 快速 and 新快速
            # are distinct classes, as are two different named limited expresses.
            best_strength = max(strength for _, strength in matching_entries)
            return [
                entry
                for entry, strength in matching_entries
                if strength == best_strength
            ]

        if has_named_service(railway_name_jp):
            return []
        if any(identity.category and identity.category != '新幹線' for identity in service_identities(railway_name_jp)):
            return []  # A matching corridor cannot turn 快速 into 新快速, etc.
        line_identity = cls._normalize_identity(item.get("railName", ""))
        if line_identity and line_identity == selected_identity:
            return entries

        explicit_service_markers = ("特急", "新快速", "快速", "急行", "普通")
        if any(marker in selected_identity for marker in explicit_service_markers):
            return []

        if "新幹線" in selected_identity:
            selected_corridor = selected_identity.split("新幹線", 1)[0].replace("jr", "")
            line_corridor = line_identity.split("新幹線", 1)[0].replace("jr", "")
            if selected_corridor and selected_corridor != line_corridor:
                return []
        return entries

    @classmethod
    def _structured_train_urls(cls, item: dict, timetable_url: str, railway_name_jp: str) -> List[str]:
        entries = cls._selected_service_entries(item, railway_name_jp)
        urls = []
        seen = set()
        for entry in entries:
            hour = str(entry.get("hour", ""))
            minute = str(entry.get("minute", ""))
            train_id = str(entry.get("trainId", ""))
            if not hour or not minute or not train_id:
                continue
            signature = (
                hour,
                minute,
                entry.get("trainName", ""),
                entry.get("vendorTrainId") or train_id,
            )
            if signature in seen:
                continue
            seen.add(signature)
            urls.append(cls._train_detail_url(timetable_url, train_id, hour, minute))
        return urls

    @staticmethod
    def _train_detail_url(timetable_url: str, train_id: str, hour: str, minute: str) -> str:
        parsed = urlparse(timetable_url)
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in {"hh", "m", "mm"}
        ]
        query.extend((("hh", str(int(hour))), ("mm", str(int(minute)))))
        path = f"{parsed.path.rstrip('/')}/{train_id}"
        return urlunparse(parsed._replace(path=path, query=urlencode(query)))

    @classmethod
    def _representative_train_urls(
        cls,
        item: dict,
        timetable_url: str,
        railway_name_jp: str,
    ) -> List[str]:
        """Return one detail URL per structured service/destination group.

        Sampling groups avoids chronological first-N bias while the caller's
        global request budget keeps validation bounded.
        """
        representatives = []
        seen_groups = set()
        for entry in cls._selected_service_entries(item, railway_name_jp):
            destination = cls._normalize_identity(entry.get("destination_name", ""))
            kind = cls._normalize_identity(entry.get("kind_name", ""))
            train = service_identities(str(entry.get('trainName') or entry.get('kind_name') or ''))
            group = (kind, train, destination)
            if group in seen_groups:
                continue
            seen_groups.add(group)
            hour = str(entry.get("hour", ""))
            minute = str(entry.get("minute", ""))
            train_id = str(entry.get("trainId", ""))
            if hour and minute and train_id:
                representatives.append(
                    cls._train_detail_url(timetable_url, train_id, hour, minute)
                )
        return representatives

    @classmethod
    def _candidate_train_urls(cls, soup: BeautifulSoup, timetable_url: str, railway_name_jp: str) -> List[str]:
        item = cls._timetable_item(soup)
        if item:
            return cls._structured_train_urls(item, timetable_url, railway_name_jp)

        urls = []
        for anchor in soup.select('.tblDiaDetail td li a'):
            href = anchor.get('href')
            if href and '/timetable/' in href and href not in urls:
                urls.append(href)
        return urls

    async def _fast_check_direction_validity(
        self,
        timetable_url: str,
        departure_station: str,
        arrival_station: str,
        railway_name_jp: str = "",
        search_date: str | None = None,
        detail_budget: dict | None = None,
        prefetched_soup: BeautifulSoup | None = None,
    ) -> bool:
        try:
            exact_date_url = (
                self._exact_date_timetable_url(timetable_url, search_date)
                if search_date
                else timetable_url
            )
            if prefetched_soup is None:
                r = await self.client.get(urljoin(self.base_url, exact_date_url))
                self._raise_for_rate_limit(r)
                soup = BeautifulSoup(r.text, 'html.parser')
            else:
                soup = prefetched_soup
            item = self._timetable_item(soup)
            if item:
                selected_entries = self._selected_service_entries(item, railway_name_jp)
                if any(
                    self._station_names_match(
                        arrival_station,
                        str(entry.get("destination_name", "")),
                    )
                    for entry in selected_entries
                    if entry.get("destination_name")
                ):
                    return True
                train_urls = self._representative_train_urls(
                    item,
                    exact_date_url,
                    railway_name_jp,
                )
            else:
                train_urls = self._candidate_train_urls(
                    soup,
                    exact_date_url,
                    railway_name_jp,
                )
            if not train_urls:
                return False

            budget = detail_budget if detail_budget is not None else {
                "remaining": self.CANDIDATE_DETAIL_REQUEST_BUDGET
            }
            semaphore = asyncio.Semaphore(1)
            for train_url in train_urls:
                if budget["remaining"] <= 0:
                    break
                budget["remaining"] -= 1
                details = await self._fetch_train_details(
                    train_url,
                    departure_station,
                    arrival_station,
                    semaphore,
                )
                if (details.get("arrival_time") and (not has_named_service(railway_name_jp)
                        or service_match_strength(railway_name_jp, details.get('train_name', '')) == 2)):
                    return True
            return False
        except Exception as e:
            if self._rate_limited:
                raise
            logger.warning(f"Error checking direction validity for {timetable_url}: {e}")
            return False

    async def _get_timetable_urls(
        self,
        station_id: str,
        departure_station: str,
        arrival_station: str,
        railway_name_jp: str,
        search_date: str | None = None,
    ) -> List[str]:
        url = f"{self.base_url}/timetable/{station_id}"
        try:
            date_params = self._date_query_params(search_date)
            r = await self.client.get(url, params=date_params or None)
            self._raise_for_rate_limit(r)
            soup = BeautifulSoup(r.text, 'html.parser')
            main_div = soup.select_one('#main') or soup

            candidates = []
            for dt in main_div.find_all('dt'):
                line_name = dt.text.strip()
                if not self._is_candidate_mode_compatible(line_name, railway_name_jp):
                    continue
                score = self._score_line_match(line_name, railway_name_jp)
                dd = dt.find_next_sibling('dd')
                if dd:
                    for a in dd.find_all('a'):
                        dir_name = a.text.strip()
                        href = a.get('href')
                        if href:
                            candidates.append({
                                'line': line_name,
                                'dir': dir_name,
                                'url': href,
                                'score': score
                            })

            if not candidates:
                return []

            candidates.sort(key=lambda candidate: candidate['score'], reverse=True)
            unique_candidates = {}
            for candidate in candidates:
                identity = self._exact_date_timetable_url(candidate['url'], search_date)
                unique_candidates.setdefault(identity, candidate)
            candidates = list(unique_candidates.values())
            candidates = candidates[:self.CANDIDATE_TAB_VALIDATION_LIMIT]
            detail_budget = {"remaining": self.CANDIDATE_DETAIL_REQUEST_BUDGET}

            # Read at most the existing tab limit before any detail request.
            # Specific trainName metadata exists here, even when all station
            # headings have zero line score. Strong evidence is inspected before
            # category-only/HTML-only candidates can spend the shared budget.
            if has_named_service(railway_name_jp):
                prepared = []
                for candidate in candidates:
                    candidate_url = self._exact_date_timetable_url(candidate['url'], search_date)
                    try:
                        response = await self.client.get(urljoin(self.base_url, candidate_url))
                        self._raise_for_rate_limit(response)
                    except Exception as exc:
                        if self._rate_limited:
                            raise
                        logger.warning('Timetable candidate metadata unavailable: %s (%s)', candidate_url, type(exc).__name__)
                        continue
                    soup = BeautifulSoup(response.text, 'html.parser')
                    item = self._timetable_item(soup)
                    entries = self._selected_service_entries(item, railway_name_jp) if item else []
                    if item and not entries:
                        continue
                    strength = max((service_match_strength(railway_name_jp,
                        str(e.get('trainName') or e.get('kind_name') or '')) for e in entries), default=0)
                    destination = any(self._station_names_match(arrival_station, str(e.get('destination_name', ''))) for e in entries)
                    prepared.append({**candidate, 'soup': soup, 'strength': strength, 'destination': destination})
                candidates = sorted(prepared, key=lambda c: (c['strength'], c['destination']), reverse=True)

            # A selected RouteSegment needs one compatible direction tab. Check
            # candidates in score order and stop at the first proven match so a
            # successful cheap metadata check does not trigger every remaining
            # tab request.
            for candidate in candidates:
                candidate_url = (
                    self._exact_date_timetable_url(candidate['url'], search_date)
                    if search_date
                    else candidate['url']
                )
                if not has_named_service(railway_name_jp) and self._canonical_station_name(arrival_station) in self._canonical_station_name(candidate['dir']):
                    return [candidate_url]
                is_valid = await self._fast_check_direction_validity(
                    candidate_url,
                    departure_station,
                    arrival_station,
                    railway_name_jp,
                    search_date,
                    detail_budget,
                    candidate.get('soup'),
                )
                if is_valid:
                    return [candidate_url]
            return []
        except Exception as e:
            if self._rate_limited:
                raise
            logger.error(f"Error getting timetable urls for {station_id}: {e}")
            return []

    async def _fetch_train_details(self, train_url: str, departure_station: str, arrival_station: str, sem: asyncio.Semaphore) -> dict:
        cache_key = (
            train_url,
            self._canonical_station_name(departure_station),
            self._canonical_station_name(arrival_station),
        )
        cached = self._train_detail_cache.get(cache_key)
        if cached is not None:
            self._requests['cache_hits'] += 1
        if cached is not None:
            return dict(cached)

        async with sem:
            try:
                if self._rate_limited:
                    raise RuntimeError('Yahoo Transit rate limit (HTTP 429)')
                r = await self.client.get(urljoin(self.base_url, train_url))
                self._raise_for_rate_limit(r)
                soup = BeautifulSoup(r.text, 'html.parser')

                result = {
                    "arrival_time": "",
                    "train_name": "",
                    "stop_sequence": [],
                    "final_destination": "",
                    'platform': '', 'arrival_platform': '',
                    'platform_status': PlatformStatus.LOOKUP_FAILED,
                    'arrival_platform_status': PlatformStatus.LOOKUP_FAILED,
                }
                data = self._next_data(soup)
                if data:
                    tt = data.get("props", {}).get("pageProps", {}).get("timetableStationTrainResult", {}).get("timetable", {})

                    result["train_name"] = tt.get("displayName", "")

                    stop_stations = tt.get("stopStation", [])
                    result["stop_sequence"] = [
                        str(station.get("stationName", ""))
                        for station in stop_stations
                        if station.get("stationName")
                    ]
                    if result["stop_sequence"]:
                        result["final_destination"] = result["stop_sequence"][-1]
                    dep_idx = -1
                    for idx, s in enumerate(stop_stations):
                        if self._station_names_match(departure_station, s.get("stationName", "")):
                            dep_idx = idx
                            break

                    search_space = stop_stations[dep_idx + 1:] if dep_idx != -1 else []
                    for s in search_space:
                        if self._station_names_match(arrival_station, s.get("stationName", "")):
                            arr_time = s.get("arrivalTime") or s.get("departureTime")
                            if arr_time:
                                result["arrival_time"] = self._format_yahoo_time(arr_time)
                                result['platform'], result['platform_status'] = read_platform(
                                    stop_stations[dep_idx].get('trackNumber'), field_parsed=True)
                                result['arrival_platform'], result['arrival_platform_status'] = read_platform(
                                    s.get('trackNumber'), field_parsed=True)
                                break
                    if stop_stations:
                        self._train_detail_cache[cache_key] = dict(result)
                        return result

                # Fallback if no JSON
                station_elements = soup.select('.station')
                result["stop_sequence"] = [
                    title.get_text(" ", strip=True)
                    for station in station_elements
                    if (title := station.select_one('.title'))
                ]
                if result["stop_sequence"]:
                    result["final_destination"] = result["stop_sequence"][-1]

                departure_seen = False
                for s in station_elements:
                    title = s.select_one('.title')
                    if not title:
                        continue
                    if self._station_names_match(departure_station, title.text):
                        departure_seen = True
                        continue
                    if departure_seen and self._station_names_match(arrival_station, title.text):
                        time_lis = s.select('.time li')
                        for li in time_lis:
                            if '着' in li.text:
                                result["arrival_time"] = li.text.replace('着', '').strip()
                                self._train_detail_cache[cache_key] = dict(result)
                                return result
                        if time_lis:
                            result["arrival_time"] = time_lis[0].text.replace('着', '').replace('発', '').strip()
                            self._train_detail_cache[cache_key] = dict(result)
                            return result
                self._train_detail_cache[cache_key] = dict(result)
                return result
            except Exception as exc:
                if self._rate_limited:
                    raise
                logger.warning(f"Failed to fetch Yahoo train detail {train_url}: {exc}")
                return {
                    "arrival_time": "",
                    "train_name": "",
                    "stop_sequence": [],
                    "final_destination": "",
                    'platform': '', 'arrival_platform': '',
                    'platform_status': PlatformStatus.LOOKUP_FAILED,
                    'arrival_platform_status': PlatformStatus.LOOKUP_FAILED,
                }

    @staticmethod
    def _format_yahoo_time(raw_time: Any) -> str:
        value = str(raw_time).strip()
        if ":" in value:
            hour, minute = value.split(":", 1)
            return f"{int(hour):02d}:{int(minute):02d}"
        if len(value) >= 3 and value.isdigit():
            return f"{int(value[:-2]):02d}:{int(value[-2:]):02d}"
        return value

    def _structured_departures(self, item: dict, url: str, railway_name_jp: str) -> List[DepartureInfo]:
        entries = self._selected_service_entries(item, railway_name_jp)
        departures = []
        seen = set()
        for entry in entries:
            hour = str(entry.get("hour", ""))
            minute = str(entry.get("minute", ""))
            train_id = str(entry.get("trainId", ""))
            train_name_jp = str(entry.get("trainName") or entry.get("kind_name") or "")
            if not hour or not minute or not train_id:
                continue

            signature = (
                hour,
                minute,
                train_name_jp,
                entry.get("vendorTrainId") or train_id,
            )
            if signature in seen:
                continue
            seen.add(signature)

            train_url = self._train_detail_url(url, train_id, hour, minute)
            translated_name = self.translation_service.translate_train(train_name_jp)
            platform, platform_status = read_platform(entry.get('trackNumber'), field_parsed=True)
            departures.append(DepartureInfo(
                id=train_id,
                time=f"{int(hour):02d}:{int(minute):02d}",
                arrival_time="",
                train_name=translated_name,
                train_type=translated_name,
                direction=str(entry.get("destination_name", "")),
                platform=platform, platform_status=platform_status if platform else PlatformStatus.LOOKUP_FAILED,
                metadata={
                    "url": train_url,
                    "original_train_name": train_name_jp,
                },
            ))
        return departures

    def _html_departures(self, soup: BeautifulSoup) -> List[DepartureInfo]:
        departures = []
        seen = set()
        for row in soup.select('.tblDiaDetail tr'):
            hour_td = row.select_one('.hour')
            hour_match = re.search(r'\d+', hour_td.get_text(" ", strip=True)) if hour_td else None
            if not hour_match:
                continue
            hour = hour_match.group()

            for item in row.select('td li'):
                anchor = item.select_one('a')
                minute_element = item.select_one('dt')
                if not anchor or not minute_element:
                    continue
                href = anchor.get('href')
                minute_match = re.search(r'\d+', minute_element.get_text(" ", strip=True))
                if not href or not minute_match:
                    continue

                minute = minute_match.group()
                train_type = item.select_one('.trainType')
                train_type_text = train_type.get_text(" ", strip=True) if train_type else ""
                destination = item.select_one('.trainFor')
                destination_text = destination.get_text(" ", strip=True) if destination else ""
                signature = (hour, minute, train_type_text, destination_text)
                if signature in seen:
                    continue
                seen.add(signature)

                train_id = href.split('/')[-1].split('?')[0]
                translated_name = self.translation_service.translate_train(train_type_text)
                departures.append(DepartureInfo(
                    id=train_id,
                    time=f"{int(hour):02d}:{int(minute):02d}",
                    arrival_time="",
                    train_name=translated_name,
                    train_type=translated_name,
                    direction=destination_text,
                    metadata={"url": href, "original_train_name": train_type_text},
                ))
        return departures

    async def _parse_timetable_page(
        self,
        url: str,
        departure_station: str,
        arrival_station: str,
        railway_name_jp: str = "",
        *,
        cursor: int = 0,
        page_state: dict | None = None,
    ) -> List[DepartureInfo]:
        response = await self.client.get(urljoin(self.base_url, url))
        self._raise_for_rate_limit(response)
        soup = BeautifulSoup(response.text, 'html.parser')
        item = self._timetable_item(soup)
        departures = (
            self._structured_departures(item, url, railway_name_jp)
            if item
            else self._html_departures(soup)
        )
        semaphore = asyncio.Semaphore(self.TRAIN_DETAIL_CONCURRENCY)

        # Destination metadata proves target-terminating trains cheaply. For
        # trains terminating beyond the target, validate one representative
        # per service/destination group and reuse the detail cache during the
        # final enrichment pass. This avoids fetching every unrelated train on
        # a busy line while retaining services that call at the target en route.
        selected_ids = {
            departure.id
            for departure in departures
            if departure.direction
            and self._station_names_match(arrival_station, departure.direction)
        }
        destination_groups: Dict[tuple, List[DepartureInfo]] = {}
        for departure in departures:
            if departure.id in selected_ids:
                continue
            destination_key = self._normalize_identity(departure.direction)
            group_key = (
                service_identities(
                    str(departure.metadata.get("original_train_name", departure.train_name))
                ),
                destination_key or departure.id,
            )
            destination_groups.setdefault(group_key, []).append(departure)

        remaining_group_checks = self.CANDIDATE_DETAIL_REQUEST_BUDGET
        for group in destination_groups.values():
            if remaining_group_checks <= 0:
                break
            representative = group[0]
            train_url = representative.metadata.get("url")
            if not train_url:
                continue
            remaining_group_checks -= 1
            details = await self._fetch_train_details(
                train_url,
                departure_station,
                arrival_station,
                semaphore,
            )
            if (details.get("arrival_time") and (not has_named_service(railway_name_jp)
                    or service_match_strength(railway_name_jp, details.get('train_name', '')) == 2)):
                selected_ids.update(departure.id for departure in group)

        matching_departures = [
            departure
            for departure in departures
            if departure.id in selected_ids
        ]
        departures = matching_departures[cursor:cursor + self.FINAL_DEPARTURE_DETAIL_BUDGET]
        if page_state is not None:
            following = cursor + len(departures)
            page_state.update({"total_candidates": len(matching_departures),
                               "next_cursor": following if following < len(matching_departures) else None})

        async def enrich(departure: DepartureInfo) -> Optional[DepartureInfo]:
            train_url = departure.metadata.get("url")
            if not train_url:
                return None
            details = await self._fetch_train_details(
                train_url,
                departure_station,
                arrival_station,
                semaphore,
            )
            arrival_time = details.get("arrival_time", "")
            if not arrival_time:
                return None
            if has_named_service(railway_name_jp) and service_match_strength(railway_name_jp, details.get('train_name', '')) != 2:
                return None
            translated_name = (
                self.translation_service.translate_train(details["train_name"])
                if details.get("train_name")
                else departure.train_name
            )
            platform = details.get('platform', '')
            platform_status = details.get('platform_status', PlatformStatus.LOOKUP_FAILED)
            if platform_status != PlatformStatus.KNOWN and departure.platform_status == PlatformStatus.KNOWN:
                # The same entry/train ID is verified by exact stop detail; its
                # station-table trackNumber is independent, usable evidence.
                platform, platform_status = departure.platform, departure.platform_status
            return departure.model_copy(update={
                "arrival_time": arrival_time,
                "train_name": translated_name,
                "train_type": translated_name,
                "source": "yahoo",
                'platform': platform, 'platform_status': platform_status,
                'arrival_platform': details.get('arrival_platform', ''),
                'arrival_platform_status': details.get('arrival_platform_status', PlatformStatus.LOOKUP_FAILED),
                "source_url": urljoin(self.base_url, train_url),
                "metadata": {
                    **departure.metadata,
                    "stop_sequence": details.get("stop_sequence", []),
                    "final_destination": details.get("final_destination", ""),
                },
            })

        enriched = await asyncio.gather(*(enrich(departure) for departure in departures))
        return [departure for departure in enriched if departure is not None]

    def _merge_departures(self, deps: List[DepartureInfo]) -> List[DepartureInfo]:
        seen = {}
        for d in deps:
            key = (d.time, d.metadata.get("original_train_name", d.train_name), d.direction)
            if key not in seen:
                seen[key] = d
            else:
                if not seen[key].arrival_time and d.arrival_time:
                    seen[key] = d

        merged = list(seen.values())
        merged.sort(key=lambda x: x.time)
        return merged

    async def get_timetable(
        self,
        route_id: str,
        departure: str,
        arrival: str,
        timetable_id: Optional[str] = None,
        railway_name_jp: str = "",
        search_date: str | None = None,
        cursor: int = 0,
    ) -> Timetable:
        logger.info(f"YahooTimetableScraper fetching timetable for {departure} -> {arrival}")

        station_id = await self._get_station_id(departure)
        if not station_id:
            raise ValueError(f"Could not find Yahoo Station ID for {departure}")

        if timetable_id:
            best_urls = [f"/timetable/{station_id}/{timetable_id}"]
        else:
            best_urls = await self._get_timetable_urls(
                station_id,
                departure,
                arrival,
                railway_name_jp,
                search_date,
            )
            if not best_urls:
                raise ValueError(f"Could not find any Timetable URLs for {departure} -> {arrival}")

        selected_date_departures = []
        page_states = []
        failures = []
        for best_url in best_urls:
            exact_date_url = self._exact_date_timetable_url(best_url, search_date)
            logger.info(f"Using Timetable URL: {exact_date_url}")
            try:
                state = {}
                departures = await self._parse_timetable_page(
                    exact_date_url,
                    departure,
                    arrival,
                    railway_name_jp,
                    cursor=cursor,
                    page_state=state,
                )
                page_states.append(state)
                selected_date_departures.extend(departures)
            except Exception as e:
                if self._rate_limited:
                    raise
                logger.warning(f"Failed to parse timetable tab {exact_date_url}: {e}")
                failures.append(e)

        if failures and not page_states:
            raise ScraperException('Yahoo timetable could not be read; provider data is unavailable') from failures[0]

        merged_departures = [item.model_copy(update={'operating_date': search_date or ''})
                             for item in self._merge_departures(selected_date_departures)]
        departures_by_category = {
            "weekday": [],
            "saturday": [],
            "holiday": [],
        }
        departures_by_category[self._day_category(search_date)] = merged_departures

        return Timetable(
            route_id=route_id,
            selected_calendar=calendar_type_for_date(search_date),
            weekday=departures_by_category["weekday"],
            saturday=departures_by_category["saturday"],
            holiday=departures_by_category["holiday"],
            source="yahoo",
            source_url=urljoin(self.base_url, self._exact_date_timetable_url(best_urls[0], search_date)),
            complete=not any(state.get('next_cursor') is not None for state in page_states),
            next_cursor=next((state['next_cursor'] for state in page_states if state.get('next_cursor') is not None), None),
            total_candidates=sum(state.get('total_candidates', 0) for state in page_states),
        )
