from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # CORS 추가
from pydantic import BaseModel
import simpy
from typing import List, Dict, Any, Optional, Callable, Set
import asyncio # for async signal events
import traceback # For logging exceptions
import re  # 정규식 처리를 위해 추가
import random  # 랜덤 딜레이를 위해 추가

app = FastAPI()

# CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용으로 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models (Pydantic) ---
class Action(BaseModel):
    type: str # 'delay', 'signal_create', 'signal_update', 'signal_check', 'action_jump', 'route_to_connector'
    name: str
    parameters: Dict[str, Any] = {} # e.g., {"duration": 10}, {"signal_name": "s1", "value": True}, {"target_action_name": "Action X"}, {"connector_id": "c1"}
    original_connector_id: Optional[str] = None # 연결점 액션일 경우 원본 연결점 ID 저장

class ProcessBlockConfig(BaseModel):
    id: str
    name: str
    actions: List[Action]
    capacity: Optional[int] = None  # 블록의 최대 용량 (None이면 무제한)
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

class EntityState(BaseModel): # 엔티티 상태를 위한 모델
    id: str
    current_block_id: Optional[str] = None
    current_block_name: Optional[str] = None
    # current_action_name: Optional[str] = None # 추후 확장 가능

class SimulationStepResult(BaseModel):
    time: float
    event_description: str
    entities_processed_total: int
    active_entities: List[EntityState] = [] # 활성 엔티티 상태 추가
    current_signals: Optional[Dict[str, bool]] = None # 현재 신호값들 추가

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

# --- Global Simulation State (Simplified for now) ---
# In a real scenario, you'd need robust state management, especially for "step-by-step" and "previous_step"
# This might involve saving/loading simulation snapshots or re-running up to a point.
# For this example, we'll keep it very basic.

sim_env: Optional[simpy.Environment] = None
sim_log: List[Dict[str, Any]] = [] # To store events for step-by-step or review
processed_entities_count = 0

# 블록 간 통신을 위한 파이프 (SimPy Store)
block_pipes: Dict[str, simpy.Store] = {} # key: connector_id, value: Store

# 신호 관리를 위한 딕셔너리 (이벤트 기반 최적화)
signals: Dict[str, Dict[str, Any]] = {}
active_entities_registry: Set['Entity'] = set() # 활성 엔티티 추적

# MODIFIED: 블록별 현재 엔티티 수 추적
block_entity_counts: Dict[str, int] = {}  # key: block_id, value: current entity count

# Performance optimization: Entity object pooling
class EntityPool:
    def __init__(self):
        self.pool: List['Entity'] = []
        self.max_pool_size = 100
    
    def get_entity(self, env, id: str, name: str = "Product") -> 'Entity':
        if self.pool:
            entity = self.pool.pop()
            entity.reset(env, id, name)
            return entity
        return Entity(env, id, name)
    
    def return_entity(self, entity: 'Entity'):
        if len(self.pool) < self.max_pool_size:
            entity.cleanup()
            self.pool.append(entity)

entity_pool = EntityPool()

# --- 전역 변수 추가 ---
# 소스 블록이 다음 엔티티를 생성하도록 요청하는 이벤트 (스텝 실행용)
# key: block_id, value: simpy.Event
source_entity_request_events: Dict[str, simpy.Event] = {}
# 소스 블록이 현재까지 생성한 엔티티 수 (스텝 실행용)
# key: block_id, value: int
source_entity_generated_counts: Dict[str, int] = {}
# 전체 시뮬레이션에서 이 소스 블록이 생성해야 하는 총 엔티티 수 (스텝 실행용)
# 이 값은 첫 스텝의 initial_entities에서 설정되고, 매 배출마다 증가될 수 있음 (프론트 제어)
# 여기서는 백엔드가 각 스텝에서 1개씩 생성하도록 유도
source_entity_total_limits: Dict[str, int] = {}

class Entity:
    def __init__(self, env, id, name="Product"):
        self.env = env
        self.id = id
        self.name = name
        self.current_block_id: Optional[str] = None
        self.current_block_name: Optional[str] = None # 블록 이름 추가
        self.log = []
        self.log.append(f"{env.now:.2f}: Entity {self.id} created.")
        print(f"{env.now:.2f}: Entity {self.id} ({self.name}) created.")
        active_entities_registry.add(self) # 생성 시 레지스트리에 추가

    def reset(self, env, id: str, name: str = "Product"):
        """Reset entity for reuse from pool"""
        self.env = env
        self.id = id
        self.name = name
        self.current_block_id = None
        self.current_block_name = None
        self.log = []
        self.log.append(f"{env.now:.2f}: Entity {self.id} created (reused).")
        print(f"{env.now:.2f}: Entity {self.id} ({self.name}) created (reused).")
        active_entities_registry.add(self)

    def cleanup(self):
        """Clean up entity for pool return"""
        global block_entity_counts
        
        # 현재 블록에서 엔티티 수 감소
        if self.current_block_id and self.current_block_id in block_entity_counts:
            block_entity_counts[self.current_block_id] = max(0, block_entity_counts[self.current_block_id] - 1)
            if __debug__:
                print(f"{self.env.now:.2f}: Entity {self.id} cleaned up from Block {self.current_block_name}({self.current_block_id}). Count: {block_entity_counts[self.current_block_id]}")
        
        self.log.clear()
        self.current_block_id = None
        self.current_block_name = None
        active_entities_registry.discard(self)

    def __hash__(self): # Set에 넣기 위해 hashable하게 만듦
        return hash(self.id)

    def __eq__(self, other): # Set에 넣기 위해 eq도 구현
        if isinstance(other, Entity):
            return self.id == other.id
        return False

    def set_location(self, block_id: str, block_name: str):
        global block_entity_counts
        
        # 이전 블록에서 엔티티 수 감소
        if self.current_block_id and self.current_block_id in block_entity_counts:
            block_entity_counts[self.current_block_id] = max(0, block_entity_counts[self.current_block_id] - 1)
            if __debug__:
                print(f"{self.env.now:.2f}: Entity {self.id} left Block {self.current_block_name}({self.current_block_id}). Count: {block_entity_counts[self.current_block_id]}")
        
        # 새 블록으로 이동
        self.current_block_id = block_id
        self.current_block_name = block_name
        
        # 새 블록에서 엔티티 수 증가
        if block_id not in block_entity_counts:
            block_entity_counts[block_id] = 0
        block_entity_counts[block_id] += 1
        
        # DEBUG 로그 제거로 성능 최적화
        if __debug__:  # 디버그 모드에서만 출력
            print(f"{self.env.now:.2f}: Entity {self.id} moved to Block {block_name}({block_id}). Count: {block_entity_counts[block_id]}")

def get_active_entity_states() -> List[EntityState]:
    global block_entity_counts
    states = []
    print(f"DEBUG: get_active_entity_states called. Registry size: {len(active_entities_registry)}") # DEBUG
    print(f"DEBUG: Block entity counts: {block_entity_counts}")  # 블록별 카운트 정보 출력
    for entity in active_entities_registry:
        states.append(EntityState(
            id=entity.id, 
            current_block_id=entity.current_block_id,
            current_block_name=entity.current_block_name
        ))
        print(f"DEBUG: Entity {entity.id} state: ID={entity.current_block_id}, Name={entity.current_block_name}") # DEBUG
    return states

def check_entity_movement(initial_entity_states: Dict[str, str], initial_processed_count: int) -> bool:
    """엔티티의 블록 간 이동이 발생했는지 확인합니다."""
    global processed_entities_count
    
    # 1. 엔티티 배출 감지 (processed_entities_count 증가)
    if processed_entities_count > initial_processed_count:
        print(f"  Entity processed: count changed from {initial_processed_count} to {processed_entities_count}")
        return True
    
    # 2. 새로운 엔티티 생성 감지
    current_entity_ids = {entity.id for entity in active_entities_registry}
    initial_entity_ids = set(initial_entity_states.keys())
    
    new_entities = current_entity_ids - initial_entity_ids
    if new_entities:
        print(f"  New entities generated: {new_entities}")
        return True
    
    # 3. 기존 엔티티의 블록 이동 감지
    for entity in active_entities_registry:
        if entity.id in initial_entity_states:
            initial_block = initial_entity_states[entity.id]
            current_block = entity.current_block_id
            
            if initial_block != current_block:
                print(f"  Entity {entity.id} moved: {initial_block} -> {current_block}")
                return True
    
    return False

def get_latest_movement_description() -> str:
    """최근 로그에서 엔티티 이동 관련 설명을 찾습니다."""
    if not sim_log:
        return "No movement recorded yet"
    
    # 최근 10개 로그에서 이동 관련 설명 찾기
    recent_logs = sim_log[-10:]
    
    for log_entry in reversed(recent_logs):
        event = log_entry.get("event", "")
        
        # 엔티티 생성 관련
        if "generated at Source" in event:
            entity_id = log_entry.get("entity_id", "unknown")
            return f"Entity {entity_id}: {event}"
        
        # 엔티티 도착 관련
        if "arrived at" in event:
            entity_id = log_entry.get("entity_id", "unknown")
            return f"Entity {entity_id}: {event}"
        
        # 엔티티 배출 관련
        if "processed" in event.lower() or "sink" in event.lower():
            entity_id = log_entry.get("entity_id", "unknown")
            return f"Entity {entity_id}: {event}"
    
    return "Entity movement completed"

def parse_delay_value(duration_str: str) -> float:
    """Parses delay value, which can be a single value or a range."""
    if not duration_str:
        return 0.0
    
    duration_str = str(duration_str).strip()
    
    # 범위 표현 처리 (예: "3-7")
    if '-' in duration_str and duration_str.count('-') == 1:
        try:
            parts = duration_str.split('-')
            if len(parts) == 2:
                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())
                if min_val <= max_val:
                    return random.uniform(min_val, max_val)
        except ValueError:
            pass
    
    # 단일 값 처리
    try:
        return float(duration_str)
    except ValueError:
        print(f"Warning: Cannot parse delay value '{duration_str}', using 0.0")
        return 0.0

