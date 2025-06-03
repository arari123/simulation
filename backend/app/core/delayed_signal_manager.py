"""
지연된 신호 관리 모듈
엔티티가 목적지에 도착한 후에 신호를 복원하는 기능을 제공합니다.
"""
import simpy
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DelayedSignalManager:
    """지연된 신호 변경을 관리하는 클래스"""
    
    def __init__(self, signal_manager):
        self.signal_manager = signal_manager
        self.env: Optional[simpy.Environment] = None
        
    def initialize(self, env: simpy.Environment):
        """환경 초기화"""
        self.env = env
        
    def schedule_delayed_signal_updates(self, env: simpy.Environment, delay: float, 
                                      signal_updates: List[Tuple[str, Any]], source: str):
        """지정된 지연 시간 후에 신호 업데이트를 예약합니다."""
        if delay > 0:
            env.process(self._delayed_signal_update_process(env, delay, signal_updates, source))
        else:
            # 지연 없이 즉시 실행
            for signal_name, value in signal_updates:
                self.signal_manager.set_signal(signal_name, value, env)
                
    def _delayed_signal_update_process(self, env: simpy.Environment, delay: float, 
                                     signal_updates: List[Tuple[str, Any]], source: str):
        """지연된 신호 업데이트 프로세스"""
        yield env.timeout(delay)
        
        logger.info(f"{env.now}: Executing {len(signal_updates)} delayed signal updates from {source}")
        
        for signal_name, value in signal_updates:
            current_value = self.signal_manager.get_signal(signal_name, None)
            if current_value != value:
                self.signal_manager.set_signal(signal_name, value, env)
                logger.info(f"{env.now}: [DELAYED] Signal '{signal_name}' changed from {current_value} to {value}")
                
    def reset(self):
        """지연 신호 관리자 초기화"""
        self.env = None