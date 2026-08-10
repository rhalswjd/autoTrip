from typing import List, Dict, Any
from bs4 import BeautifulSoup
from infrastructure.scrapers.timetable.yahoo_selectors import YAHOO_SELECTORS

class TimetableParser:
    """
    HTML에서 데이터를 추출하여 순수 Dictionary 형태로 반환하는 클래스.
    HTML 구조(Selector) 변경에 대비하여 Selector를 외부 주입 가능하도록 설계합니다.
    절대로 ScheduleCandidate 도메인을 직접 생성하지 않습니다.
    """
    def __init__(self, selectors: Dict[str, str] = None):
        self.selectors = selectors or YAHOO_SELECTORS
        
    def parse(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        raw_candidates = []
        
        route_items = soup.select(self.selectors.get("route_item", "div.routeSummary"))
        
        for item in route_items:
            dep_el = item.select_one(self.selectors.get("departure_time", ".time span"))
            dep_time = dep_el.text.strip() if dep_el else "00:00"
            
            arr_el = item.select_one(self.selectors.get("arrival_time", ".time span"))
            arr_time = arr_el.text.strip() if arr_el else "00:00"
            
            train_el = item.select_one(self.selectors.get("train_name", ".transport span"))
            train_name = train_el.text.strip() if train_el else ""
            
            dir_el = item.select_one(self.selectors.get("direction", ".dest"))
            direction = dir_el.text.strip() if dir_el else ""
            
            raw_candidates.append({
                "departure_time": dep_time,
                "arrival_time": arr_time,
                "train_name": train_name,
                "train_type": "", # 원천에 없는 값은 임의로 지어내지 않고 빈 문자열 유지
                "direction": direction,
                "platform": "", # TODO: 추가 파싱 로직 필요
                "is_current": False # 현재 선택 여부는 파서가 판단할 책임이 아님 (무조건 False)
            })
            
        return raw_candidates

    def parse_timetable(self, html: str) -> List[Dict[str, Any]]:
        """
        역 시간표(Timetable) 페이지 전용 파서.
        검색 결과(search/result)가 아닌 실제 야후 노선 시간표 페이지를 파싱합니다.
        """
        from core.logger import logger
        logger.info(f"10. parse_timetable html prefix (2000 chars):\n{html[:2000]}")
        soup = BeautifulSoup(html, 'html.parser')
        raw_candidates = []
        
        # Parse legends
        train_legend = {}
        dest_legend = {}
        
        trs = soup.select("tbody tr")
        for tr in trs:
            th = tr.select_one("th")
            if th and "列車種別" in th.text:
                for li in tr.select("li"):
                    parts = li.text.split("：")
                    if len(parts) == 2:
                        train_legend[parts[0].strip()] = parts[1].strip()
            if th and "行き先" in th.text:
                for li in tr.select("li"):
                    parts = li.text.split("：")
                    if len(parts) == 2:
                        dest_legend[parts[0].strip()] = parts[1].strip()
                        
        for tr in trs:
            tds = tr.select("td")
            if not tds:
                continue
                
            hour_text = tds[0].text.strip()
            if not hour_text.isdigit():
                continue
                
            hour = int(hour_text)
            
            for li in tr.select("li.timeNumb"):
                dl = li.select_one("dl")
                if not dl:
                    continue
                    
                dt = dl.select_one("dt")
                if dt:
                    for span in dt.select("span"):
                        span.decompose()
                        
                min_text = dt.text.strip() if dt else "00"
                import re
                match = re.search(r'\d+', min_text)
                min_text = match.group(0) if match else "00"
                
                train_type_el = dl.select_one("dd.trainType")
                train_type_raw = train_type_el.text.strip() if train_type_el else ""
                clean_type_raw = train_type_raw.replace("[", "").replace("]", "")
                train_type = train_legend.get(clean_type_raw, train_type_raw)
                if not train_type and "無印" in train_legend:
                    train_type = train_legend["無印"]
                
                dest_el = dl.select_one("dd.trainFor")
                direction_raw = dest_el.text.strip() if dest_el else ""
                direction = dest_legend.get(direction_raw, direction_raw)
                if not direction and "無印" in dest_legend:
                    direction = dest_legend["無印"]
                
                departure_time = f"{hour:02d}:{int(min_text):02d}"
                
                raw_candidates.append({
                    "departure_time": departure_time,
                    "arrival_time": "",
                    "train_name": "",
                    "train_type": train_type,
                    "direction": direction,
                    "platform": "",
                    "is_current": False
                })
                
        from core.logger import logger
        logger.info(f"[Parser] Parsed departures count: {len(raw_candidates)}")
        if raw_candidates:
            logger.info(f"[Parser] First object: {raw_candidates[0]}")
        return raw_candidates