# 조건부 실행에서 개별 스크립트 라인을 실행하는 함수
def execute_script_line(env, line, entity, act_log, out_pipe_connectors=None):
    """스크립트 라인을 실행하고 결과를 반환합니다."""
    global signals, block_pipes
    
    if out_pipe_connectors is None:
        out_pipe_connectors = {}
    
    result = {'routed_out': False, 'jump_to_line': None}
    
    try:
        # 신호 변경 (signal = value)
        if ' = ' in line:
            signal_match = re.match(r'^(.+?)\s*=\s*(true|false)$', line)
            if signal_match:
                signal_name = signal_match.group(1).strip()
                new_value = signal_match.group(2) == 'true'
                
                print(f"{env.now:.2f}: {act_log} - Sub-action: Update signal '{signal_name}' to {new_value}")
                
                if signal_name in signals:
                    current_signal_info = signals[signal_name]
                    if current_signal_info["value"] != new_value:
                        current_signal_info["value"] = new_value
                        if new_value is True:
                            if not current_signal_info["event"].processed:
                                current_signal_info["event"].succeed()
                        else:
                            current_signal_info["event"] = env.event()
                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' updated to {new_value}")
                    else:
                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' already {new_value}")
                else:
                    print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' not found, creating with value {new_value}")
                    signals[signal_name] = {"event": env.event(), "value": new_value}
                    if new_value is True:
                        signals[signal_name]["event"].succeed()
        
        # 딜레이 (delay N)
        elif line.startswith('delay '):
            duration_str = line.replace('delay ', '').strip()
            try:
                duration = parse_delay_value(duration_str)
                print(f"{env.now:.2f}: {act_log} - Sub-action: Delay {duration}s")
                if duration > 0:
                    yield env.timeout(duration)
                else:
                    yield env.timeout(0.00001)
            except ValueError:
                print(f"{env.now:.2f}: {act_log} - Invalid delay value: {duration_str}")
        
        # 점프 (jump to N)
        elif line.startswith('jump to '):
            target_line_str = line.replace('jump to ', '').strip()
            try:
                target_line = int(target_line_str)
                print(f"{env.now:.2f}: {act_log} - Sub-action: Jump to line {target_line} (with 0.1s auto-delay)")
                # 점프 전 자동 딜레이 적용
                yield env.timeout(0.1)
                result['jump_to_line'] = target_line - 1  # 0-based index로 변환
            except ValueError:
                print(f"{env.now:.2f}: {act_log} - Invalid jump target: {target_line_str}")
        
        # 신호 대기 (wait signal = value)
        elif line.startswith('wait '):
            wait_condition = line.replace('wait ', '').strip()
            signal_match = re.match(r'^(.+?)\s*=\s*(true|false)$', wait_condition)
            if signal_match:
                signal_name = signal_match.group(1).strip()
                expected_value = signal_match.group(2) == 'true'
                
                print(f"{env.now:.2f}: {act_log} - Sub-action: Wait for signal '{signal_name}' = {expected_value}")
                
                if signal_name in signals:
                    current_value = signals[signal_name]["value"]
                    if current_value != expected_value:
                        print(f"{env.now:.2f}: {act_log} - Waiting for signal '{signal_name}' to become {expected_value} (current: {current_value})")
                        if expected_value is True:
                            yield signals[signal_name]["event"]
                        else:
                            # false를 기다리는 경우 - 이벤트 기반 대기
                            if "false_waiters" not in signals[signal_name]:
                                signals[signal_name]["false_waiters"] = []
                            wait_event = env.event()
                            signals[signal_name]["false_waiters"].append(wait_event)
                            yield wait_event
                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' condition met")
                    else:
                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' already {expected_value}")
                else:
                    print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' not found, creating and waiting")
                    signals[signal_name] = {"event": env.event(), "value": False}
                    if expected_value is True:
                        yield signals[signal_name]["event"]
            else:
                print(f"{env.now:.2f}: {act_log} - Invalid wait condition format: {wait_condition}")
        
        # 이동 (go to target)
        elif line.startswith('go to '):
            target = line.replace('go to ', '').strip()
            
            # 딜레이가 포함된 경우 처리
            delay = 0
            if ',' in target:
                target_parts = target.split(',')
                target = target_parts[0].strip()
                try:
                    delay = parse_delay_value(target_parts[1].strip())
                except ValueError:
                    delay = 0
            
            print(f"{env.now:.2f}: {act_log} - Sub-action: Go to {target} (delay: {delay}s)")
            
            # 딜레이 처리
            if delay > 0:
                yield env.timeout(delay)
            
            # self.connector 형태 처리를 위한 특별 로직
            if target.startswith('self.'):
                connector_name = target.replace('self.', '').strip()
                print(f"{env.now:.2f}: {act_log} - Self routing to connector: {connector_name}")
                
                # 현재 엔티티의 블록 ID와 이름 사용
                current_block_id = entity.current_block_id
                current_block_name = entity.current_block_name
                
                # connector_name이 블록 이름인 경우 (예: "공정1") - 블록으로 이동
                if connector_name == current_block_name or connector_name == str(current_block_id):
                    print(f"{env.now:.2f}: {act_log} - Self routing to block (connector name matches block name/ID)")
                    # 블록으로 이동하는 경우는 단순히 성공으로 표시 (실제로는 연결점 액션 종료 후 블록 액션으로 이동)
                    result['routed_out'] = True
                    print(f"{env.now:.2f}: {act_log} - Self routing to block completed")
                    return result
                else:
                    # 실제 연결점으로 이동하는 경우
                    print(f"{env.now:.2f}: {act_log} - Self routing to actual connector: {connector_name}")
                    result['routed_out'] = True
                    print(f"{env.now:.2f}: {act_log} - Self routing to connector completed")
                    return result
            
            # 파이프 ID로 직접 라우팅 시도
            actual_pipe_id = None
            
            # 1. 파이프 ID를 직접 사용하는 경우 (예: "2-conn-left")
            if target in block_pipes:
                actual_pipe_id = target
                print(f"{env.now:.2f}: {act_log} - Using direct pipe ID: {actual_pipe_id}")
            
            # 2. block.connector 형태인 경우
            elif '.' in target:
                parts = target.split('.')
                if len(parts) == 2:
                    block_name, connector_name = parts
                    
                    # 먼저 직접 파이프명으로 시도
                    direct_pipe_id = f"{block_name}-{connector_name}"
                    if direct_pipe_id in block_pipes:
                        actual_pipe_id = direct_pipe_id
                    else:
                        # 연결 매핑에서 찾기
                        for from_connector, to_pipe in out_pipe_connectors.items():
                            if from_connector == connector_name or to_pipe == direct_pipe_id:
                                actual_pipe_id = to_pipe
                                break
                        
                        # 그래도 못 찾으면 블록명이 포함된 파이프 찾기
                        if not actual_pipe_id:
                            for pipe_id in block_pipes.keys():
                                if block_name.lower() in pipe_id.lower() and connector_name.lower() in pipe_id.lower():
                                    actual_pipe_id = pipe_id
                                    break
            
            # 3. 사용 가능한 파이프에서 유사한 이름 찾기
            if not actual_pipe_id:
                for pipe_id in block_pipes.keys():
                    if target.lower().replace('-', '').replace('_', '') in pipe_id.lower().replace('-', '').replace('_', ''):
                        actual_pipe_id = pipe_id
                        break
            
            if actual_pipe_id and actual_pipe_id in block_pipes:
                target_pipe = block_pipes[actual_pipe_id]
                print(f"{env.now:.2f}: {act_log} - Routing entity to pipe {actual_pipe_id}")
                try:
                    yield target_pipe.put(entity)
                    result['routed_out'] = True
                    print(f"{env.now:.2f}: {act_log} - Entity routed successfully")
                except Exception as e:
                    print(f"{env.now:.2f}: {act_log} - Error routing entity: {e}")
            else:
                print(f"{env.now:.2f}: {act_log} - Pipe '{target}' not found. Available pipes: {list(block_pipes.keys())}")
        
        else:
            print(f"{env.now:.2f}: {act_log} - Unrecognized sub-action: {line}")
    
    except Exception as e:
        print(f"{env.now:.2f}: {act_log} - Error executing sub-action '{line}': {e}")
        traceback.print_exc()
    
    return result

