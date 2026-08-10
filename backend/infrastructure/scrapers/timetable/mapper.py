import hashlib
from typing import Dict, Any, List
from domain.planner import ScheduleCandidate

class TimetableMapper:
    """
    Parser에서 추출한 Raw Data(Dict)를 도메인 엔티티(ScheduleCandidate)로 변환하는 클래스.
    Stable ID 생성 로직을 포함합니다.
    """
    def generate_candidate_id(self, dep_station: str, arr_station: str, dep_time: str, train_name: str, direction: str) -> str:
        """
        UUID를 사용하지 않고 불변하는 Stable ID를 생성합니다.
        React의 안정적인 Key 렌더링 및 사용자 선택 추적에 필수적입니다.
        일본어 문자가 깨지지 않도록 정규식(ASCII) 변환 없이 원래 문자열 그대로 utf-8 해싱합니다.
        """
        raw_string = f"{dep_station}_{arr_station}_{dep_time}_{train_name}_{direction}"
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    def map_to_domain(self, raw_data: List[Dict[str, Any]], dep_station: str, arr_station: str) -> Dict[int, List[ScheduleCandidate]]:
        from infrastructure.services.translation_service import TranslationService
        translator = TranslationService()
        
        candidates = []
        for raw in raw_data:
            dep_time = raw.get("departure_time", "00:00").replace("発", " Departure").replace("着", " Arrival")
            arr_time = raw.get("arrival_time", "00:00").replace("発", " Departure").replace("着", " Arrival")
            train_name = raw.get("train_name", "")
            train_type = raw.get("train_type", "")
            direction = raw.get("direction", "")
            is_current = raw.get("is_current", False)
            
            clean_train_type = train_type.replace("[", "").replace("]", "")
            clean_direction = direction.replace("[", "").replace("]", "")
            
            en_train_name = translator.translate_train(train_name) if train_name else ""
            en_train_type = translator.translate_train(clean_train_type) if clean_train_type else ""
            en_direction = translator.get_english_name(clean_direction) if clean_direction else ""
            
            candidate_id = self.generate_candidate_id(dep_station, arr_station, dep_time, en_train_name, en_direction)
            
            candidates.append(ScheduleCandidate(
                candidate_id=candidate_id,
                departure_time=dep_time,
                arrival_time=arr_time,
                train_name=en_train_name,
                train_type=en_train_type,
                direction=en_direction,
                is_current=is_current
            ))
            
        # TODO: 다중 Segment에 대한 파싱 및 매핑 로직 고도화 필요
        # 현재는 모든 후보를 첫 번째 Segment(index 0)에 임시로 할당합니다.
        return {0: candidates}

    def map_to_timetable(self, raw_data: List[Dict[str, Any]], route_id: str) -> 'Timetable':
        from domain.timetable import Timetable, DepartureInfo
        from infrastructure.services.translation_service import TranslationService
        
        translator = TranslationService()
        
        departures = []
        for raw in raw_data:
            dep_time = raw.get("departure_time", "00:00").replace("発", " Departure").replace("着", " Arrival")
            arr_time = raw.get("arrival_time", "00:00").replace("発", " Departure").replace("着", " Arrival")
            train_name = raw.get("train_name", "")
            train_type = raw.get("train_type", "")
            direction = raw.get("direction", "")
            platform = raw.get("platform", "")
            
            # Remove brackets for better translation if any
            clean_train_type = train_type.replace("[", "").replace("]", "")
            clean_direction = direction.replace("[", "").replace("]", "")
            
            en_train_name = translator.translate_train(train_name) if train_name else ""
            en_train_type = translator.translate_train(clean_train_type) if clean_train_type else ""
            en_direction = translator.get_english_name(clean_direction) if clean_direction else ""
            
            final_train_name = en_train_name
            if not final_train_name and en_train_type:
                final_train_name = en_train_type
            
            import uuid
            departures.append(DepartureInfo(
                id=str(uuid.uuid4()),
                time=dep_time,
                arrival_time=arr_time,
                train_name=final_train_name,
                train_type=en_train_type,
                platform=platform,
                direction=en_direction
            ))
            
        first_train = departures[0].time if departures else "05:00"
        last_train = departures[-1].time if departures else "23:30"
            
        return Timetable(
            route_id=route_id,
            first_train=first_train,
            last_train=last_train,
            departures=departures
        )
