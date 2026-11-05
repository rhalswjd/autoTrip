import httpx
from bs4 import BeautifulSoup
import asyncio
import json
import re
from typing import List
from urllib.parse import urljoin
import uuid
from datetime import datetime

from application.ports.scraper_port import ScraperPort, ScraperException
from domain.route import Route, RouteSegment, FareBreakdown
from domain.station import Station
from domain.timetable import Timetable
from domain.journey import canonical_station
from domain.station_identity import qualified_station_name
from domain.chronology import JST
from core.logger import logger

class YahooTransitAdapter(ScraperPort):
    MAX_PAGES_PER_SOURCE = 2

    @staticmethod
    def station_alias(name: str) -> str:
        return qualified_station_name(name)

    @staticmethod
    def _fare_breakdown(summary: dict, edges: list) -> FareBreakdown:
        def amount(value):
            digits = str(value or '').replace(',', '')
            return int(digits) if digits.isdigit() else None
        detail = str(summary.get('totalPriceDetail') or '')
        base = re.search(r'乗車券([0-9,]+)円', detail)
        surcharge = re.search(r'特別料金([0-9,]+)円', detail)
        seats = list(dict.fromkeys(str((e.get('priceInfo') or {}).get('expType')) for e in edges
                                 if (e.get('priceInfo') or {}).get('expType')
                                 and (amount((e.get('priceInfo') or {}).get('expPrice')) or 0) > 0))
        return FareBreakdown(total=amount(summary.get('totalPrice')),
            base=amount(base.group(1)) if base else None,
            surcharge=amount(surcharge.group(1)) if surcharge else None, seat_basis=' / '.join(seats))

    def __init__(self, timetable_scraper=None):
        self.timetable_scraper = timetable_scraper
        self.request_count = 0
        self.rate_limited = False
        self.base_url = "https://transit.yahoo.co.jp/search/result"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        # Avoid direct import at top to prevent circular deps if any, but it's safe here
        from infrastructure.services.translation_service import TranslationService
        self.translation_service = TranslationService()

    @staticmethod
    def _format_duration(value: str) -> str:
        value = str(value or "").strip()
        if not value:
            return ""
        hours = re.search(r"(\d+)時間", value)
        minutes = re.search(r"(\d+)分", value)
        parts = []
        if hours:
            parts.append(f"{int(hours.group(1))}h")
        if minutes:
            parts.append(f"{int(minutes.group(1))}m")
        return " ".join(parts) if parts else value

    @staticmethod
    def _duration_minutes(value: str) -> int | None:
        value = str(value or "")
        hours = re.search(r"(\d+)時間", value)
        minutes = re.search(r"(\d+)分", value)
        if not hours and not minutes:
            return None
        return (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)

    async def _fetch_yahoo_page(
        self,
        url: str,
        params: dict | None,
        route_params: dict,
        client: httpx.AsyncClient,
        search_date: str,
        search_time: str,
        source: str,
        rank_offset: int,
    ) -> tuple[List[Route], str | None]:
        logger.debug(f"Fetching Yahoo Transit page: {url} params={params}")
        if self.rate_limited:
            raise ScraperException('Yahoo HTTP 429: further route requests stopped')
        response = await client.get(url, params=params, follow_redirects=True)
        self.request_count += 1 + len(getattr(response, 'history', []))
        if response.status_code == 429:
            self.rate_limited = True
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        routes = []
        
        script = soup.select_one("script#__NEXT_DATA__")
        next_data = None
        if script:
            next_data = json.loads(script.string)

        search_data = next_data.get("props", {}).get("pageProps", {}).get("naviSearchParam", {}) if next_data else {}
        feature_list = search_data.get("featureInfoList", [])
            
        # DOM IDs may restart at route01 or continue at route04 on page two.
        # featureInfoList is page-local in both cases; global IDs are not array
        # offsets. Align the two page-local sequences before normalization.
        route_blocks = soup.find_all(id=re.compile(r'^route\d+$'))
        for feature_index, route_div in enumerate(route_blocks):
                
            summary = route_div.select_one('.routeSummary')
            if not summary:
                continue
                
            time_text = summary.select_one('.time').text if summary.select_one('.time') else ""
            
            feature = feature_list[feature_index] if len(feature_list) > feature_index else {}
            summary_info = feature.get("summaryInfo", {})
            # Yahoo can return the next morning even for a late departure query.
            # Its calendar export contains the real dates; HH:mm alone does not.
            calendar = summary_info.get('calendarData') or {}
            instants = {}
            for field, calendar_field in (('departure_datetime', 'startTime'), ('arrival_datetime', 'endTime')):
                if calendar.get(calendar_field):
                    try:
                        instants[field] = datetime.strptime(calendar[calendar_field], '%Y%m%dT%H%M%S').replace(tzinfo=JST).isoformat()
                    except (ValueError, TypeError):
                        logger.warning('Yahoo route calendar field malformed: %s', calendar_field)
            elapsed_raw = str(summary_info.get("totalTime") or "")
            if not elapsed_raw:
                elapsed_match = re.search(r'([0-9]+時間(?:[0-9]+分)?|[0-9]+分)', time_text)
                elapsed_raw = elapsed_match.group(1) if elapsed_match else ""
            onboard_raw = str(summary_info.get("timeOnBoard") or "")
            if not onboard_raw:
                onboard_match = re.search(r'乗車\s*([0-9]+時間(?:[0-9]+分)?|[0-9]+分)', time_text)
                onboard_raw = onboard_match.group(1) if onboard_match else ""

            duration = self._format_duration(elapsed_raw)
            onboard_duration = self._format_duration(onboard_raw)
            elapsed_minutes = self._duration_minutes(elapsed_raw)
            onboard_minutes = self._duration_minutes(onboard_raw)
            non_riding_duration = ""
            if elapsed_minutes is not None and onboard_minutes is not None and elapsed_minutes >= onboard_minutes:
                non_riding_duration = self._format_duration(f"{elapsed_minutes - onboard_minutes}分")
            
            times = re.findall(r'\d{1,2}:\d{2}', time_text)
            dep_time = str(summary_info.get("departureTime") or (times[0] if times else ""))
            arr_time = str(summary_info.get("arrivalTime") or (times[-1] if len(times) > 1 else (times[0] if times else "")))
            
            fare_elem = summary.select_one('.fare')
            fare_text = fare_elem.text if fare_elem else summary.text
            fare_match = re.search(r'([0-9,]+)円', fare_text)
            fare = int(fare_match.group(1).replace(',', '')) if fare_match else 0
            fare_breakdown = self._fare_breakdown(summary_info, feature.get('edgeInfoList', []))
            if fare_breakdown.total is not None:
                fare = fare_breakdown.total
            
            transfer_match = re.search(r'乗換：(\d+)回', fare_text) if not fare_elem else re.search(r'乗換：(\d+)回', summary.text)
            transfers = int(transfer_match.group(1)) if transfer_match else 0
            
            detail = route_div.select_one('.routeDetail')
            if not detail:
                continue
                
            station_names = [dt.text.strip() for dt in detail.select('.station dt') if dt.text.strip()]
            
            # Parse transport cleanly
            trains = []
            for t in detail.select('.transport'):
                div = t.select_one('div')
                if div:
                    # remove .small or .destination text
                    for cls in ['.small', '.destination']:
                        elem = div.select_one(cls)
                        if elem:
                            elem.decompose()
                    trains.append(div.text.strip())

            # Translate to English
            domain_stations = []
            for idx, s_name in enumerate(station_names):
                en_name = self.translation_service.get_english_name(s_name)
                edge_station = next((edge for edge in feature.get("edgeInfoList", [])
                                     if canonical_station(str(edge.get("stationName", ""))) == canonical_station(s_name)), {})
                station_code = str(edge_station.get("stationCode") or "")
                domain_stations.append(Station(id=station_code, name=en_name, name_jp=s_name,
                    provider_ids={'yahoo': station_code} if station_code else {}, provider_aliases={'yahoo': s_name}))
                
            en_trains = [self.translation_service.translate_train(t) for t in trains]
                
            if en_trains:
                # Find the first major train that isn't 'Walk'
                main_train = next((t for t in en_trains if t != 'Walk'), en_trains[0])
                railway = main_train
            else:
                railway = "Unknown Railway"
                
            polyline = " -> ".join(en_trains)
            
            # Parse platforms and fares from __NEXT_DATA__
            edge_list = feature.get("edgeInfoList", [])
            
            platforms = []
            fares = []
            seat_selections = []
            seen_edge_groups = set()
            edge_idx = 0
            
            for jp_train in trains:
                plat = None
                base_fare = None
                express_fare = None
                has_seat = False
                while edge_idx < len(edge_list):
                    e = edge_list[edge_idx]
                    e_name = e.get("railNameExcludingDestination") or e.get("railName", "")
                    
                    if "徒歩" in jp_train or "Walk" in jp_train or "도보" in jp_train or jp_train in e_name or e_name in jp_train:
                        if "徒歩" not in jp_train and "Walk" not in jp_train and "도보" not in jp_train:
                            riding_info = e.get("ridingPositionInfo") or {}
                            pos = riding_info.get("departure", [])
                            if pos and len(pos) >= 1:
                                plat = pos[0]
                                
                            p_info = e.get("priceInfo") or {}
                            if p_info:
                                p = int(p_info.get("price", "0").replace(",", ""))
                                ep = int(p_info.get("expPrice", "0").replace(",", ""))
                                e_group = p_info.get("edgeGroup")
                                
                                base_fare = None
                                if e_group:
                                    if e_group not in seen_edge_groups:
                                        base_fare = p
                                        seen_edge_groups.add(e_group)
                                else:
                                    base_fare = p
                                    
                                express_fare = ep if ep > 0 else None
                                if p_info.get("expType"):
                                    has_seat = True
                                    
                        while edge_idx + 1 < len(edge_list):
                            next_e = edge_list[edge_idx + 1]
                            next_e_name = next_e.get("railNameExcludingDestination") or next_e.get("railName", "")
                            if next_e_name == e_name:
                                edge_idx += 1
                            else:
                                break
                                
                        edge_idx += 1
                        break
                    edge_idx += 1
                platforms.append(plat)
                fares.append((base_fare, express_fare))
                seat_selections.append(has_seat)
            
            segments = []
            for j, jp_train in enumerate(trains):
                if "徒歩" in jp_train or "Walk" in jp_train or "도보" in jp_train:
                    seg_type = "walk"
                elif "バス" in jp_train or "Bus" in jp_train:
                    seg_type = "bus"
                else:
                    seg_type = "train"
                
                is_through = False
                if j < len(station_names):
                    if "乗換不要" in station_names[j] or "直通" in station_names[j]:
                        is_through = True
                
                seg_platform = platforms[j] if j < len(platforms) else None
                seg_fares = fares[j] if j < len(fares) else (None, None)
                seg_has_seat = seat_selections[j] if j < len(seat_selections) else False
                
                segments.append(RouteSegment(
                    segment_type=seg_type,
                    railway_name=en_trains[j],
                    railway_name_jp=trains[j],
                    is_through=is_through,
                    departure_platform=seg_platform,
                    base_fare=seg_fares[0] if seg_fares else None,
                    express_fare=seg_fares[1] if seg_fares else None,
                    has_seat_selection=seg_has_seat
                ))

                def station_times(station_name):
                    return [str(info.get("time", "")) for edge in edge_list
                            if canonical_station(str(edge.get("stationName", ""))) == canonical_station(station_name)
                            for info in edge.get("timeInfo", []) if info.get("time")]

                if j + 1 < len(station_names):
                    start_times, end_times = station_times(station_names[j]), station_times(station_names[j + 1])
                    segments[-1] = segments[-1].model_copy(update={
                        "departure_time": start_times[-1] if start_times else "",
                        "arrival_time": end_times[0] if end_times else "",
                    })
            
            dep_en = self.translation_service.get_english_name(route_params.get("from", ""))
            arr_en = self.translation_service.get_english_name(route_params.get("to", ""))
            
            routes.append(Route(
                id=str(uuid.uuid4()),
                departure_station=domain_stations[0].name if domain_stations else dep_en,
                arrival_station=domain_stations[-1].name if domain_stations else arr_en,
                railway_name=railway,
                departure_time=dep_time,
                arrival_time=arr_time,
                total_duration=duration,
                onboard_duration=onboard_duration,
                non_riding_duration=non_riding_duration,
                total_fare=fare,
                fare_breakdown=fare_breakdown,
                fare_status='indicative' if fare > 0 else 'unknown',
                transfer_count=transfers,
                polyline=polyline,
                search_date=instants['departure_datetime'][:10] if instants.get('departure_datetime') else search_date,
                search_time=search_time,
                **instants,
                search_source=source,
                source_rank=rank_offset + feature_index + 1,
                stations=domain_stations,
                segments=segments
            ))
            
        pager_info = search_data.get("pagerInfo", {})
        next_url = None
        if int(pager_info.get("end") or 0) < int(pager_info.get("count") or 0):
            next_url = pager_info.get("prevNextThreeUrl") or None
        return routes, next_url

    async def _fetch_yahoo_tab(
        self,
        params: dict,
        client: httpx.AsyncClient,
        search_date: str | None = None,
        search_time: str | None = None,
        source: str = "",
    ) -> List[Route]:
        if not search_date or not search_time:
            raise ValueError("Yahoo route search requires an explicit date and time")

        routes: List[Route] = []
        visited_requests = set()
        url = self.base_url
        request_params: dict | None = params

        for _page_number in range(self.MAX_PAGES_PER_SOURCE):
            request_key = (
                url,
                tuple(sorted((request_params or {}).items())),
            )
            if request_key in visited_requests:
                break
            visited_requests.add(request_key)

            page_routes, next_url = await self._fetch_yahoo_page(
                url,
                request_params,
                params,
                client,
                search_date,
                search_time,
                source,
                len(routes),
            )
            routes.extend(page_routes)
            if not next_url:
                break
            url = urljoin(self.base_url, next_url)
            request_params = None

        return routes

    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        before_requests = self.request_count
        if not time or not date:
            raise ScraperException("Yahoo route search requires an explicit departure date and time")

        base_params = {
            "from": self.station_alias(departure),
            "to": self.station_alias(arrival),
            "shin": "1",
            "ex": "1",
            "hb": "1",
            "al": "1"
        }
        
        hh, mm = time.split(':')
        base_params.update({
            "y": date[0:4],
            "m": date[5:7],
            "d": date[8:10],
            "hh": hh,
            "m1": mm[0],
            "m2": mm[1],
            "type": "1"
        })
            
        try:
            logger.debug(f"Fetching Yahoo Transit multi-tabs: {departure} to {arrival}")
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0) as client:
                
                # We fetch three sorts: s=None (Recommended), s=1 (Cheapest), s=2 (Fewest transfers)
                # s=0 is Earliest, which is usually identical to Recommended when time is specified.
                
                params_rec = dict(base_params)
                params_cheap = dict(base_params)
                params_cheap["s"] = "1"
                params_trans = dict(base_params)
                params_trans["s"] = "2"
                
                results = await asyncio.gather(
                    self._fetch_yahoo_tab(
                        params_rec,
                        client,
                        search_date=date,
                        search_time=time,
                        source="earliest",
                    ),
                    self._fetch_yahoo_tab(
                        params_cheap,
                        client,
                        search_date=date,
                        search_time=time,
                        source="cheapest",
                    ),
                    self._fetch_yahoo_tab(
                        params_trans,
                        client,
                        search_date=date,
                        search_time=time,
                        source="fewest_transfers",
                    ),
                    return_exceptions=True,
                )

                source_names = ("earliest", "cheapest", "fewest_transfers")
                successful_results = []
                failures = []
                for source_name, result in zip(source_names, results):
                    if isinstance(result, BaseException):
                        failures.append(result)
                        logger.error(f"Yahoo Transit source {source_name} failed: {result}")
                    else:
                        successful_results.append(result)

                if not successful_results:
                    failure_summary = "; ".join(str(failure) for failure in failures)
                    raise ScraperException(f"All Yahoo Transit sources failed: {failure_summary}")
                
                # Merge and deduplicate
                merged_routes = []
                seen_signatures = set()
                
                for route_list in successful_results:
                    for r in route_list:
                        # Exact provider-candidate dedup precedes passenger-family grouping.
                        # Translated presentation strings and prices are not identities.
                        sig = (tuple(canonical_station(s.name_jp or s.name) for s in r.stations),
                               tuple((s.railway_name_jp, s.is_through) for s in r.segments),
                               r.departure_time, r.arrival_time)
                        if sig not in seen_signatures:
                            seen_signatures.add(sig)
                            merged_routes.append(r)
                            
                logger.info('Yahoo route requests: %d; candidates=%d', self.request_count - before_requests, len(merged_routes))
                return merged_routes
        except Exception as e:
            logger.error(f"Yahoo Transit Scraper Error: {e}")
            raise ScraperException(f"Yahoo Transit scraping failed: {str(e)}") from e

    async def get_timetable(
        self,
        route_id: str,
        departure: str = "",
        arrival: str = "",
        timetable_id: str | None = None,
        railway_name_jp: str = "",
        search_date: str | None = None,
        station_context=None,
        not_before=None,
    ) -> Timetable:
        if not self.timetable_scraper:
            raise NotImplementedError("TimetableScraper not injected")
        if not departure or not arrival:
            raise ValueError("Departure and arrival stations are required for Yahoo Transit Timetable")
            
        logger.info(f"Scraping Timetable for {departure} -> {arrival}")
        # Use the injected timetable scraper
        res = await self.timetable_scraper.get_timetable(
            route_id,
            departure,
            arrival,
            timetable_id=timetable_id,
            railway_name_jp=railway_name_jp,
            search_date=search_date,
        )
        
        logger.info(
            "YahooTransitAdapter returning timetable: search_date=%s "
            "selected_calendar=%s weekday=%d saturday=%d holiday=%d selected=%d",
            search_date,
            res.selected_calendar.value,
            len(res.weekday),
            len(res.saturday),
            len(res.holiday),
            len(res.selected_departures()),
        )
        return res
