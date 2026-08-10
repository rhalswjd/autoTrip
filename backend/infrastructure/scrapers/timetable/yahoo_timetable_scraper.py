import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import re

from domain.timetable import Timetable, DepartureInfo
from core.logger import logger

class YahooTimetableScraper:
    def __init__(self):
        self.base_url = "https://transit.yahoo.co.jp"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.client = httpx.AsyncClient(follow_redirects=True, headers=self.headers, timeout=15.0)

    async def _get_station_id(self, station_name: str) -> Optional[str]:
        url = f"{self.base_url}/station/time/search"
        params = {"q": station_name}
        try:
            r = await self.client.get(url, params=params)
            if "/timetable/" in str(r.url):
                match = re.search(r'/timetable/(\d+)', str(r.url))
                if match:
                    return match.group(1)
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a'):
                href = a.get('href', '')
                if '/timetable/' in href and a.text.strip() == station_name:
                    match = re.search(r'/timetable/(\d+)', href)
                    if match:
                        return match.group(1)
            return None
        except Exception as e:
            logger.error(f"Error getting station ID for {station_name}: {e}")
            return None

    def _score_line_match(self, dt_text: str, railway_name_jp: str) -> int:
        if not railway_name_jp: return 0
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

    async def _check_direction_validity(self, timetable_url: str, arrival_station: str) -> bool:
        try:
            r = await self.client.get(urljoin(self.base_url, timetable_url))
            soup = BeautifulSoup(r.text, 'html.parser')
            train_links = []
            for a in soup.select('.tblDiaDetail td li a'):
                href = a.get('href')
                if href and '/timetable/' in href:
                    train_links.append(href)
                    if len(train_links) >= 3:
                        break
            
            for t_url in train_links:
                tr = await self.client.get(urljoin(self.base_url, t_url))
                tsoup = BeautifulSoup(tr.text, 'html.parser')
                script = tsoup.select_one("script#__NEXT_DATA__")
                if script:
                    import json
                    data = json.loads(script.string)
                    stop_stations = data.get("props", {}).get("pageProps", {}).get("timetableStationTrainResult", {}).get("timetable", {}).get("stopStation", [])
                    for s in stop_stations:
                        if arrival_station in s.get("stationName", ""):
                            return True
                
                # fallback
                stations = tsoup.select('.station .title')
                for s in stations:
                    if arrival_station in s.text:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking direction validity for {timetable_url}: {e}")
            return False

    async def _get_best_timetable_url(self, station_id: str, departure_station: str, arrival_station: str, railway_name_jp: str) -> Optional[str]:
        url = f"{self.base_url}/timetable/{station_id}"
        try:
            r = await self.client.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            main_div = soup.select_one('#main') or soup
            
            candidates = []
            for dt in main_div.find_all('dt'):
                line_name = dt.text.strip()
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
                return None
                
            candidates.sort(key=lambda x: x['score'], reverse=True)
            best_score = candidates[0]['score']
            top_candidates = [c for c in candidates if c['score'] == best_score]
            
            for c in top_candidates:
                if arrival_station in c['dir']:
                    return c['url']
                    
            for c in top_candidates:
                is_valid = await self._check_direction_validity(c['url'], arrival_station)
                if is_valid:
                    return c['url']
                    
            return top_candidates[0]['url']
        except Exception as e:
            logger.error(f"Error getting timetable url for {station_id}: {e}")
            return None

    async def _fetch_train_details(self, train_url: str, arrival_station: str, sem: asyncio.Semaphore) -> dict:
        async with sem:
            try:
                r = await self.client.get(urljoin(self.base_url, train_url))
                soup = BeautifulSoup(r.text, 'html.parser')
                
                result = {"arrival_time": "", "train_name": ""}
                script = soup.select_one("script#__NEXT_DATA__")
                if script:
                    import json
                    data = json.loads(script.string)
                    tt = data.get("props", {}).get("pageProps", {}).get("timetableStationTrainResult", {}).get("timetable", {})
                    
                    result["train_name"] = tt.get("displayName", "")
                    
                    stop_stations = tt.get("stopStation", [])
                    for s in stop_stations:
                        if arrival_station in s.get("stationName", ""):
                            arr_time = s.get("arrivalTime") or s.get("departureTime")
                            if arr_time:
                                arr_time = str(arr_time)
                                if len(arr_time) >= 3:
                                    result["arrival_time"] = f"{arr_time[:-2].zfill(2)}:{arr_time[-2:]}"
                                else:
                                    result["arrival_time"] = arr_time
                                break
                    if result["arrival_time"]:
                        return result
                
                for s in soup.select('.station'):
                    title = s.select_one('.title')
                    if title and arrival_station in title.text:
                        time_lis = s.select('.time li')
                        for li in time_lis:
                            if '着' in li.text:
                                result["arrival_time"] = li.text.replace('着', '').strip()
                                return result
                        if time_lis:
                            result["arrival_time"] = time_lis[0].text.replace('着', '').replace('発', '').strip()
                            return result
                return result
            except Exception:
                return {"arrival_time": "", "train_name": ""}

    async def _parse_timetable_page(self, url: str, arrival_station: str) -> List[DepartureInfo]:
        r = await self.client.get(urljoin(self.base_url, url))
        soup = BeautifulSoup(r.text, 'html.parser')
        
        departures = []
        train_tasks = []
        sem = asyncio.Semaphore(15)
        
        rows = soup.select('.tblDiaDetail tr')
        for r_idx, row in enumerate(rows):
            hour_td = row.select_one('.hour')
            if not hour_td: continue
            hour = hour_td.text.strip()
            
            for li in row.select('td li'):
                a = li.select_one('a')
                if not a: continue
                href = a.get('href')
                
                dt = li.select_one('dt')
                if not dt: continue
                
                minute_match = re.search(r'^(\d+)', dt.text.strip())
                minute = minute_match.group(1) if minute_match else "00"
                time_str = f"{int(hour):02d}:{int(minute):02d}"
                
                train_type = li.select_one('.trainType')
                train_type_text = train_type.text.strip() if train_type else ""
                
                train_for = li.select_one('.trainFor')
                dest = train_for.text.strip() if train_for else ""
                
                train_id = href.split('/')[-1].split('?')[0] if href else f"{hour}{minute}"
                
                dep_info = DepartureInfo(
                    id=train_id,
                    time=time_str,
                    arrival_time="",
                    train_name=train_type_text,
                    train_type=train_type_text,
                    direction=dest,
                    metadata={"url": href}
                )
                departures.append(dep_info)
                
                if href:
                    train_tasks.append((len(departures)-1, self._fetch_train_details(href, arrival_station, sem)))
                    
        if train_tasks:
            results = await asyncio.gather(*(t[1] for t in train_tasks))
            for (idx, _), details in zip(train_tasks, results):
                old = departures[idx]
                departures[idx] = DepartureInfo(
                    id=old.id,
                    time=old.time,
                    arrival_time=details["arrival_time"],
                    train_name=details["train_name"] if details["train_name"] else old.train_name,
                    train_type=old.train_type,
                    platform=old.platform,
                    direction=old.direction,
                    metadata=old.metadata
                )
                
        # Filter out trains that don't reach the destination
        valid_departures = [d for d in departures if d.arrival_time != ""]
        return valid_departures

    async def get_timetable(self, route_id: str, departure: str, arrival: str, timetable_id: Optional[str] = None, railway_name_jp: str = "") -> Timetable:
        logger.info(f"YahooTimetableScraper fetching timetable for {departure} -> {arrival}")
        
        station_id = await self._get_station_id(departure)
        if not station_id:
            raise ValueError(f"Could not find Yahoo Station ID for {departure}")
            
        if timetable_id:
            best_url = f"/timetable/{station_id}/{timetable_id}?kind=1"
        else:
            best_url = await self._get_best_timetable_url(station_id, departure, arrival, railway_name_jp)
            if not best_url:
                raise ValueError(f"Could not find Timetable ID for {departure} -> {arrival}")
                
        # Strip time-filtering params like ym, d, hh, m so we get the full day timetable
        import re
        best_url = re.sub(r'[?&](ym|d|hh|m)=\d+', '', best_url)
        best_url = best_url.replace('?&', '?')
        if best_url.endswith('?'):
            best_url = best_url[:-1]
            
        logger.info(f"Using Timetable URL: {best_url}")
        
        base_timetable_url = re.sub(r'[?&]?kind=\d+', '', best_url)
        if '?' in base_timetable_url:
            if not base_timetable_url.endswith('&') and not base_timetable_url.endswith('?'):
                base_timetable_url += '&'
        else:
            base_timetable_url += '?'
            
        weekday_url = base_timetable_url + "kind=1"
        weekday_deps = await self._parse_timetable_page(weekday_url, arrival)
        
        return Timetable(
            route_id=route_id,
            weekday=weekday_deps,
            saturday=weekday_deps,
            holiday=weekday_deps
        )