def block_process(env: simpy.Environment, block_config: ProcessBlockConfig, in_pipe_ids: List[str], out_pipe_connectors: Dict[str, str]):
    global processed_entities_count, sim_log, signals, block_pipes, active_entities_registry
    global source_entity_request_events, source_entity_generated_counts 
    
    block_log_prefix = f"BPROC [{block_config.name}({block_config.id})]"
    print(f"{env.now:.2f}: {block_log_prefix} Process started. Inputs: {in_pipe_ids}, Outputs: {out_pipe_connectors}")
    sim_log.append({"time": env.now, "event": f"{block_log_prefix} process started."})

    # MODIFIED: custom_sink 액션이 있는 블록은 싱크 블록으로 간주하여 소스 블록 로직에서 제외
    has_custom_sink = any(action.type == "custom_sink" for action in block_config.actions)
    is_source_block = not in_pipe_ids and not has_custom_sink
    
    print(f"{env.now:.2f}: {block_log_prefix} Block analysis - Has input pipes: {bool(in_pipe_ids)}, Has custom_sink: {has_custom_sink}, Is source: {is_source_block}")

    while True:
        entity: Optional[Entity] = None
        print(f"{env.now:.2f}: {block_log_prefix} New loop iteration. Is source: {is_source_block}")

        if is_source_block:
            if block_config.id not in source_entity_request_events:
                print(f"{env.now:.2f}: {block_log_prefix} Critical Error: source_entity_request_event for {block_config.id} not initialized. Halting block.")
                yield env.timeout(float('inf')) 
                continue

            current_total_generated = source_entity_generated_counts.get(block_config.id, 0)
            print(f"{env.now:.2f}: {block_log_prefix} Source block. Total generated so far: {current_total_generated}.")
            
            print(f"{env.now:.2f}: {block_log_prefix} Waiting for entity request event for {block_config.id} (Event ID: {id(source_entity_request_events.get(block_config.id))}).")
            try:
                if block_config.id in source_entity_request_events:
                    yield source_entity_request_events[block_config.id]
                    print(f"{env.now:.2f}: {block_log_prefix} Entity request event received for {block_config.id}.")
                else: # 이론상 발생하면 안됨.
                    print(f"{env.now:.2f}: {block_log_prefix} ERROR: Request event not found for {block_config.id} even after check. Halting generation for this cycle.")
                    yield env.timeout(1) # 문제가 있으니 잠시 대기 후 루프 재시작
                    continue
            except RuntimeError as e:
                print(f"{env.now:.2f}: {block_log_prefix} Runtime error waiting for request event: {e}. Retrying in next cycle.")
                yield env.timeout(0.000001) 
                continue
            except Exception as e: # 기타 예외
                print(f"{env.now:.2f}: {block_log_prefix} Exception waiting for request event: {e}. Halting block.")
                yield env.timeout(float('inf'))
                continue
            
            entity_id_str = f"{block_config.id}-e{current_total_generated + 1}"
            entity = entity_pool.get_entity(env, entity_id_str)
            entity.set_location(block_config.id, block_config.name)
            print(f"{env.now:.2f}: {block_log_prefix} Generated Entity {entity.id}")
            sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} generated at Source {block_config.name}"})
            
            source_entity_generated_counts[block_config.id] = current_total_generated + 1
        
        elif has_custom_sink:
            # MODIFIED: 싱크 블록의 경우 입력 파이프에서 엔티티를 기다리되, 파이프가 없으면 무한 대기
            if in_pipe_ids and in_pipe_ids[0] in block_pipes:
                pipe_id_to_get = in_pipe_ids[0]
                
                # MODIFIED: 용량 제한 체크
                current_entity_count = block_entity_counts.get(block_config.id, 0)
                max_capacity = block_config.capacity
                
                print(f"{env.now:.2f}: {block_log_prefix} Checking capacity - Current: {current_entity_count}, Max: {max_capacity}")
                
                if max_capacity is not None and current_entity_count >= max_capacity:
                    print(f"{env.now:.2f}: {block_log_prefix} Block at capacity ({current_entity_count}/{max_capacity}). Cannot accept more entities.")
                    sim_log.append({"time": env.now, "block_id": block_config.id, "event": f"Block {block_config.name} at capacity ({current_entity_count}/{max_capacity}), cannot accept entities"})
                    # 용량이 가득 차면 파이프에서 엔티티를 받지 않고 대기
                    yield env.timeout(1.0)  # 1초 대기 후 재시도
                    continue
                
                print(f"{env.now:.2f}: {block_log_prefix} Sink block waiting for entity from pipe '{pipe_id_to_get}' (capacity: {current_entity_count}/{max_capacity if max_capacity else 'unlimited'})")
                item_event = block_pipes[pipe_id_to_get].get()
                try:
                    retrieved_item = yield item_event
                    entity = retrieved_item 
                except Exception as e: 
                    print(f"{env.now:.2f}: {block_log_prefix} Exception while getting from pipe {pipe_id_to_get}: {e}. Stopping block or retrying.")
                    yield env.timeout(float('inf')) 
                    continue

                if entity:
                    entity.set_location(block_config.id, block_config.name)
                    print(f"{env.now:.2f}: {block_log_prefix} Sink received Entity {entity.id} from pipe '{pipe_id_to_get}'")
                    sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} arrived at sink {block_config.name} via pipe {pipe_id_to_get}"})
                else: 
                    print(f"{env.now:.2f}: {block_log_prefix} Received None from pipe '{pipe_id_to_get}'. Idling.")
                    yield env.timeout(1) 
                    continue
            else:
                print(f"{env.now:.2f}: {block_log_prefix} Sink block has no input pipe or pipe not found. Terminating block process.")
                break  # while 루프 완전 종료
        
        else: # Non-source block
            if in_pipe_ids and in_pipe_ids[0] in block_pipes:
                pipe_id_to_get = in_pipe_ids[0]
                
                # MODIFIED: 용량 제한 체크
                current_entity_count = block_entity_counts.get(block_config.id, 0)
                max_capacity = block_config.capacity
                
                print(f"{env.now:.2f}: {block_log_prefix} Checking capacity - Current: {current_entity_count}, Max: {max_capacity}")
                
                if max_capacity is not None and current_entity_count >= max_capacity:
                    print(f"{env.now:.2f}: {block_log_prefix} Block at capacity ({current_entity_count}/{max_capacity}). Cannot accept more entities.")
                    sim_log.append({"time": env.now, "block_id": block_config.id, "event": f"Block {block_config.name} at capacity ({current_entity_count}/{max_capacity}), cannot accept entities"})
                    # 용량이 가득 차면 파이프에서 엔티티를 받지 않고 대기
                    yield env.timeout(1.0)  # 1초 대기 후 재시도
                    continue
                
                print(f"{env.now:.2f}: {block_log_prefix} Waiting for entity from pipe '{pipe_id_to_get}' (capacity: {current_entity_count}/{max_capacity if max_capacity else 'unlimited'})")
                item_event = block_pipes[pipe_id_to_get].get()
                try:
                    retrieved_item = yield item_event
                    entity = retrieved_item 
                except Exception as e: 
                    print(f"{env.now:.2f}: {block_log_prefix} Exception while getting from pipe {pipe_id_to_get}: {e}. Stopping block or retrying.")
                    yield env.timeout(float('inf')) 
                    continue

                if entity:
                    entity.set_location(block_config.id, block_config.name)
                    print(f"{env.now:.2f}: {block_log_prefix} Received Entity {entity.id} from pipe '{pipe_id_to_get}'")
                    sim_log.append({"time": env.now, "entity_id": entity.id, "event": f"Entity {entity.id} arrived at {block_config.name} via pipe {pipe_id_to_get}"})
                else: 
                    print(f"{env.now:.2f}: {block_log_prefix} Received None from pipe '{pipe_id_to_get}'. Idling.")
                    yield env.timeout(1) 
                    continue
            else:
                print(f"{env.now:.2f}: {block_log_prefix} No valid input pipe or pipe ID '{in_pipe_ids[0] if in_pipe_ids else 'N/A'}' not in block_pipes. Idling.")
                yield env.timeout(1) 
                continue
        
        if not entity:
            print(f"{env.now:.2f}: {block_log_prefix} No entity to process this iteration. Min_delay.")
            yield env.timeout(0.0001) 
            continue

        entity_log_prefix = f"{block_log_prefix} [E:{entity.id}]"
        print(f"{env.now:.2f}: {entity_log_prefix} Starting actions.")
        print(f"{env.now:.2f}: {entity_log_prefix} DEBUG: Block has {len(block_config.actions)} actions to process")
        for i, action in enumerate(block_config.actions):
            print(f"{env.now:.2f}: {entity_log_prefix} DEBUG: Action {i}: {action.name} ({action.type})")

        current_action_index = 0
        # MODIFIED: 'self' 라우팅 후 돌아올 지점을 저장하기 위한 변수, 엔티티별로 초기화
        target_index_after_self_initiated_block_actions = -1 

        while current_action_index < len(block_config.actions):
            action = block_config.actions[current_action_index]
            action_full_name = f"{action.name}{'@CP:'+action.original_connector_id if action.original_connector_id else ''}"
            act_log = f"{entity_log_prefix} Action '{action_full_name}' ({action.type}) P:{action.parameters}"
            
            print(f"{env.now:.2f}: {act_log} - Starting.")
            sim_log.append({"time": env.now, "entity_id": entity.id, "block_id": block_config.id, "connector_id": action.original_connector_id , "action_name": action.name, "action_type": action.type, "parameters": action.parameters, "event": "Action starting"})

            routed_out = False
            # found_target_action 변수는 action_jump 타입 내부에서만 사용되도록 변경

            if action.type == "delay":
                duration = parse_delay_value(str(action.parameters.get("duration", 0)))
                print(f"{env.now:.2f}: {act_log} - Delaying for {duration}s.")
                if duration > 0: yield env.timeout(duration) # MODIFIED
                else: yield env.timeout(0.00001) # MODIFIED
                print(f"{env.now:.2f}: {act_log} - Finished delay.")
            
            elif action.type == "signal_create":
                signal_name = action.parameters.get("signal_name")
                value = action.parameters.get("value", False)
                print(f"{env.now:.2f}: {act_log} - Create signal '{signal_name}' = {value}")
                if signal_name:
                    if signal_name in signals: 
                        print(f"{env.now:.2f}: {act_log} - Failed. Signal '{signal_name}' already exists.")
                    else:
                        signals[signal_name] = {"event": env.event(), "value": False} 
                        if value is True: 
                            signals[signal_name]["event"].succeed()
                            signals[signal_name]["value"] = True
                        print(f"{env.now:.2f}: {act_log} - Created signal '{signal_name}' with value {signals[signal_name]['value']}.")
                else:
                    print(f"{env.now:.2f}: {act_log} - Failed. 'signal_name' missing.")
            
            elif action.type == "signal_update":
                signal_name = action.parameters.get("signal_name")
                new_value = action.parameters.get("value", False)
                print(f"{env.now:.2f}: {act_log} - Update signal '{signal_name}' to {new_value}")
                if signal_name:
                    if signal_name in signals:
                        current_signal_info = signals[signal_name]
                        if current_signal_info["value"] != new_value:
                            print(f"{env.now:.2f}: {act_log} - Current val: {current_signal_info['value']}. Updating to {new_value}")
                            current_signal_info["value"] = new_value
                            if new_value is True: 
                                if not current_signal_info["event"].processed:
                                    print(f"{env.now:.2f}: {act_log} - Triggering signal event for '{signal_name}' (Event ID: {id(current_signal_info['event'])})")
                                    current_signal_info["event"].succeed()
                                    print(f"{env.now:.2f}: {act_log} - Signal event triggered successfully")
                                else:
                                    print(f"{env.now:.2f}: {act_log} - Signal event already processed for '{signal_name}', creating new event")
                                    # 이미 처리된 경우에만 새 이벤트 생성
                                    current_signal_info["event"] = env.event()
                            else: 
                                # False로 변경될 때 false_waiters에게 알림
                                if "false_waiters" in current_signal_info:
                                    for wait_event in current_signal_info["false_waiters"]:
                                        if not wait_event.processed:
                                            wait_event.succeed()
                                    current_signal_info["false_waiters"] = []
                                # 새 이벤트 생성 (다음 True 대기를 위해)
                                current_signal_info["event"] = env.event()
                            print(f"{env.now:.2f}: {act_log} - Updated '{signal_name}' to {new_value}. Event processed: {current_signal_info['event'].processed}")
                        else:
                            print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' already {new_value}. No change.")
                    else:
                        print(f"{env.now:.2f}: {act_log} - Failed. Signal '{signal_name}' not found.")
                else:
                    print(f"{env.now:.2f}: {act_log} - Failed. 'signal_name' missing.")
            
            elif action.type == "signal_check":
                signal_name = action.parameters.get("signal_name")
                expected_value = action.parameters.get("expected_value", True)
                print(f"{env.now:.2f}: {act_log} - Check signal '{signal_name}' for {expected_value}")
                if signal_name:
                    if signal_name in signals:
                        signal_info = signals[signal_name]
                        print(f"{env.now:.2f}: {act_log} - Waiting for '{signal_name}'=={expected_value}. Current: {signal_info['value']}, Event processed: {signal_info['event'].processed}")
                        
                        # 이벤트 기반 대기로 최적화
                        if signal_info["value"] != expected_value:
                            print(f"{env.now:.2f}: {act_log} - Waiting for '{signal_name}'=={expected_value}. Current: {signal_info['value']}")
                            if expected_value is True: 
                                if not signal_info["event"].processed:
                                    yield signal_info["event"]
                            else: 
                                # False를 기다리는 경우 - 이벤트 기반 대기
                                if "false_waiters" not in signal_info:
                                    signal_info["false_waiters"] = []
                                wait_event = env.event()
                                signal_info["false_waiters"].append(wait_event)
                                yield wait_event
                            if env.peek() == float('inf'): 
                                print(f"{env.now:.2f}: {act_log} - Simulation ended while waiting for signal.")
                                break 
                        if signal_info["value"] == expected_value:        
                            print(f"{env.now:.2f}: {act_log} - Condition met for signal '{signal_name}' ({expected_value}).")
                        else:
                            print(f"{env.now:.2f}: {act_log} - Condition NOT met for signal '{signal_name}' ({expected_value}) after wait cycles, sim ended or an issue.")
                    else:
                        print(f"{env.now:.2f}: {act_log} - Failed. Signal '{signal_name}' not found. Will wait indefinitely.")
                        signals[signal_name] = {"event": env.event(), "value": False} 
                        if expected_value is True: yield signals[signal_name]["event"] # MODIFIED
                else:
                    print(f"{env.now:.2f}: {act_log} - Failed. 'signal_name' missing.")

            elif action.type == "action_jump":
                target_name = action.parameters.get("target_action_name")
                print(f"{env.now:.2f}: {act_log} - Jump to '{target_name}'")
                if target_name:
                    jump_to_action_name = target_name
                else:
                    print(f"{env.now:.2f}: {act_log} - Failed. 'target_action_name' missing.")
            
            elif action.type == "route_to_connector":
                target_block_id_str = str(action.parameters.get("target_block_id"))
                target_connector_id = action.parameters.get("target_connector_id")
                delay_duration = parse_delay_value(str(action.parameters.get("delay", 0)))

                # MODIFIED: self 라우팅의 경우 connector_id 파라미터도 확인
                if not target_connector_id:
                    target_connector_id = action.parameters.get("connector_id")

                print(f"{env.now:.2f}: {act_log} - Route to B:{target_block_id_str}.C:{target_connector_id}, Delay:{delay_duration}")

                if delay_duration > 0:
                    print(f"{env.now:.2f}: {act_log} - Delaying route for {delay_duration}s.")
                    yield env.timeout(delay_duration)

                # MODIFIED: 같은 블록 내 연결점으로 이동하는 경우 self 라우팅으로 처리
                if target_connector_id == "self" or target_block_id_str == block_config.id or action.parameters.get("target_block_name") == "self":
                    # self 라우팅의 경우 실제 connector_id 사용
                    actual_connector_id = action.parameters.get("connector_id")
                    if not actual_connector_id:
                        actual_connector_id = target_connector_id
                    
                    print(f"{env.now:.2f}: {act_log} - Routing to self (same block). Will execute connector actions for connector {actual_connector_id}, then continue from action after this one.")
                    entity.set_location(block_config.id, block_config.name)

                    # 'self' 라우팅 액션 다음 인덱스를 저장
                    target_index_after_self_initiated_block_actions = current_action_index + 1
                    
                    # actual_connector_id에 해당하는 연결점 액션들을 찾기
                    first_connector_action_idx = -1
                    for idx, act_in_list in enumerate(block_config.actions):
                        if act_in_list.original_connector_id == actual_connector_id:
                            first_connector_action_idx = idx
                            break
                    
                    if first_connector_action_idx != -1:
                        current_action_index = first_connector_action_idx
                        print(f"{env.now:.2f}: {act_log} - Jumping to first connector action (index {current_action_index}) for connector {actual_connector_id}. Will resume at index {target_index_after_self_initiated_block_actions} after connector actions completion.")
                        sim_log.append({"time": env.now, "entity_id": entity.id, "block_id": block_config.id, "connector_id": action.original_connector_id, "action_name": action.name, "action_type": action.type, "parameters": action.parameters, "event": "Action finished (self-route initiated, jumping to connector actions)"})
                        print(f"{env.now:.2f}: {act_log} - Finished (self-route jump to index {current_action_index}).")
                        continue 
                    else:
                        print(f"{env.now:.2f}: {act_log} - Self-route specified, but no connector actions found for {actual_connector_id}. Continuing to next action.")
                        target_index_after_self_initiated_block_actions = -1 # 점프가 발생하지 않았으므로 리셋

                else:
                    # 다른 블록으로의 실제 라우팅
                    # MODIFIED: 연결 설정을 참조하여 올바른 파이프 찾기
                    actual_pipe_id = None
                    
                    # target_connector_id가 직접 파이프인지 확인
                    if target_connector_id in block_pipes:
                        actual_pipe_id = target_connector_id
                        print(f"{env.now:.2f}: {act_log} - Direct pipe found: {target_connector_id}")
                    else:
                        # 연결 설정에서 from_connector_id로 사용되는 target_connector_id를 찾아서 to_connector_id를 파이프로 사용
                        # 전역 연결 설정에 접근해야 함 (setup 데이터 필요)
                        # 임시 해결책: out_pipe_connectors 사용
                        if target_connector_id in out_pipe_connectors:
                            actual_pipe_id = out_pipe_connectors[target_connector_id]
                            print(f"{env.now:.2f}: {act_log} - Found pipe via connection mapping: {target_connector_id} -> {actual_pipe_id}")
                        else:
                            print(f"{env.now:.2f}: {act_log} - No connection mapping found for {target_connector_id}. Available mappings: {out_pipe_connectors}")
                    
                    if actual_pipe_id and actual_pipe_id in block_pipes:
                        target_pipe = block_pipes[actual_pipe_id]
                        print(f"{env.now:.2f}: {act_log} - DEBUG: Using pipe: '{actual_pipe_id}' (Type: {type(actual_pipe_id)}) in block_pipes. Keys available: {list(block_pipes.keys())}")
                        print(f"{env.now:.2f}: {act_log} - Putting Entity {entity.id} to Block {target_block_id_str}, Connector_Pipe {actual_pipe_id}.")
                        # 엔티티가 이동하기 전에 현재 블록에서의 위치는 유지됨. 파이프로 보내는 것.
                        # 받는 쪽에서 entity.set_location() 호출 예정.
                        try:
                            yield target_pipe.put(entity) # MODIFIED
                            # MODIFIED: 연결점 액션 내에서의 라우팅은 routed_out 설정하지 않음
                            # 연결점 액션 시퀀스를 중단하지 않고 계속 진행하도록 함
                            if action.original_connector_id is None:
                                # 블록 액션에서의 라우팅은 기존대로 routed_out 설정
                                routed_out = True 
                            else:
                                # 연결점 액션에서의 라우팅은 routed_out 설정하지 않음
                                print(f"{env.now:.2f}: {act_log} - Connector action routing completed. Continuing with remaining connector actions.")
                            print(f"{env.now:.2f}: {act_log} - Entity {entity.id} successfully put into pipe {actual_pipe_id}.")
                        except Exception as e_put:
                            print(f"{env.now:.2f}: {act_log} - ERROR putting entity into pipe {actual_pipe_id}: {e_put}")
                            traceback.print_exc()
                    else:
                        print(f"{env.now:.2f}: {act_log} - Failed. Target connector pipe '{target_connector_id}' -> '{actual_pipe_id}' not found for block {target_block_id_str}.")
            
            elif action.type == "custom_sink":
                print(f"{env.now:.2f}: {act_log} - Executing custom sink for entity {entity.id}.")
                if entity in active_entities_registry:
                    active_entities_registry.remove(entity)
                    print(f"{env.now:.2f}: Entity {entity.id} removed from active registry (sink).")
                    # 엔티티를 풀로 반환
                    entity_pool.return_entity(entity)
                processed_entities_count += 1
                routed_out = True 
                print(f"{env.now:.2f}: {act_log} - Finished. Processed entity. Total processed: {processed_entities_count}")
                if sim_env and hasattr(sim_env, 'stop_on_entities_processed') and sim_env.stop_on_entities_processed and processed_entities_count >= sim_env.stop_on_entities_processed: # type: ignore
                    print(f"{env.now:.2f}: Reached target processed entities ({processed_entities_count}). Stopping simulation via event.")
                    if hasattr(sim_env, 'simulation_stop_event') and sim_env.simulation_stop_event and not sim_env.simulation_stop_event.triggered: # type: ignore
                        sim_env.simulation_stop_event.succeed() # type: ignore
            
            elif action.type == "conditional_branch":
                script = action.parameters.get("script", "")
                print(f"{env.now:.2f}: {act_log} - Executing conditional branch.")
                
                if script:
                    try:
                        # 스크립트를 줄별로 파싱하여 실행
                        lines = script.split('\n')
                        i = 0
                        
                        while i < len(lines):
                            line = lines[i].strip()
                            
                            # 빈 줄이나 주석 건너뛰기
                            if not line or line.startswith('//'):
                                i += 1
                                continue
                            
                            # IF 조건문 처리
                            if line.startswith('if '):
                                condition_match = re.match(r'^if\s+(.+?)\s*=\s*(true|false)$', line)
                                if condition_match:
                                    signal_name = condition_match.group(1).strip()
                                    expected_value = condition_match.group(2) == 'true'
                                    
                                    print(f"{env.now:.2f}: {act_log} - Checking condition: {signal_name} = {expected_value}")
                                    
                                    # 신호 값 확인
                                    condition_met = False
                                    if signal_name in signals:
                                        current_value = signals[signal_name]["value"]
                                        condition_met = (current_value == expected_value)
                                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' = {current_value}, condition {'met' if condition_met else 'not met'}")
                                    else:
                                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' not found, condition not met")
                                    
                                    i += 1
                                    
                                    # 조건이 만족되면 하위 액션들 실행
                                    if condition_met:
                                        while i < len(lines) and lines[i].startswith('\t'):
                                            sub_line = lines[i].strip()
                                            print(f"{env.now:.2f}: {act_log} - Executing sub-action: {sub_line}")
                                            
                                            # 하위 액션 실행
                                            sub_action_result = yield from execute_script_line(env, sub_line, entity, act_log, out_pipe_connectors)
                                            
                                            # 점프 명령어 처리
                                            if sub_action_result and sub_action_result.get('jump_to_line') is not None:
                                                jump_target = sub_action_result.get('jump_to_line')
                                                print(f"{env.now:.2f}: {act_log} - Jump command received, jumping to line {jump_target + 1}")
                                                i = jump_target
                                                break
                                            
                                            # 라우팅이 발생했으면 조건부 실행 중단
                                            if sub_action_result and sub_action_result.get('routed_out'):
                                                routed_out = True
                                                break
                                            
                                            i += 1
                                        
                                        # 라우팅이 발생했으면 조건부 실행 전체 중단
                                        if routed_out:
                                            break
                                    else:
                                        # 조건이 맞지 않으면 하위 액션들 건너뛰기
                                        while i < len(lines) and lines[i].startswith('\t'):
                                            i += 1
                                else:
                                    print(f"{env.now:.2f}: {act_log} - Invalid if condition format: {line}")
                                    i += 1
                            else:
                                # if 블록 외부의 명령들을 else 케이스로 처리 (모든 if 조건이 맞지 않을 때 실행)
                                print(f"{env.now:.2f}: {act_log} - Processing else case command: {line}")
                                sub_result = execute_script_line(env, entity, line, block_pipes, signals, act_log)
                                if sub_result.get('routed_out'):
                                    result['routed_out'] = True
                                    break
                                elif sub_result.get('jump_to_line') is not None:
                                    i = sub_result['jump_to_line'] - 1  # -1 because i will be incremented
                                    continue
                                i += 1
                                
                        print(f"{env.now:.2f}: {act_log} - Conditional branch execution completed.")
                        
                    except Exception as e:
                        print(f"{env.now:.2f}: {act_log} - Error executing conditional branch: {e}")
                        traceback.print_exc()
                else:
                    print(f"{env.now:.2f}: {act_log} - No script provided for conditional branch.")
            
            elif action.type == "signal_wait":
                signal_name = action.parameters.get("signal_name")
                expected_value = action.parameters.get("expected_value", True)
                print(f"{env.now:.2f}: {act_log} - Wait for signal '{signal_name}' = {expected_value}")
                
                if signal_name:
                    if signal_name in signals:
                        signal_info = signals[signal_name]
                        print(f"{env.now:.2f}: {act_log} - Waiting for '{signal_name}'=={expected_value}. Current: {signal_info['value']}")
                        
                        # MODIFIED: 현재 신호 상태와 대기 조건을 명확히 로그
                        print(f"{env.now:.2f}: {act_log} - DEBUG: Signal '{signal_name}' details - Current value: {signal_info['value']}, Expected: {expected_value}, Event processed: {signal_info['event'].processed if 'event' in signal_info else 'No event'}")
                        
                        # 조건이 만족될 때까지 대기 - 이벤트 기반 최적화
                        if signal_info["value"] != expected_value:
                            if expected_value is True:
                                # True를 기다리는 경우 이벤트 대기
                                if not signal_info["event"].processed:
                                    print(f"{env.now:.2f}: {act_log} - Waiting for signal event (Event ID: {id(signal_info['event'])})")
                                    print(f"{env.now:.2f}: {act_log} - DEBUG: This entity will wait indefinitely until '{signal_name}' becomes True")
                                    yield signal_info["event"]
                                    print(f"{env.now:.2f}: {act_log} - Signal event received, continuing...")
                                else:
                                    print(f"{env.now:.2f}: {act_log} - Signal event already processed, but value is still {signal_info['value']}")
                            else:
                                # False를 기다리는 경우 - 이벤트 기반 대기
                                if "false_waiters" not in signal_info:
                                    signal_info["false_waiters"] = []
                                wait_event = env.event()
                                signal_info["false_waiters"].append(wait_event)
                                print(f"{env.now:.2f}: {act_log} - DEBUG: This entity will wait indefinitely until '{signal_name}' becomes False")
                                yield wait_event
                                
                                # 대기 후 시뮬레이션 종료 확인 (False 대기의 경우에만)
                                if env.peek() == float('inf'):
                                    print(f"{env.now:.2f}: {act_log} - Simulation ended while waiting for False signal.")
                                    break
                        else:
                            print(f"{env.now:.2f}: {act_log} - Signal condition already met: '{signal_name}' = {signal_info['value']}")
                        
                        print(f"{env.now:.2f}: {act_log} - Signal condition met: '{signal_name}' = {signal_info['value']}")
                    else:
                        print(f"{env.now:.2f}: {act_log} - Signal '{signal_name}' not found. Creating and waiting.")
                        print(f"{env.now:.2f}: {act_log} - DEBUG: Signal '{signal_name}' does not exist. This entity will wait indefinitely until signal is created and set to {expected_value}")
                        signals[signal_name] = {"event": env.event(), "value": False}
                        if expected_value is True:
                            yield signals[signal_name]["event"]
                else:
                    print(f"{env.now:.2f}: {act_log} - 'signal_name' missing for signal_wait.")
            
            elif action.type == "action_jump":
                target_action_name = action.parameters.get("target_action_name")
                print(f"{env.now:.2f}: {act_log} - Attempting to jump to action '{target_action_name}'.")
                found_target_action_for_jump = False 
                target_idx_for_jump = -1
                for i, act in enumerate(block_config.actions):
                    is_same_context = (act.original_connector_id == action.original_connector_id)
                    if not action.original_connector_id and not act.original_connector_id:
                        is_same_context = True
                    
                    if act.name == target_action_name and is_same_context:
                        target_idx_for_jump = i
                        found_target_action_for_jump = True
                        break
                
                if found_target_action_for_jump:
                    current_action_index = target_idx_for_jump
                    print(f"{env.now:.2f}: {act_log} - Jumping to action '{target_action_name}' (index {current_action_index}).")
                    sim_log.append({"time": env.now, "entity_id": entity.id, "block_id": block_config.id, "connector_id": action.original_connector_id, "action_name": action.name, "action_type": action.type, "parameters": action.parameters, "event": "Action finished (jumped)"})
                    print(f"{env.now:.2f}: {act_log} - Finished (jumped to index {current_action_index}).")
                    continue
                else:
                    print(f"{env.now:.2f}: {act_log} - Failed. Target action '{target_action_name}' not found in the current context or block.")

            sim_log.append({"time": env.now, "entity_id": entity.id, "block_id": block_config.id, "connector_id": action.original_connector_id, "action_name": action.name, "action_type": action.type, "parameters": action.parameters, "event": "Action finished"})
            print(f"{env.now:.2f}: {act_log} - Finished.")

            if routed_out:
                print(f"{env.now:.2f}: {entity_log_prefix} Entity routed out. Ending actions for this entity in this block/CP.")
                target_index_after_self_initiated_block_actions = -1 
                break 
            
            if target_index_after_self_initiated_block_actions != -1:
                # MODIFIED: 연결점 액션과 블록 액션을 구분하여 처리
                is_current_action_a_connector_action = (action.original_connector_id is not None)
                
                is_next_action_not_same_connector_or_end = True 
                if (current_action_index + 1) < len(block_config.actions):
                    next_action = block_config.actions[current_action_index + 1]
                    # 같은 연결점의 액션이거나 블록 액션이면 계속 진행
                    if (next_action.original_connector_id == action.original_connector_id) or (next_action.original_connector_id is None):
                        is_next_action_not_same_connector_or_end = False
                
                # 현재가 연결점 액션이고, 다음이 다른 연결점 액션이거나 끝이면 점프
                if is_current_action_a_connector_action and is_next_action_not_same_connector_or_end:
                    # MODIFIED: 연결점 액션 완료 후에는 엔티티 처리 완료로 간주
                    print(f"{env.now:.2f}: {entity_log_prefix} Connector actions sequence completed. Entity processing finished in this block.")
                    target_index_after_self_initiated_block_actions = -1
                    routed_out = True  # 연결점 액션 완료 후 엔티티를 라우팅된 것으로 처리
                    break  # while 루프 종료

            current_action_index += 1
        
        if not routed_out: # 모든 액션을 수행했으나 명시적으로 다른 곳으로 route되지 않은 경우 (소스 블록이거나, 마지막 액션이 route가 아닌 경우)
            if is_source_block:
                 print(f"{env.now:.2f}: {entity_log_prefix} Source block finished processing entity (or no actions to take after generation). Entity {entity.id} remains in source block if not routed by its connector actions.")
            else: # 일반 블록인데 모든 액션 후 route_out 안된 경우. (예: 마지막 액션이 delay)
                 print(f"{env.now:.2f}: {entity_log_prefix} Finished all actions in block, but not explicitly routed out. Entity {entity.id} might be stuck if not handled by subsequent block logic or if it's a sink-like behavior without custom_sink.")

        # 한 엔티티에 대한 처리가 끝났거나, 엔티티가 라우팅되어 나갔음.
        # 루프의 처음으로 돌아가 다음 엔티티를 받거나 생성.
        print(f"{env.now:.2f}: {block_log_prefix} Completed processing for an entity or entity routed. Ready for next.")
        
        # yield env.timeout(0.000001) # MODIFIED - 일단 주석 처리하여 시간 진행 관찰

