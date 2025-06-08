"""
디버그 매니저 - 브레이크포인트 관리 및 실행 제어
"""
import simpy
import logging
from typing import Dict, Set, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DebugState:
    """디버그 상태 정보"""
    is_debugging: bool = False
    is_paused: bool = False
    current_break: Optional[Tuple[str, int]] = None  # (block_id, line_number)
    step_mode: bool = False

class DebugManager:
    """브레이크포인트 관리 및 디버그 실행 제어"""
    
    def __init__(self):
        self.breakpoints: Dict[str, Set[int]] = {}  # {block_id: set(line_numbers)}
        self.debug_state = DebugState()
        self.continue_event: Optional[simpy.Event] = None
        self.waiting_for_continue = False  # continue 대기 플래그
        self.execution_context_stack = []  # 조건부 실행 컨텍스트 추적
        
    def set_breakpoint(self, block_id: str, line_number: int) -> None:
        """브레이크포인트 설정"""
        if block_id not in self.breakpoints:
            self.breakpoints[block_id] = set()
        self.breakpoints[block_id].add(line_number)
        # Breakpoint added
        
    def clear_breakpoint(self, block_id: str, line_number: int) -> None:
        """브레이크포인트 해제"""
        if block_id in self.breakpoints:
            self.breakpoints[block_id].discard(line_number)
            if not self.breakpoints[block_id]:
                del self.breakpoints[block_id]
        # Breakpoint removed
        
    def clear_all_breakpoints(self, block_id: Optional[str] = None) -> None:
        """모든 브레이크포인트 제거"""
        if block_id:
            if block_id in self.breakpoints:
                del self.breakpoints[block_id]
                # All breakpoints cleared for block
        else:
            self.breakpoints.clear()
            # All breakpoints cleared
            
    def get_breakpoints(self, block_id: Optional[str] = None) -> Dict[str, Set[int]]:
        """브레이크포인트 목록 조회"""
        if block_id:
            return {block_id: self.breakpoints.get(block_id, set())}
        return self.breakpoints.copy()
        
    def start_debugging(self) -> None:
        """디버깅 모드 시작"""
        self.debug_state.is_debugging = True
        # Debug mode started
        
    def stop_debugging(self) -> None:
        """디버깅 모드 종료"""
        self.debug_state.is_debugging = False
        self.debug_state.is_paused = False
        self.debug_state.current_break = None
        if self.continue_event:
            self.continue_event.succeed()
        # Debug mode stopped
        
    def push_execution_context(self, context_type: str, condition_met: bool) -> None:
        """실행 컨텍스트 추가 (조건부 실행 추적용)"""
        self.execution_context_stack.append((context_type, condition_met))
        
    def pop_execution_context(self) -> None:
        """실행 컨텍스트 제거"""
        if self.execution_context_stack:
            self.execution_context_stack.pop()
            
    def is_in_false_condition(self) -> bool:
        """현재 false 조건 내부인지 확인"""
        for context_type, condition_met in self.execution_context_stack:
            if context_type == 'if' and not condition_met:
                return True
        return False
        
    def check_breakpoint(self, block_id: str, line_number: int, env: simpy.Environment):
        """브레이크포인트 체크 및 실행 중단"""
        # Checking breakpoint
        
        # 디버깅 모드가 아니면 즉시 반환
        if not self.debug_state.is_debugging:
            # 브레이크포인트가 설정되어 있으면 자동으로 디버깅 모드 시작
            if self.breakpoints:
                # Auto-starting debug mode
                self.start_debugging()
            else:
                yield env.timeout(0)
                return
            
        # false 조건 내부면 브레이크포인트 무시
        if self.is_in_false_condition():
            # Inside false condition, skipping breakpoint check
            yield env.timeout(0)
            return
            
        # 브레이크포인트 확인
        if block_id in self.breakpoints and line_number in self.breakpoints[block_id]:
            # Breakpoint hit
            
            # 디버그 상태 업데이트
            self.debug_state.is_paused = True
            self.debug_state.current_break = (block_id, line_number)
            
            # 계속 실행 플래그 설정
            self.waiting_for_continue = True
            self.just_resumed = False  # 방금 재개되었는지 확인하는 플래그
            # Waiting at breakpoint
            
            # continue 신호를 기다리면서 시간은 진행하지 않음
            while self.waiting_for_continue:
                yield env.timeout(0)  # 시간 진행 없이 제어를 반환
                # 재개 신호가 있으면 플래그 설정
                if not self.waiting_for_continue:
                    self.just_resumed = True
            
            # Resuming execution
            
            # 재개 후 상태 정리
            self.debug_state.is_paused = False
            if not self.debug_state.step_mode:
                self.debug_state.current_break = None
        else:
            # 스텝 모드에서는 모든 라인에서 멈춤
            if self.debug_state.step_mode:
                # Step mode pause
                
                self.debug_state.is_paused = True
                self.debug_state.current_break = (block_id, line_number)
                
                # 스텝 모드에서도 시간 진행 없이 대기
                self.waiting_for_continue = True
                while self.waiting_for_continue:
                    yield env.timeout(0)
                
                self.debug_state.is_paused = False
                self.debug_state.step_mode = False  # 스텝 모드는 한 번만
            else:
                yield env.timeout(0)
                
    def continue_execution(self) -> bool:
        """실행 계속"""
        # Continue execution called
        if self.debug_state.is_paused:
            self.waiting_for_continue = False
            self.debug_state.step_mode = False
            self.debug_state.is_paused = False  # 일시정지 상태 해제
            self.debug_state.current_break = None  # 현재 브레이크포인트 정보 제거
            # Execution continued
            return True
        # Continue conditions not met
        return False
        
    def step_execution(self) -> bool:
        """한 스텝 실행"""
        if self.debug_state.is_paused and hasattr(self, 'waiting_for_continue'):
            self.debug_state.step_mode = True
            self.waiting_for_continue = False
            # Step execution
            return True
        return False
        
    def get_debug_info(self) -> Dict:
        """현재 디버그 정보 반환"""
        info = {
            "is_debugging": self.debug_state.is_debugging,
            "is_paused": self.debug_state.is_paused,
            "current_break": {
                "block_id": self.debug_state.current_break[0],
                "line": self.debug_state.current_break[1]
            } if self.debug_state.current_break else None,
            "breakpoints": {
                block_id: list(lines) 
                for block_id, lines in self.breakpoints.items()
            },
            "execution_context": [
                {"type": ctx[0], "condition_met": ctx[1]} 
                for ctx in self.execution_context_stack
            ]
        }
        # Returning debug info
        return info
        
    def reset(self) -> None:
        """디버그 상태 초기화"""
        self.debug_state = DebugState()
        self.continue_event = None
        self.execution_context_stack.clear()
        # 브레이크포인트는 유지
        # Debug state reset