from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# Models are currently defined in main.py for simplicity.
# This file can be used if model definitions become more complex or numerous.

class PlaceholderModel(BaseModel):
    id: int
    name: str

class Action(BaseModel):
    type: str # 'delay', 'signal_create', 'signal_update', 'signal_check', 'action_jump', 'route_to_connector'
    name: str
    parameters: Dict[str, Any] = {} # e.g., {"duration": 10}, {"signal_name": "s1", "value": True}, {"target_action_name": "Action X"}, {"connector_id": "c1"}
    original_connector_id: Optional[str] = None # 연결점 액션일 경우 원본 연결점 ID 저장

class ConnectionPoint(BaseModel):
    id: str
    name: str
    x: int = 0
    y: int = 0
    actions: List[Action] = []

class ProcessBlockConfig(BaseModel):
    id: str
    name: str
    actions: List[Action]
    capacity: Optional[int] = None  # 블록의 최대 용량 (None이면 무제한)
    connectionPoints: Optional[List[ConnectionPoint]] = [] # 커넥터 정보
    script: Optional[str] = ''  # 블록 스크립트
    status: Optional[str] = None  # 블록 상태 속성
    # x: int # Position for frontend, not directly used by SimPy logic here
    # y: int # Position for frontend

class ConnectionConfig(BaseModel):
    from_block_id: str
    from_connector_id: str # Assuming named/ID'd connectors on blocks
    to_block_id: str
    to_connector_id: str

class SimulationSetup(BaseModel):
    blocks: List[ProcessBlockConfig]
    connections: List[ConnectionConfig]
    initial_entities: int = 1
    stop_time: Optional[float] = None # Run until this time
    stop_entities_processed: Optional[int] = None # Or run until this many entities are processed by a designated "sink"
    initial_signals: Optional[Dict[str, bool]] = None # 전역 신호 초기값
    signals: Optional[Dict[str, bool]] = None # 호환성을 위한 signals 필드 추가
    globalSignals: Optional[List[Dict[str, Any]]] = None # 타입 정보를 포함한 전역 변수/신호
    
    def __init__(self, **data):
        super().__init__(**data)
        # signals가 있고 initial_signals가 없으면 복사
        if self.signals and not self.initial_signals:
            self.initial_signals = self.signals

class EntityState(BaseModel): # 엔티티 상태를 위한 모델
    id: str
    current_block_id: Optional[str] = None
    current_block_name: Optional[str] = None
    # current_action_name: Optional[str] = None # 추후 확장 가능
    # 엔티티 속성 추가
    state: Optional[str] = None  # "normal" | "transit"
    color: Optional[str] = None  # "gray", "blue", "green", "red", "black", "white"
    custom_attributes: Optional[List[str]] = []  # ["flip", "1c", etc.]

class SimulationStepResult(BaseModel):
    time: float
    event_description: str
    entities_processed_total: int
    active_entities: List[EntityState] = [] # 활성 엔티티 상태 추가
    current_signals: Optional[Dict[str, bool]] = None # 현재 신호값들 추가
    globalSignals: Optional[List[Dict[str, Any]]] = None # 타입 정보를 포함한 전역 변수/신호
    block_states: Optional[Dict[str, Any]] = None # 블록 상태 정보 (경고, 처리량 등)
    script_logs: Optional[List[Dict[str, Any]]] = None # 스크립트 로그 추가
    debug_info: Optional[Dict[str, Any]] = None # 디버그 정보 추가

class SimulationRunResult(BaseModel): # 전체 실행 결과 모델
    message: str
    log: List[Dict[str, Any]]
    total_entities_processed: int
    final_time: float
    active_entities: List[EntityState] = [] # 활성 엔티티 상태 추가

class BatchStepRequest(BaseModel): # 배치 스텝 요청 모델
    steps: int = 5  # 한 번에 실행할 스텝 수

class BatchStepResult(BaseModel): # 배치 스텝 결과 모델
    message: str
    steps_executed: int
    final_event_description: str
    log: List[Dict[str, Any]]
    current_time: float
    active_entities: List[EntityState] = []
    total_entities_processed: int
    step_results: Optional[List[Dict[str, Any]]] = []  # 각 스텝의 전체 결과

class ExecutionModeRequest(BaseModel):
    mode: str = Field(default="default", description="실행 모드: default, time_step, high_speed")
    config: dict = Field(default_factory=dict, description="모드별 설정")

# Example: If Action, ProcessBlockConfig, etc., were moved here:
# class Action(BaseModel):
#     type: str 
#     name: str
#     parameters: Dict[str, Any] = {} 