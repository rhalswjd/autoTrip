from pydantic import BaseModel, ConfigDict
from enum import Enum

class PlannerState(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"

class PlannerMode(str, Enum):
    WEEKDAY = "WEEKDAY"
    WEEKEND_HOLIDAY = "WEEKEND_HOLIDAY"
    SPECIFIC_DATE = "SPECIFIC_DATE" # Used during Final Check when an actual travel date is selected.

class ScheduleCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    # candidate_id:
    # - Stable ID (UUID 사용 금지)
    # - React key 용도 및 사용자 선택 추적용
    # - 향후 departure_station, arrival_station, departure_time, train_name, direction 등을 조합하여 생성될 예정
    candidate_id: str
    departure_time: str
    arrival_time: str
    train_name: str
    train_type: str
    direction: str
    is_current: bool = False

class PlannerMetadata(BaseModel):
    """
    Planner Domain Metadata
    
    현재:
    - planner_state
    - planner_mode
    
    향후 확장 예정:
    - Recommendation
    - Schedule Context
    - Final Check
    """
    model_config = ConfigDict(frozen=True)
    
    planner_state: PlannerState = PlannerState.AUTO
    planner_mode: PlannerMode = PlannerMode.WEEKDAY
    
    # TODO
    # Recommendation metadata
    # Schedule Context
    # Final Check metadata