@app.post("/simulation/run", response_model=SimulationRunResult) # response_model 수정
async def run_simulation_endpoint(setup: SimulationSetup):
    global sim_env, sim_log, processed_entities_count, block_pipes, signals, active_entities_registry
    global block_entity_counts
    sim_env = simpy.Environment()
    sim_env.initial_entity_limit_for_source = setup.initial_entities 

    sim_log = []
    processed_entities_count = 0
    block_pipes = {}
    signals = {}
    active_entities_registry.clear() # 실행 시마다 초기화
    block_entity_counts = {}  # 블록 엔티티 카운트 초기화

    # 전역 신호 초기화 (initial_signals 사용)
    if setup.initial_signals:
        for signal_name, initial_value in setup.initial_signals.items():
            signals[signal_name] = {"event": sim_env.event(), "value": False}
            if initial_value is True:
                signals[signal_name]["event"].succeed()
                signals[signal_name]["value"] = True
            print(f"Initialized global signal: {signal_name} = {signals[signal_name]['value']}")

    # 1. 파이프 생성 (커넥터 ID 기반)
    # 모든 유니크한 "to_connector_id"와 "from_connector_id"에 대해 파이프를 만들 수 있으나,
    # 여기서는 연결 설정에 명시된 파이프만 생성
    # 하나의 커넥터는 하나의 파이프(Store)에 연결됨.
    # from_connector_id (output) -> pipe -> to_connector_id (input)
    # 파이프 ID는 연결의 고유 식별자로 사용 (예: from_block_id.conn_id -> to_block_id.conn_id)
    # 또는 단순히 to_block_id.conn_id (즉, 입력 커넥터 ID)를 파이프 ID로 사용할 수 있음.
    # 여기서는 "수신하는 쪽의 커넥터 ID"를 파이프의 key로 사용.
    for conn in setup.connections:
        # 파이프는 데이터가 흘러 들어가는 "to_connector_id"를 기준으로 생성
        # 한 수신 커넥터는 하나의 Store를 가짐.
        if conn.to_connector_id not in block_pipes:
            block_pipes[conn.to_connector_id] = simpy.Store(sim_env)
            print(f"Created pipe for connector_id: {conn.to_connector_id}")

    # 2. 블록 프로세스 설정
    for block_config in setup.blocks:
        in_pipe_ids_for_block = []
        out_pipe_connectors_for_block = {} # key: block's own connector_id (output), value: target pipe_id (which is a to_connector_id)

        for conn in setup.connections:
            if conn.to_block_id == block_config.id:
                # 이 블록으로 들어오는 연결이므로, 해당 파이프 ID(conn.to_connector_id)를 입력으로 추가
                if conn.to_connector_id not in in_pipe_ids_for_block:
                    in_pipe_ids_for_block.append(conn.to_connector_id)
            
            if conn.from_block_id == block_config.id:
                # 이 블록에서 나가는 연결이므로, 이 블록의 from_connector_id가 어떤 파이프(수신측 to_connector_id)로 연결되는지 매핑
                out_pipe_connectors_for_block[conn.from_connector_id] = conn.to_connector_id
        
        # MODIFIED: 소스 블록 초기화 로직 수정 - custom_sink가 있는 블록은 제외
        has_custom_sink = any(action.type == "custom_sink" for action in block_config.actions)
        is_source = not in_pipe_ids_for_block and not has_custom_sink
        
        print(f"    Block {block_config.id} ('{block_config.name}') - Capacity: {block_config.capacity}")
        
        if is_source:
            print(f"    Source Block {block_config.id} ('{block_config.name}') initializing.")
            source_entity_request_events[block_config.id] = sim_env.event() 
            source_entity_generated_counts[block_config.id] = 0
            
            # 첫 스텝에서 initial_entities 만큼 생성하도록 요청
            # 현재 block_process는 요청당 1개만 생성하므로, initial_entities > 0 이면 첫번째 요청을 여기서 트리거
            if setup.initial_entities > 0:
                print(f"    Triggering initial entity generation request for source block {block_config.id} (for the 1st of {setup.initial_entities} entities).")
                if not source_entity_request_events[block_config.id].triggered:
                     source_entity_request_events[block_config.id].succeed()
                     # block_process가 이 이벤트를 소비한 후, 다음 요청을 위해 새 이벤트가 필요함.
                     # 이 새 이벤트는 block_process가 yield에서 깨어난 후, 다음 루프 시작 전 또는 
                     # 후속 스텝 요청 시 step_simulation_endpoint에서 만들어져야 함.
                     # 여기서는 일단 트리거만. 새 이벤트는 후속 스텝 로직 또는 block_process 내부에서 관리.
                     # -> 수정: 트리거 후 즉시 새 이벤트로 교체하여 다음 스텝/요청을 대비.
                     # 1부터 시작하도록 수정
                     source_entity_request_events[block_config.id] = sim_env.event()
        else:
            print(f"    Non-source Block {block_config.id} ('{block_config.name}') - Has input pipes: {bool(in_pipe_ids_for_block)}, Has custom_sink: {has_custom_sink}, Capacity: {block_config.capacity}")
        
        sim_env.process(block_process(sim_env, block_config, in_pipe_ids_for_block, out_pipe_connectors_for_block))
        print(f"    Block {block_config.id} ('{block_config.name}'): Input pipe IDs: {in_pipe_ids_for_block}, Output connectors: {out_pipe_connectors_for_block}")

    print(f"  Registering {len(setup.blocks)} block processes...")
    print(f"Initial sim_env.step() at time {sim_env.now}. Event queue length: {len(getattr(sim_env, '_queue', []))}")

    print(f"Starting simulation. Initial entities: {setup.initial_entities}, Stop time: {setup.stop_time}, Stop entities: {setup.stop_entities_processed}")
    sim_log.append({"time": sim_env.now, "event": "Simulation run started", "details": setup.model_dump(exclude_none=True)})

    run_until_time = float('inf')
    if setup.stop_time is not None:
        run_until_time = setup.stop_time
    
    if setup.stop_entities_processed is not None and setup.stop_entities_processed > 0:
        # 엔티티 개수 기반 중지 로직
        async def entity_count_monitor(env, target_count):
            global processed_entities_count
            while processed_entities_count < target_count:
                await env.timeout(0.1) # 짧은 간격으로 체크
                if env.peek() >= run_until_time: # 설정된 최대 시간 도달 시 중지
                    break
            print(f"Target entities ({target_count}) processed or max time reached. Stopping simulation.")
            # 모든 프로세스가 자연스럽게 종료되도록 유도하거나, 강제 중단 이벤트 발생 (여기서는 자연 종료 유도)
            # 또는 env.interrupt() 사용 고려
            if sim_env and not sim_env._stopped:
                 sim_env.stop() # 명시적으로 시뮬레이션 중단

        sim_env.process(entity_count_monitor(sim_env, setup.stop_entities_processed))
        try:
            sim_env.run(until=run_until_time) 
        except simpy.core.StopSimulation:
            print("Simulation stopped by entity count monitor or other stop event.")
            pass # 정상적인 중단
    else:
        sim_env.run(until=run_until_time if run_until_time != float('inf') else None) # None이면 무한 실행 (다른 중지 조건 필요)

    print(f"Simulation finished at time {sim_env.now:.2f}. Total processed: {processed_entities_count}")
    sim_log.append({"time": sim_env.now, "event": "Simulation run finished", "total_processed": processed_entities_count})

    final_active_entities = get_active_entity_states()
    print(f"Simulation finished. Active entities at end: {len(final_active_entities)}")

    # MODIFIED: inf 값을 JSON 호환 값으로 변환
    final_time = sim_env.now
    if final_time == float('inf'):
        final_time = -1  # 무한대를 -1로 표현

    return SimulationRunResult(
        message="Simulation complete", 
        log=sim_log, 
        total_entities_processed=processed_entities_count, 
        final_time=final_time,
        active_entities=final_active_entities
    )


