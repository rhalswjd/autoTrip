from typing import List, Dict, Any
from bs4 import BeautifulSoup
import logging

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
                    train_type = span.get_text(strip=True)
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
                "time": departure_time,
                "train_name": train_type, # JR Odekake에서는 '普通', '快速' 등이 train-name div에 들어감
                "destination": destination.replace('行', ''), # '行' 제거
                "platform": platform,
                "metadata": metadata
            })
            
        logger.info(f"[JROdekakeParser] Parsed {len(departures)} departures.")
        return departures
