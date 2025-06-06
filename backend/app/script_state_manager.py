"""
스크립트 실행 상태 관리자
각 블록의 스크립트 실행 상태를 추적하고 관리합니다.
"""
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ScriptExecutionState:
    """스크립트 실행 상태를 나타내는 데이터 클래스"""
    current_line: int = 0  # 현재 실행 중인 라인
    is_executing: bool = False  # 실행 중인지 여부
    entity_id: Optional[str] = None  # 실행 중인 엔티티 ID
    entity_ref: Optional[Any] = None  # 실행 중인 엔티티 참조
    waiting_for: Optional[str] = None  # 대기 중인 조건
    context: Dict[str, Any] = field(default_factory=dict)  # 추가 컨텍스트 정보

class ScriptStateManager:
    """블록별 스크립트 실행 상태를 관리하는 클래스"""
    
    def __init__(self):
        # 블록 ID별 실행 상태 저장
        self.block_states: Dict[str, ScriptExecutionState] = {}
        logger.info("ScriptStateManager initialized")
    
    def get_state(self, block_id: str) -> ScriptExecutionState:
        """블록의 현재 실행 상태를 가져옵니다."""
        if block_id not in self.block_states:
            self.block_states[block_id] = ScriptExecutionState()
            logger.debug(f"Created new script state for block {block_id}")
        return self.block_states[block_id]
    
    def update_state(self, block_id: str, **kwargs):
        """블록의 실행 상태를 업데이트합니다."""
        state = self.get_state(block_id)
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
                logger.debug(f"Updated block {block_id} state: {key}={value}")
    
    def start_execution(self, block_id: str, entity_id: Optional[str] = None, entity_ref: Optional[Any] = None):
        """블록의 스크립트 실행을 시작합니다."""
        state = self.get_state(block_id)
        state.is_executing = True
        state.entity_id = entity_id
        state.entity_ref = entity_ref
        if entity_id:
            logger.info(f"Block {block_id} started script execution with entity {entity_id}")
        else:
            logger.info(f"Block {block_id} started script execution without entity (force execution)")
    
    def set_current_line(self, block_id: str, line: int):
        """현재 실행 중인 라인을 설정합니다."""
        state = self.get_state(block_id)
        state.current_line = line
        logger.debug(f"Block {block_id} current line: {line}")
    
    def set_waiting(self, block_id: str, condition: str):
        """대기 상태를 설정합니다."""
        state = self.get_state(block_id)
        state.waiting_for = condition
        logger.debug(f"Block {block_id} waiting for: {condition}")
    
    def clear_waiting(self, block_id: str):
        """대기 상태를 해제합니다."""
        state = self.get_state(block_id)
        state.waiting_for = None
        logger.debug(f"Block {block_id} waiting cleared")
    
    def end_execution(self, block_id: str):
        """블록의 스크립트 실행을 종료합니다."""
        state = self.get_state(block_id)
        state.is_executing = False
        state.current_line = 0
        state.entity_id = None
        state.entity_ref = None
        state.waiting_for = None
        logger.info(f"Block {block_id} ended script execution")
    
    def reset_block(self, block_id: str):
        """블록의 실행 상태를 초기화합니다."""
        if block_id in self.block_states:
            del self.block_states[block_id]
            logger.info(f"Reset script state for block {block_id}")
    
    def reset_all(self):
        """모든 블록의 실행 상태를 초기화합니다."""
        self.block_states.clear()
        logger.info("Reset all script states")
    
    def get_all_states(self) -> Dict[str, dict]:
        """모든 블록의 실행 상태를 딕셔너리로 반환합니다."""
        result = {}
        for block_id, state in self.block_states.items():
            result[block_id] = {
                'current_line': state.current_line,
                'is_executing': state.is_executing,
                'entity_id': state.entity_id,
                'waiting_for': state.waiting_for
            }
        return result

# 전역 인스턴스
script_state_manager = ScriptStateManager()