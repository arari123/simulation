import random
import re
from typing import Dict, List
from .entity import active_entities_registry
from .state_manager import sim_log, processed_entities_count

def parse_delay_value(duration_str: str) -> float:
    """
    딜레이 값을 파싱합니다.
    지원 형식:
    - "5" -> 5.0
    - "3-10" -> 3.0~10.0 사이의 랜덤값
    - "2.5" -> 2.5
    - "1.5-4.2" -> 1.5~4.2 사이의 랜덤값
    """
    duration_str = duration_str.strip()
    
    # 범위 형식인지 확인 (예: "3-10", "1.5-4.2")
    if '-' in duration_str:
        parts = duration_str.split('-')
        if len(parts) == 2:
            try:
                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())
                if min_val <= max_val:
                    return random.uniform(min_val, max_val)
                else:
                    raise ValueError(f"Invalid range: min ({min_val}) > max ({max_val})")
            except ValueError as e:
                raise ValueError(f"Invalid delay range format '{duration_str}': {e}")
        else:
            raise ValueError(f"Invalid delay range format '{duration_str}': expected 'min-max'")
    else:
        # 단일 값 형식
        try:
            return float(duration_str)
        except ValueError:
            raise ValueError(f"Invalid delay value '{duration_str}': must be a number or range")

def check_entity_movement(initial_entity_states: Dict[str, str], initial_processed_count: int) -> bool:
    """
    엔티티의 움직임이 있었는지 확인합니다.
    initial_entity_states: {entity_id: block_id} 형태의 초기 상태
    initial_processed_count: 초기 처리된 엔티티 수
    """
    global processed_entities_count
    
    # 처리된 엔티티 수가 변경되었으면 움직임이 있었음
    if processed_entities_count != initial_processed_count:
        return True
    
    # 현재 엔티티들의 위치를 확인
    current_entity_states = {}
    for entity in active_entities_registry:
        # entity가 문자열인지 객체인지 확인
        if hasattr(entity, 'id') and hasattr(entity, 'current_block_id'):
            current_entity_states[entity.id] = entity.current_block_id
        elif isinstance(entity, str):
            # entity가 문자열이면 ID로 간주하고 레지스트리에서 실제 객체 찾기
            continue
        else:
            print(f"[WARNING] 알 수 없는 엔티티 타입: {type(entity)}, 값: {entity}")
            continue
    
    # 엔티티 수가 변경되었으면 움직임이 있었음
    if len(current_entity_states) != len(initial_entity_states):
        return True
    
    # 각 엔티티의 위치가 변경되었는지 확인
    for entity_id, current_block_id in current_entity_states.items():
        if entity_id not in initial_entity_states:
            return True  # 새로운 엔티티 발견
        if initial_entity_states[entity_id] != current_block_id:
            return True  # 엔티티 위치 변경
    
    # 사라진 엔티티가 있는지 확인
    for entity_id in initial_entity_states:
        if entity_id not in current_entity_states:
            return True  # 엔티티가 사라짐
    
    return False

def get_latest_movement_description() -> str:
    """최근 로그에서 엔티티 움직임 관련 설명을 추출합니다."""
    from . import state_manager
    
    if not state_manager.sim_log:
        return "시뮬레이션이 시작되지 않았습니다."
    
    # 최근 로그 항목들을 역순으로 확인
    for log_entry in reversed(state_manager.sim_log[-10:]):  # 최근 10개 항목만 확인
        event_description = log_entry.get('event', log_entry.get('description', ''))
        
        # 엔티티 관련 주요 이벤트 키워드 확인
        keywords = [
            'generated', 'routed', 'moved', 'processed', 'delayed', 
            'signal', 'wait', 'connector', 'block', 'entity'
        ]
        
        if event_description and any(keyword in event_description.lower() for keyword in keywords):
            return event_description
    
    # 엔티티 관련 이벤트가 없으면 최신 로그 반환
    if state_manager.sim_log:
        latest_log = state_manager.sim_log[-1]
        event_description = latest_log.get('event', latest_log.get('description', ''))
        if event_description:
            return event_description
    
    # 현재 시뮬레이션 상태에 따른 기본 설명
    from .entity import get_active_entity_states
    
    active_entities = get_active_entity_states()
    if active_entities:
        if len(active_entities) == 1:
            entity = active_entities[0]
            return f"엔티티 {entity.id}가 블록 {entity.current_block_id}에서 대기 중"
        else:
            return f"{len(active_entities)}개 엔티티가 활성 상태"
    
    return "시뮬레이션 진행 중" 