@app.post("/simulation/step", response_model=SimulationStepResult) # response_model 수정
async def step_simulation_endpoint(setup: Optional[SimulationSetup] = None):
    global sim_env, sim_log, processed_entities_count, signals, block_pipes, active_entities_registry
    global source_entity_request_events, source_entity_generated_counts

    current_event_description = "No event processed."
    
    # MODIFIED: 시뮬레이션 초기화 감지 개선
    is_first_step = (sim_env is None)
    
    # setup이 있고 현재 시뮬레이션이 있다면 초기화 요청으로 간주
    if setup and sim_env:
        print("Setup provided with existing simulation. Treating as reset request.")
        is_first_step = True

    if is_first_step:
        print("Initializing simulation environment for step (first step or reset)...")
        if not setup: # 첫 스텝인데 setup 데이터가 없으면 에러
            raise HTTPException(status_code=400, detail="SimulationSetup data is required for the first step or reset.")

        # MODIFIED: 기존 시뮬레이션 상태 완전 초기화
        sim_env = None
        sim_log = []
        processed_entities_count = 0
        signals = {}
        block_pipes = {}
        active_entities_registry = set()
        source_entity_request_events = {}
        source_entity_generated_counts = {}
        block_entity_counts = {}  # 블록 엔티티 카운트 초기화

        sim_env = simpy.Environment()
        sim_env.initial_entity_limit_for_source = setup.initial_entities 

        # 전역 신호 초기화 (initial_signals 사용)
        if setup.initial_signals:
            for signal_name, initial_value in setup.initial_signals.items():
                signals[signal_name] = {"event": sim_env.event(), "value": False}
                if initial_value is True:
                    signals[signal_name]["event"].succeed()
                    signals[signal_name]["value"] = True
                print(f"Initialized global signal: {signal_name} = {signals[signal_name]['value']}")

        # 1. 파이프 생성 (커넥터 ID 기반)
        # 모든 유니크한 "to_connector_id"와 "from_connector_id"에 대해 파이프를 만들 수 있으나,
        # 여기서는 연결 설정에 명시된 파이프만 생성
        # 하나의 커넥터는 하나의 파이프(Store)에 연결됨.
        # from_connector_id (output) -> pipe -> to_connector_id (input)
        # 파이프 ID는 연결의 고유 식별자로 사용 (예: from_block_id.conn_id -> to_block_id.conn_id)
        # 또는 단순히 to_block_id.conn_id (즉, 입력 커넥터 ID)를 파이프 ID로 사용할 수 있음.
        # 여기서는 "수신하는 쪽의 커넥터 ID"를 파이프의 key로 사용.
        for conn in setup.connections:
            # 파이프는 데이터가 흘러 들어가는 "to_connector_id"를 기준으로 생성
            # 한 수신 커넥터는 하나의 Store를 가짐.
            if conn.to_connector_id not in block_pipes:
                block_pipes[conn.to_connector_id] = simpy.Store(sim_env)
                print(f"Created pipe for connector_id: {conn.to_connector_id}")

        # 2. 블록 프로세스 설정
        for block_config in setup.blocks:
            in_pipe_ids_for_block = []
            out_pipe_connectors_for_block = {} # key: block's own connector_id (output), value: target pipe_id (which is a to_connector_id)

            for conn in setup.connections:
                if conn.to_block_id == block_config.id:
                    # 이 블록으로 들어오는 연결이므로, 해당 파이프 ID(conn.to_connector_id)를 입력으로 추가
                    if conn.to_connector_id not in in_pipe_ids_for_block:
                        in_pipe_ids_for_block.append(conn.to_connector_id)
            
                if conn.from_block_id == block_config.id:
                    # 이 블록에서 나가는 연결이므로, 이 블록의 from_connector_id가 어떤 파이프(수신측 to_connector_id)로 연결되는지 매핑
                    out_pipe_connectors_for_block[conn.from_connector_id] = conn.to_connector_id
        
            # MODIFIED: 소스 블록 초기화 로직 수정 - custom_sink가 있는 블록은 제외
            has_custom_sink = any(action.type == "custom_sink" for action in block_config.actions)
            is_source = not in_pipe_ids_for_block and not has_custom_sink
            
            print(f"    Block {block_config.id} ('{block_config.name}') - Capacity: {block_config.capacity}")
            
            if is_source:
                print(f"    Source Block {block_config.id} ('{block_config.name}') initializing.")
                source_entity_request_events[block_config.id] = sim_env.event() 
                source_entity_generated_counts[block_config.id] = 0
                
                # 첫 스텝에서 initial_entities 만큼 생성하도록 요청
                # 현재 block_process는 요청당 1개만 생성하므로, initial_entities > 0 이면 첫번째 요청을 여기서 트리거
                if setup.initial_entities > 0:
                    print(f"    Triggering initial entity generation request for source block {block_config.id} (for the 1st of {setup.initial_entities} entities).")
                    if not source_entity_request_events[block_config.id].triggered:
                         source_entity_request_events[block_config.id].succeed()
                         # block_process가 이 이벤트를 소비한 후, 다음 요청을 위해 새 이벤트가 필요함.
                         # 이 새 이벤트는 block_process가 yield에서 깨어난 후, 다음 루프 시작 전 또는 
                         # 후속 스텝 요청 시 step_simulation_endpoint에서 만들어져야 함.
                         # 여기서는 일단 트리거만. 새 이벤트는 후속 스텝 로직 또는 block_process 내부에서 관리.
                         # -> 수정: 트리거 후 즉시 새 이벤트로 교체하여 다음 스텝/요청을 대비.
                         # 1부터 시작하도록 수정
                         source_entity_request_events[block_config.id] = sim_env.event()
            else:
                print(f"    Non-source Block {block_config.id} ('{block_config.name}') - Has input pipes: {bool(in_pipe_ids_for_block)}, Has custom_sink: {has_custom_sink}, Capacity: {block_config.capacity}")
            
            sim_env.process(block_process(sim_env, block_config, in_pipe_ids_for_block, out_pipe_connectors_for_block))
            print(f"    Block {block_config.id} ('{block_config.name}'): Input pipe IDs: {in_pipe_ids_for_block}, Output connectors: {out_pipe_connectors_for_block}")

        print(f"  Registering {len(setup.blocks)} block processes completed.")
        print(f"Initial sim_env.step() at time {sim_env.now}. Event queue length: {len(getattr(sim_env, '_queue', []))}")

        try:
            current_event_description = f"Initial processes started. Next event at: {sim_env.peek() if getattr(sim_env, '_queue', []) else 'N/A'}"
            if getattr(sim_env, '_queue', []): # 이벤트가 있을 때만 step() 호출
                 sim_env.step() 
            else:
                current_event_description = "No events to process at initialization."
        except simpy.core.EmptySchedule: 
            current_event_description = "Simulation ended: No events in schedule after initialization."
        except Exception as e:
            current_event_description = f"Error during initial step: {str(e)}"
            traceback.print_exc()
        
        print(f"After initial step, sim_env.now: {sim_env.now}, Event queue length: {len(getattr(sim_env, '_queue', []))}. Logs added: {len(sim_log)}")
        
        # MODIFIED: current_signals 추출 로직 개선
        current_signals_dict = {}
        if signals:
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict) and 'value' in signal_data:
                    current_signals_dict[signal_name] = signal_data['value']
                else:
                    current_signals_dict[signal_name] = bool(signal_data)
        
        # MODIFIED: inf 값을 JSON 호환 값으로 변환
        current_time = sim_env.now
        if current_time == float('inf'):
            current_time = -1  # 무한대를 -1로 표현
            current_event_description = "Simulation halted: waiting for external input"
        
        return SimulationStepResult(
            time=current_time,
            event_description=current_event_description,
            entities_processed_total=processed_entities_count,
            active_entities=get_active_entity_states(),
            current_signals=current_signals_dict if current_signals_dict else None
        )

    else: # Subsequent step
        if not sim_env:
             raise HTTPException(status_code=500, detail="Simulation environment not initialized. Perform a first step with setup data.")

        print(f"--- Performing subsequent step. Current sim_env.now: {sim_env.now} ---")

        # 후속 스텝에서는 모든 소스 블록에 대해 새 엔티티 생성을 "요청"
        # (block_process는 요청당 1개의 엔티티만 생성)
        for block_id, event in list(source_entity_request_events.items()): # list로 복사하여 반복 중 변경 가능하도록
            # 이전에 생성된 엔티티 수와 initial_entities를 비교하여 더 생성할지 결정하는 로직 추가 가능
            # 예: if source_entity_generated_counts.get(block_id, 0) < setup.initial_entities (이러려면 setup이 전달되어야 함)
            # 지금은 매 스텝마다 1개씩 추가 생성 요청
            if block_id in source_entity_generated_counts: # 해당 블록이 소스 블록으로 등록되었는지 확인
                # MODIFIED: 현재 활성 엔티티가 있고 아직 처리되지 않았다면 새 요청 생성 안함
                has_active_entity_from_this_source = any(
                    entity.current_block_id == block_id for entity in active_entities_registry
                )
                entities_already_generated = source_entity_generated_counts.get(block_id, 0)
                
                if has_active_entity_from_this_source and entities_already_generated > 0:
                    print(f"  Source block {block_id} has active entity. Skipping new generation request.")
                    continue
                
                if not event.triggered:
                    print(f"  Triggering next entity generation for source block: {block_id} (Event ID: {id(event)}).")
                    event.succeed()
                    source_entity_request_events[block_id] = sim_env.event() # 새 이벤트로 교체
                    print(f"  Replaced event for source block {block_id} with new event (Event ID: {id(source_entity_request_events[block_id])}).")
                else:
                    # 이미 트리거된 이벤트라면, block_process가 아직 처리 중일 수 있음.
                    # 이 경우 새 이벤트를 만들어서 교체해두면, block_process가 현재 이벤트를 처리하고 다음 루프에서 새 이벤트를 기다림.
                    print(f"  Source block {block_id} event (ID: {id(event)}) was already triggered. Ensuring new event is ready (New ID: {id(source_entity_request_events[block_id])}).")
                    # 위에서 이미 succeed() 후 새 이벤트로 교체되었으므로, 이 로직은 약간 중복될 수 있으나,
                    # 안전하게 항상 새 이벤트를 참조하도록 보장.
                    if source_entity_request_events[block_id].triggered : # 만약 교체된 새 이벤트마저도 어떤 이유로 triggered 상태라면 (이론상 거의 없음)
                        source_entity_request_events[block_id] = sim_env.event() # 정말 새것으로 교체

        if not getattr(sim_env, '_queue', []): 
            current_event_description = "Simulation ended: No more events in schedule."
            print(current_event_description)
        else:
            next_event_time_peek = sim_env.peek()
            print(f"  Stepping from {sim_env.now}. Event queue length: {len(sim_env._queue)}. Next event time: {next_event_time_peek}")
            
            # DEBUG: 이벤트 큐 상세 분석
            print(f"  DEBUG: Event queue details:")
            for i, event in enumerate(sim_env._queue[:5]):  # 처음 5개 이벤트만 출력
                print(f"    Event {i}: time={event[0]}, priority={event[1]}, event_id={id(event[2])}")
            
            log_before_step = len(sim_log)
            try:
                # MODIFIED: 엔티티 블록 이동 기반 스텝 실행 - 블록 간 이동 시에만 스텝 종료
                step_limit = 50  # 무한루프 방지 (블록 이동은 더 많은 내부 처리가 필요할 수 있음)
                steps_taken = 0
                entity_movement_detected = False
                
                # 스텝 시작 전 엔티티 위치 상태 저장
                initial_entity_states = {entity.id: entity.current_block_id for entity in active_entities_registry}
                initial_processed_count = processed_entities_count
                
                print(f"  Entity movement detection - Initial states: {len(initial_entity_states)} entities")
                
                while steps_taken < step_limit and not entity_movement_detected:
                    if next_event_time_peek > sim_env.now:
                        # 시간이 진행되는 경우 - 한 번 실행하고 엔티티 이동 체크
                        print(f"  Time will advance from {sim_env.now} to {next_event_time_peek}. Taking step.")
                        sim_env.step()
                        
                        # 엔티티 이동 감지
                        entity_movement_detected = check_entity_movement(initial_entity_states, initial_processed_count)
                        if entity_movement_detected:
                            current_event_description = f"Entity movement detected at time {sim_env.now:.2f}."
                        else:
                            current_event_description = f"Time advanced to {sim_env.now:.2f} (no entity movement)."
                    else:
                        # 현재 시간에 이벤트 처리
                        sim_env.step()
                        
                        # 엔티티 이동 감지
                        entity_movement_detected = check_entity_movement(initial_entity_states, initial_processed_count)
                        if entity_movement_detected:
                            # 로그에서 실제 이동 내용 찾기
                            movement_description = get_latest_movement_description()
                            current_event_description = movement_description
                            print(f"  Entity movement detected: {movement_description}")
                        
                        steps_taken += 1
                        
                        # 다음 이벤트 시간 업데이트
                        if getattr(sim_env, '_queue', []):
                            next_event_time_peek = sim_env.peek()
                        else:
                            break  # 이벤트 큐가 비었으면 종료
                
                if not entity_movement_detected and steps_taken >= step_limit:
                    current_event_description = f"Processed {steps_taken} events at time {sim_env.now:.2f} (no entity movement)."
                elif not entity_movement_detected:
                    current_event_description = f"No entity movement detected. Current time: {sim_env.now:.2f}."

            except simpy.core.EmptySchedule:
                current_event_description = "Simulation ended: No events in schedule."
            except RuntimeError as re: # e.g. "No more events." if step() is called on an empty queue after peek()
                if "No more events" in str(re):
                    current_event_description = "Simulation ended: No more events in schedule (RuntimeError)."
                else:
                    current_event_description = f"RuntimeError during step: {str(re)}"
                    traceback.print_exc()
            except Exception as e:
                current_event_description = f"Error during step: {str(e)}"
                traceback.print_exc()

            print(f"  Stepped to {sim_env.now}. Event queue length: {len(getattr(sim_env, '_queue', []))}. Logs added: {len(sim_log) - log_before_step}")

        active_entities = get_active_entity_states()
        print(f"DEBUG: get_active_entity_states returned {len(active_entities)} entities.")
        print(f"DEBUG step_simulation_endpoint: Returning processed_entities_count = {processed_entities_count}")

        # MODIFIED: current_signals 추출 로직 개선
        current_signals_dict = {}
        if signals:
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict) and 'value' in signal_data:
                    current_signals_dict[signal_name] = signal_data['value']
                else:
                    current_signals_dict[signal_name] = bool(signal_data)

        # MODIFIED: inf 값을 JSON 호환 값으로 변환
        current_time = sim_env.now
        if current_time == float('inf'):
            current_time = -1  # 무한대를 -1로 표현
            current_event_description = "Simulation halted: waiting for external input"

        return SimulationStepResult(
            time=current_time,
            event_description=current_event_description,
            entities_processed_total=processed_entities_count,
            active_entities=active_entities,
            current_signals=current_signals_dict if current_signals_dict else None
        )

