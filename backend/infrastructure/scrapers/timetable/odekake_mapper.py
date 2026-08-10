from typing import List, Dict, Any
from domain.timetable import DepartureInfo
import uuid
import logging

logger = logging.getLogger(__name__)

class JROdekakeMapper:
    """
    JROdekakeParser에서 추출한 dict 리스트를 Domain 모델(DepartureInfo)로 매핑합니다.
    """
    def map(self, parsed_data: List[Dict[str, Any]], timetable_id: str = "") -> List[DepartureInfo]:
        logger.info(f"[JROdekakeMapper] Mapping {len(parsed_data)} departures...")
        departures = []
        
        for item in parsed_data:
            # metadata 설정
            metadata = item.get("metadata", {})
            if timetable_id:
                metadata["timetable_id"] = timetable_id
                
                # 유추 가능한 ID 추출 (예: 2815011001 -> station: 2815, line: 0110)
                if len(timetable_id) >= 10:
                    metadata["station_id"] = timetable_id[:4]
                    metadata["line_id"] = timetable_id[4:8]

            # Stable ID 생성 (station_id + line_id + time + train_name + destination)
            station_id = metadata.get("station_id", "unknown")
            line_id = metadata.get("line_id", "unknown")
            stable_id = f"{station_id}_{line_id}_{item['time']}_{item['train_name']}_{item['destination']}"
            
            dep_info = DepartureInfo(
                id=stable_id,
                time=item["time"],
                train_name=item["train_name"],
                train_type=item["train_name"], # JR Odekake에서는 종별이 train_name에 위치
                platform=item["platform"],
                direction=item["destination"],
                metadata=metadata
            )
            departures.append(dep_info)
            
        return departures
