"""
신호 관리 모듈
글로벌 신호의 설정, 확인, 대기 기능을 관리합니다.
"""
import simpy
from typing import Dict, Optional, Any
import logging
from .constants import MONITORING_MODE

logger = logging.getLogger(__name__)

class SignalManager:
    """신호 관리를 담당하는 클래스"""
    
    def __init__(self):
        self.signals: Dict[str, Any] = {}
        self.signal_events: Dict[str, simpy.Event] = {}
        self.transaction_manager = None  # 트랜잭션 매니저는 나중에 설정
        
    def set_signal(self, signal_name: str, value: Any, env: simpy.Environment) -> None:
        """신호 값을 설정합니다."""
        old_value = self.signals.get(signal_name)
        self.signals[signal_name] = value
        
        # 모니터링 로깅
        if MONITORING_MODE and old_value != value:
            from .monitoring import simulation_monitor
            simulation_monitor.log_signal_change(signal_name, old_value, value, env.now)
        
        # 신호 변경 이벤트 트리거
        event_key = f"{signal_name}_{value}"
        if event_key in self.signal_events:
            event = self.signal_events[event_key]
            if not event.triggered:
                event.succeed()
            self.signal_events[event_key] = env.event()
            
        logger.debug(f"Signal '{signal_name}' changed: {old_value} → {value}")
        
    def get_signal(self, signal_name: str, default: Any = None) -> Any:
        """신호 값을 가져옵니다."""
        return self.signals.get(signal_name, default)
        
    def get_all_signals(self) -> Dict[str, Any]:
        """모든 신호를 반환합니다."""
        return self.signals.copy()
        
    def wait_for_signal(self, signal_name: str, expected_value: Any, env: simpy.Environment):
        """특정 신호가 원하는 값이 될 때까지 대기합니다."""
        # 이미 원하는 값이면 즉시 반환
        if self.get_signal(signal_name) == expected_value:
            yield env.timeout(0)
            return
            
        # 이벤트 생성 및 대기
        event_key = f"{signal_name}_{expected_value}"
        if event_key not in self.signal_events:
            self.signal_events[event_key] = env.event()
            
        yield self.signal_events[event_key]
        
    def initialize_signals(self, initial_signals: Dict[str, Any], env: simpy.Environment) -> None:
        """초기 신호값을 설정합니다."""
        for signal_name, value in initial_signals.items():
            self.set_signal(signal_name, value, env)
            
    def reset(self):
        """신호 관리자를 초기화합니다."""
        self.signals.clear()
        self.signal_events.clear()
        if self.transaction_manager:
            self.transaction_manager.reset()
            
    def set_transaction_manager(self, transaction_manager):
        """트랜잭션 매니저를 설정합니다."""
        self.transaction_manager = transaction_manager