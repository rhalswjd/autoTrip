# NOT USED YET
# Reserved for future source selection.

from application.ports.timetable_source_port import TimetableSourcePort
from infrastructure.adapters.yahoo_timetable_source import YahooTimetableSource
from infrastructure.adapters.jr_odekake_timetable_source import JROdekakeTimetableSource

class TimetableSourceFactory:
    """
    런타임 혹은 설정에 따라 적절한 Source를 반환하는 Factory.
    현재는 구현체가 적어 오버엔지니어링일 수 있으므로 구조와 TODO만 남겨둡니다.
    실제 DI는 FastAPI의 의존성 주입(Depends)을 통해 해결하는 것을 권장합니다.
    """
    
    # TODO: Source 선택 정책 확정
    # TODO: 환경설정 기반 Source 선택
    # TODO: Feature Flag 지원
    # TODO: Fallback 전략 (예: Yahoo 실패 시 JR로 Fallback)
    
    @staticmethod
    def get_source(config_value: str = "yahoo") -> TimetableSourcePort:
        # 이 단계에서는 구현하지 않습니다. 
        # 향후 팩토리 패턴이 실제로 필요해지는 시점(Phase 7 등)에 구현합니다.
        pass