# 배치 스텝 실행 엔드포인트 (성능 최적화)
@app.post("/simulation/batch-step", response_model=BatchStepResult)
async def batch_step_simulation_endpoint(request: BatchStepRequest):
    global sim_env, processed_entities_count
    
    if not sim_env:
        raise HTTPException(status_code=400, detail="시뮬레이션이 초기화되지 않았습니다. 먼저 step 엔드포인트를 호출하세요.")
    
    steps_executed = 0
    final_event_description = ""
    
    try:
        # 배치로 여러 스텝 실행
        for i in range(request.steps):
            if getattr(sim_env, '_queue', []):
                next_event_time_peek = sim_env.peek()
                
                # 스텝 시작 전 엔티티 위치 상태 저장
                initial_entity_states = {entity.id: entity.current_block_id for entity in active_entities_registry}
                initial_processed_count = processed_entities_count
                
                # 단일 스텝 실행
                step_limit = 10  # 배치에서는 더 작은 스텝 단위로
                step_steps_taken = 0
                entity_movement_detected = False
                
                while step_steps_taken < step_limit and not entity_movement_detected:
                    if next_event_time_peek > sim_env.now:
                        sim_env.step()
                        entity_movement_detected = check_entity_movement(initial_entity_states, initial_processed_count)
                        if entity_movement_detected:
                            final_event_description = get_latest_movement_description()
                        break
                    else:
                        sim_env.step()
                        entity_movement_detected = check_entity_movement(initial_entity_states, initial_processed_count)
                        if entity_movement_detected:
                            final_event_description = get_latest_movement_description()
                        step_steps_taken += 1
                        
                        if getattr(sim_env, '_queue', []):
                            next_event_time_peek = sim_env.peek()
                        else:
                            break
                
                steps_executed += 1
                
                if not entity_movement_detected:
                    break
            else:
                final_event_description = "시뮬레이션 완료: 더 이상 처리할 이벤트가 없습니다."
                break
                
    except simpy.core.EmptySchedule:
        final_event_description = "시뮬레이션 완료: 스케줄이 비었습니다."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 스텝 실행 중 오류 발생: {str(e)}")
    
    # 현재 활성 엔티티 상태 수집
    active_entities = get_active_entity_states()
    
    # MODIFIED: inf 값을 JSON 호환 값으로 변환
    current_time = sim_env.now
    if current_time == float('inf'):
        current_time = -1  # 무한대를 -1로 표현
        final_event_description = "Simulation halted: waiting for external input"
    
    return BatchStepResult(
        message=f"{steps_executed}개 스텝 배치 실행 완료",
        steps_executed=steps_executed,
        final_event_description=final_event_description,
        log=sim_log[-50:],  # 최근 50개 로그만 반환
        current_time=current_time,
        active_entities=active_entities,
        total_entities_processed=processed_entities_count
    )

