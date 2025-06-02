import simpy
from typing import Dict, List, Any, Optional

# --- Global Simulation State ---
sim_env: Optional[simpy.Environment] = None
sim_log: List[Dict[str, Any]] = []  # To store events for step-by-step or review
processed_entities_count = 0

# 블록 간 통신을 위한 파이프 (SimPy Store)
block_pipes: Dict[str, simpy.Store] = {}  # key: connector_id, value: Store

# 신호 관리를 위한 딕셔너리 (이벤트 기반 최적화)
signals: Dict[str, Dict[str, Any]] = {}

# 블록별 현재 엔티티 수 추적
block_entity_counts: Dict[str, int] = {}  # key: block_id, value: current entity count

# 소스 블록이 다음 엔티티를 생성하도록 요청하는 이벤트 (스텝 실행용)
source_entity_request_events: Dict[str, simpy.Event] = {}  # key: block_id, value: simpy.Event

# 소스 블록이 현재까지 생성한 엔티티 수 (스텝 실행용)
source_entity_generated_counts: Dict[str, int] = {}  # key: block_id, value: int

# 전체 시뮬레이션에서 이 소스 블록이 생성해야 하는 총 엔티티 수 (스텝 실행용)
source_entity_total_limits: Dict[str, int] = {}

def reset_simulation_state():
    """시뮬레이션 상태를 모두 초기화합니다."""
    global sim_env, sim_log, processed_entities_count
    global block_pipes, signals, block_entity_counts
    global source_entity_request_events, source_entity_generated_counts, source_entity_total_limits
    
    # 🔥 SimPy 환경을 완전히 제거
    if sim_env is not None:
        # 실행 중인 모든 프로세스 강제 종료
        sim_env = None
    
    sim_log.clear()
    processed_entities_count = 0
    block_pipes.clear()
    signals.clear()
    block_entity_counts.clear()
    source_entity_request_events.clear()
    source_entity_generated_counts.clear()
    source_entity_total_limits.clear()
    
    # 🔥 엔티티 레지스트리 완전 정리
    from .entity import active_entities_registry
    # 모든 엔티티를 명시적으로 제거
    for entity_id in list(active_entities_registry.keys()):
        entity = active_entities_registry[entity_id]
        entity.remove()
    
    # 추가 안전장치로 레지스트리 다시 클리어
    active_entities_registry.clear()
    
    print("[RESET] 새로운 SimPy 환경 생성됨 (시간: 0)")

def get_current_signals() -> Dict[str, bool]:
    """현재 모든 신호의 값을 반환합니다."""
    return {name: signal_data.get('value', False) for name, signal_data in signals.items()}

def set_signal(signal_name: str, value: bool, env: simpy.Environment):
    """신호 값을 설정하고 대기 중인 프로세스들을 깨웁니다."""
    if signal_name not in signals:
        signals[signal_name] = {'value': False, 'events': []}
    
    old_value = signals[signal_name]['value']
    signals[signal_name]['value'] = value
    
    if old_value != value:
        # 값이 변경되었을 때만 이벤트 발생
        events_to_succeed = signals[signal_name]['events'][:]
        signals[signal_name]['events'].clear()
        
        for event in events_to_succeed:
            if not event.triggered:
                event.succeed(value)
        
        print(f"{env.now:.2f}: Signal '{signal_name}' changed to {value}")

def wait_for_signal(signal_name: str, expected_value: bool, env: simpy.Environment) -> simpy.Event:
    """신호가 특정 값이 될 때까지 대기하는 이벤트를 반환합니다."""
    if signal_name not in signals:
        signals[signal_name] = {'value': False, 'events': []}
    
    current_value = signals[signal_name]['value']
    
    if current_value == expected_value:
        # 이미 원하는 값이면 즉시 성공하는 이벤트 반환
        event = env.event()
        event.succeed(current_value)
        return event
    else:
        # 값이 변경될 때까지 대기하는 이벤트 생성
        event = env.event()
        signals[signal_name]['events'].append(event)
        return event

def check_signal_immediate(signal_name: str, expected_value: bool) -> bool:
    """신호가 이미 원하는 값인지 즉시 확인합니다. (yield 없이)"""
    if signal_name not in signals:
        signals[signal_name] = {'value': False, 'events': []}
    
    current_value = signals[signal_name]['value']
    return current_value == expected_value

def get_active_entity_states():
    """현재 활성 엔티티 상태들을 반환"""
    from .entity import active_entities_registry
    return list(active_entities_registry.values())