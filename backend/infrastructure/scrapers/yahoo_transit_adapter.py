import httpx
from bs4 import BeautifulSoup
import re
from typing import List
import uuid

from application.ports.scraper_port import ScraperPort, ScraperException
from domain.route import Route, RouteSegment
from domain.station import Station
from domain.timetable import Timetable
from core.logger import logger

class YahooTransitAdapter(ScraperPort):
    def __init__(self, timetable_scraper=None):
        self.timetable_scraper = timetable_scraper
        self.base_url = "https://transit.yahoo.co.jp/search/result"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        # Avoid direct import at top to prevent circular deps if any, but it's safe here
        from infrastructure.services.translation_service import TranslationService
        self.translation_service = TranslationService()

    async def _fetch_yahoo_tab(self, params: dict, client: httpx.AsyncClient) -> List[Route]:
        logger.debug(f"Fetching Yahoo Transit with params: {params}")
        response = await client.get(self.base_url, params=params, follow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        routes = []
        
        script = soup.select_one("script#__NEXT_DATA__")
        next_data = None
        if script:
            import json
            next_data = json.loads(script.string)
            
        for i in range(1, 10):
            route_div = soup.select_one(f'#route0{i}')
            if not route_div:
                continue
                
            summary = route_div.select_one('.routeSummary')
            if not summary:
                continue
                
            time_text = summary.select_one('.time').text if summary.select_one('.time') else ""
            
            # Rule: 1. Try to extract Ride Time (乗車 X時間Y分 / 乗車 X分)
            ride_match = re.search(r'乗車\s*([0-9]+時間[0-9]+分|[0-9]+分)', time_text)
            if ride_match:
                duration = ride_match.group(1)
            else:
                # Rule 2: Fallback to Total Time or direct time
                duration_match = re.search(r'着(.+?)（', time_text)
                duration = duration_match.group(1) if duration_match else "0 min"
                if duration == "0 min":
                    dur_match = re.search(r'([0-9]+時間[0-9]+分|[0-9]+分)', time_text)
                    if dur_match:
                        duration = dur_match.group(1)
            
            # Translate duration to English manually
            duration = duration.replace('時間', 'h ').replace('分', 'm').strip()
            
            fare_elem = summary.select_one('.fare')
            fare_text = fare_elem.text if fare_elem else summary.text
            fare_match = re.search(r'([0-9,]+)円', fare_text)
            fare = int(fare_match.group(1).replace(',', '')) if fare_match else 0
            
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
                domain_stations.append(Station(id=f"st_{i}_{idx}", name=en_name, name_jp=s_name))
                
            en_trains = [self.translation_service.translate_train(t) for t in trains]
                
            if en_trains:
                # Find the first major train that isn't 'Walk'
                main_train = next((t for t in en_trains if t != 'Walk'), en_trains[0])
                railway = main_train
            else:
                railway = "Unknown Railway"
                
            polyline = " -> ".join(en_trains)
            
            # Parse platforms and fares from __NEXT_DATA__
            feature_list = next_data.get("props", {}).get("pageProps", {}).get("naviSearchParam", {}).get("featureInfoList", []) if next_data else []
            edge_list = feature_list[i-1].get("edgeInfoList", []) if len(feature_list) >= i else []
            
            platforms = []
            fares = []
            seen_edge_groups = set()
            edge_idx = 0
            
            for jp_train in trains:
                plat = None
                fare_val = None
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
                                
                                base_fare = 0
                                if e_group:
                                    if e_group not in seen_edge_groups:
                                        base_fare = p
                                        seen_edge_groups.add(e_group)
                                else:
                                    base_fare = p
                                    
                                fare_val = base_fare + ep
                                    
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
                fares.append(fare_val)
            
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
                seg_fare = fares[j] if j < len(fares) else None
                
                segments.append(RouteSegment(
                    segment_type=seg_type,
                    railway_name=en_trains[j],
                    railway_name_jp=trains[j],
                    is_through=is_through,
                    departure_platform=seg_platform,
                    fare=seg_fare
                ))
            
            dep_en = self.translation_service.get_english_name(params.get("from", ""))
            arr_en = self.translation_service.get_english_name(params.get("to", ""))
            
            routes.append(Route(
                id=str(uuid.uuid4()),
                departure_station=domain_stations[0].name if domain_stations else dep_en,
                arrival_station=domain_stations[-1].name if domain_stations else arr_en,
                railway_name=railway,
                total_duration=duration,
                total_fare=fare,
                transfer_count=transfers,
                polyline=polyline,
                stations=domain_stations,
                segments=segments
            ))
            
        return routes

    async def search_routes(self, departure: str, arrival: str, time: str | None = None, date: str | None = None) -> List[Route]:
        base_params = {
            "from": departure, 
            "to": arrival,
            "shin": "1",
            "ex": "1",
            "hb": "1",
            "al": "1"
        }
        
        if time and date:
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
        else:
            base_params["type"] = "5"
            
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
                
                import asyncio
                results = await asyncio.gather(
                    self._fetch_yahoo_tab(params_rec, client),
                    self._fetch_yahoo_tab(params_trans, client),
                    self._fetch_yahoo_tab(params_cheap, client)
                )
                
                # Merge and deduplicate
                merged_routes = []
                seen_signatures = set()
                
                for route_list in results:
                    for r in route_list:
                        # signature based on fare, duration, transfers and polyline
                        sig = f"{r.total_fare}_{r.total_duration}_{r.transfer_count}_{r.polyline}"
                        if sig not in seen_signatures:
                            seen_signatures.add(sig)
                            merged_routes.append(r)
                            
                return merged_routes
        except Exception as e:
            logger.error(f"Yahoo Transit Scraper Error: {e}")
            raise ScraperException(f"Yahoo Transit scraping failed: {str(e)}") from e

    async def get_timetable(self, route_id: str, departure: str = "", arrival: str = "", timetable_id: str | None = None, railway_name_jp: str = "") -> Timetable:
        if not self.timetable_scraper:
            raise NotImplementedError("TimetableScraper not injected")
        if not departure or not arrival:
            raise ValueError("Departure and arrival stations are required for Yahoo Transit Timetable")
            
        logger.info(f"Scraping Timetable for {departure} -> {arrival}")
        # Use the injected timetable scraper
        res = await self.timetable_scraper.get_timetable(route_id, departure, arrival, timetable_id=timetable_id, railway_name_jp=railway_name_jp)
        
        logger.info(f"YahooTransitAdapter returning Timetable: type={type(res)}, weekday length={len(res.weekday)}")
        return res