# MODIFIED: 시뮬레이션 초기화 전용 엔드포인트 추가
@app.post("/simulation/reset")
async def reset_simulation_endpoint():
    global sim_env, sim_log, processed_entities_count, signals, block_pipes, active_entities_registry
    global source_entity_request_events, source_entity_generated_counts, block_entity_counts
    
    print("Resetting simulation state...")
    sim_env = None
    sim_log = []
    processed_entities_count = 0
    signals = {}
    block_pipes = {}
    active_entities_registry = set()
    source_entity_request_events = {}
    source_entity_generated_counts = {}
    block_entity_counts = {}  # 블록 엔티티 카운트 초기화
    entity_pool.pool.clear()  # 엔티티 풀도 초기화
    
    return {"message": "Simulation reset successfully", "time": 0.0}

@app.get("/")
async def read_root():
    return {"message": "SimPy Process Simulation API - v2.1"}

@app.get("/simulation/load-base-config")
async def load_base_config():
    """base.json 파일을 읽어서 기본 설정을 반환합니다."""
    try:
        import json
        import os
        
        # 여러 경로를 시도해보기
        possible_paths = [
            # 현재 working directory 기준
            os.path.join(os.getcwd(), "base.json"),
            # backend 폴더 기준 상위 디렉토리
            os.path.join(os.path.dirname(__file__), "..", "..", "base.json"),
            # simulation 폴더의 base.json 파일 경로
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "base.json"),
            # 절대 경로로 시도 (Windows)
            "C:\\coding\\simulation\\base.json",
            # 절대 경로로 시도 (Unix-like)
            "/c/coding/simulation/base.json",
            # 상대 경로로 시도  
            "../../base.json",
            "../base.json",
            "base.json",
            # app 폴더 기준
            os.path.join(os.path.dirname(__file__), "base.json"),
            # backend 폴더 기준
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "base.json"),
        ]
        
        base_config_path = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                base_config_path = abs_path
                print(f"Found base.json at: {abs_path}")
                break
        
        if not base_config_path:
            # 디버깅을 위해 현재 경로와 파일 존재 여부 출력
            current_dir = os.getcwd()
            script_dir = os.path.dirname(__file__)
            file_exists_info = []
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                exists = os.path.exists(abs_path)
                file_exists_info.append(f"{abs_path}: {exists}")
            
            # 현재 디렉토리의 파일 목록도 출력
            current_files = []
            try:
                current_files = os.listdir(current_dir)[:10]  # 처음 10개만
            except:
                current_files = ["Cannot list files"]
            
            error_msg = (f"base.json 파일을 찾을 수 없습니다.\n"
                        f"현재 디렉토리: {current_dir}\n"
                        f"스크립트 디렉토리: {script_dir}\n"
                        f"현재 디렉토리 파일들: {current_files}\n"
                        f"시도한 경로들:\n" + "\n".join(file_exists_info))
            raise HTTPException(status_code=404, detail=error_msg)
        
        with open(base_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # globalSignals를 initial_signals로 변환
        if 'globalSignals' in config and config['globalSignals']:
            initial_signals = {}
            for signal in config['globalSignals']:
                signal_name = signal.get('name')
                initial_value = signal.get('initialValue', False)
                if signal_name:
                    initial_signals[signal_name] = initial_value
            
            # initial_signals를 config에 추가
            if initial_signals:
                config['initial_signals'] = initial_signals
                print(f"Converted globalSignals to initial_signals: {initial_signals}")
        
        print(f"Successfully loaded base.json from: {base_config_path}")
        return config
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"base.json 파일 형식이 올바르지 않습니다: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"base.json 파일을 읽는 중 오류가 발생했습니다: {str(e)}")

# To run this (from the 'backend' directory):
# uvicorn app.main:app --reload --port 8000 