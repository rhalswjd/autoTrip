from typing import List, Dict, Any
from bs4 import BeautifulSoup
import logging
import re
from datetime import date
from domain.journey import canonical_station, station_names_match
from domain.chronology import dated_clock
from datetime import timedelta
from infrastructure.services.platform_information import read_platform

logger = logging.getLogger(__name__)

class JROdekakeParser:
    """
    JR Odekake의 특정 방면 전체 시간표 HTML을 파싱합니다.
    (예: https://timetable.jr-odekake.net/station-timetable/{id})
    """
    def parse(self, html: str) -> List[Dict[str, Any]]:
        logger.info("[JROdekakeParser] Parsing HTML...")
        soup = BeautifulSoup(html, 'html.parser')
        
        departures = []
        
        # 각 열차 항목은 <div class="minute-item"> 내부에 있습니다.
        minute_items = soup.select('.minute-item')
        
        for item in minute_items:
            # 1. 링크 정보
            a_tag = item.find('a')
            train_link = a_tag.get('href') if a_tag else None
            
            # 2. 시간
            time_div = item.select_one('.departure-time')
            departure_time = time_div.get_text(strip=True) if time_div else None
            
            if not departure_time:
                continue
                
            # 3. 열차 정보 (종별, 행선지, 플랫폼)
            train_info = item.select_one('.train-info')
            if not train_info:
                continue
                
            # 종별 (train-name)
            name_div = train_info.select_one('.train-name')
            train_type = ""
            train_type_classes = []
            if name_div:
                span = name_div.find('span')
                if span:
                    train_type = name_div.get_text(strip=True)
                    train_type_classes = span.get('class', [])
                else:
                    train_type = name_div.get_text(strip=True)
                    
            # 행선지 (destination)
            dest_div = train_info.select_one('.destination')
            destination = dest_div.get_text(strip=True) if dest_div else ""
            
            # 플랫폼 (platform-no)
            plat_div = train_info.select_one('.platform-no')
            platform = plat_div.get_text(strip=True) if plat_div else ""
            if platform.startswith('のりば['):
                platform = platform.replace('のりば[', '').replace(']', '')
                
            # 4. 마크 (mark) / 기타 메타데이터
            mark_div = item.select_one('.mark')
            mark_text = mark_div.get_text(strip=True) if mark_div else ""
            mark_classes = mark_div.get('class', []) if mark_div else []
            
            # a_tag attributes (like data-* attributes)
            a_attrs = a_tag.attrs if a_tag else {}
            data_attrs = {k: v for k, v in a_attrs.items() if k.startswith('data-')}
            
            metadata = {
                "link": train_link,
                "train_type_classes": train_type_classes,
                "mark_text": mark_text,
                "mark_classes": mark_classes,
                "raw_destination": destination, # 원본 텍스트 (예: '京都行')
            }
            metadata.update(data_attrs)
            
            departures.append({
                "time": departure_time.zfill(5),
                "train_name": train_type, # JR Odekake에서는 '普通', '快速' 등이 train-name div에 들어감
                "destination": destination.replace('行', ''), # '行' 제거
                "platform": platform,
                "metadata": metadata
            })
            
        logger.info(f"[JROdekakeParser] Parsed {len(departures)} departures.")
        return departures

    def parse_train(self, html: str, departure: str, arrival: str, search_date: str | None = None) -> Dict[str, Any]:
        """Read exact stops only; the pass-through marker レ is not a station call."""
        soup = BeautifulSoup(html, "html.parser")
        if search_date:
            requested = date.fromisoformat(search_date)
            calendars = soup.select('tr.month')
            for heading in calendars:
                month = re.search(r'(\d{4})年(\d{1,2})月', heading.get_text())
                if not month or (int(month[1]), int(month[2])) != (requested.year, requested.month):
                    continue
                table = heading.find_parent('table')
                day_cell = next((cell for cell in table.select('tr.day td')
                                 if cell.get_text(strip=True) == str(requested.day)), None)
                if day_cell is None or 'drivingday-01' not in day_cell.get('class', []):
                    return {}
                break
            else:
                if calendars:
                    return {}  # Outside the published operating calendar.
        info = {}
        for row in soup.select("tbody.train-details tr"):
            heading, values = row.find("th"), row.find_all("td", recursive=False)
            if heading and values:
                info[heading.get_text(strip=True)] = [value.get_text(" ", strip=True) for value in values]
        stops = []
        active_column = None
        boarded_column = None
        through_boundaries = []
        visited_columns = []
        for row in soup.select("tbody.time-details tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            station = canonical_station(cells[0].get_text(strip=True))
            columns = [(cells[index].get_text("", strip=True),
                        cells[index + 1].get_text(strip=True) if index + 1 < len(cells) else "")
                       for index in range(1, len(cells), 2)]
            if active_column is None:
                if not station_names_match(departure, station):
                    continue
                boarding_columns = [index for index, (text, _) in enumerate(columns)
                                    if re.search(r'\d{1,2}:\d{2}発', text)]
                if len(boarding_columns) != 1:
                    return {}  # Ambiguous parallel departures are not interchangeable.
                active_column = boarded_column = boarding_columns[0]
                visited_columns.append(active_column)
            if active_column >= len(columns):
                continue
            text, platform = columns[active_column]
            platform, platform_status = read_platform(platform, field_parsed=len(cells) > 2 + 2 * active_column)
            arrive = re.search(r"(\d{1,2}:\d{2})着", text)
            depart = re.search(r"(\d{1,2}:\d{2})発", text)
            if '直通' in text and not depart:
                continuations = [(index, value, track) for index, (value, track) in enumerate(columns)
                                 if index != active_column and '直通' in value
                                 and re.search(r'\d{1,2}:\d{2}発', value)]
                if len(continuations) == 1:
                    active_column, continuation, _ = continuations[0]
                    depart = re.search(r"(\d{1,2}:\d{2})発", continuation)
                    visited_columns.append(active_column)
                    through_boundaries.append(station)
            if not arrive and not depart:
                continue
            stops.append({"station": station,
                          "arrival": arrive[1].zfill(5) if arrive else "",
                          "departure": depart[1].zfill(5) if depart else "",
                          "platform": platform, "platform_status": platform_status})
        origin = next((i for i, s in enumerate(stops) if station_names_match(departure, s["station"])), None)
        target = next((i for i, s in enumerate(stops) if station_names_match(arrival, s["station"])), None)
        if origin is None or target is None or target <= origin:
            return {}
        if not stops[origin]["departure"] or not stops[target]["arrival"]:
            return {}
        def value_at(label, column):
            values = info.get(label, [])
            return values[column] if column is not None and column < len(values) else ""

        dated = {}
        if search_date:
            previous = None
            for row in soup.select('tbody.time-details tr'):
                cells = row.find_all('td', recursive=False)
                column = 1 + 2 * boarded_column
                if len(cells) <= column:
                    continue
                for clock in re.findall(r'\d{1,2}:\d{2}', cells[column].get_text(' ',strip=True)):
                    value = dated_clock(search_date, clock)
                    while previous and value < previous:
                        value += timedelta(days=1)
                    previous = value
                if station_names_match(departure,cells[0].get_text(strip=True)):
                    break
            if previous:
                dated['departure_datetime'] = previous.isoformat()
                for stop in stops[origin + 1:target + 1]:
                    for clock in (stop['arrival'], stop['departure'] if stop is not stops[target] else ''):
                        if not clock:
                            continue
                        value = dated_clock(search_date,clock)
                        while value < previous:
                            value += timedelta(days=1)
                        previous = value
                dated['arrival_datetime'] = previous.isoformat()
        return {**dated, "departure_time": stops[origin]["departure"], "arrival_time": stops[target]["arrival"],
                "platform": stops[origin]["platform"], "arrival_platform": stops[target]["platform"],
                "platform_status": stops[origin]['platform_status'], "arrival_platform_status": stops[target]['platform_status'],
                "train_name": value_at("列車名", boarded_column) or value_at("列車種別", boarded_column),
                "train_number": " / ".join(filter(None, (value_at("列車番号", column) for column in visited_columns))),
                "stop_sequence": [s["station"] for s in stops], "stops": stops,
                "through_boundaries": through_boundaries}
