"""
단순화된 신호 관리자
"""
from typing import Dict, Any

class SimpleSignalManager:
    """단순화된 신호 관리자"""
    
    def __init__(self):
        self.signals: Dict[str, bool] = {}
        self.initial_signals: Dict[str, bool] = {}
    
    def initialize_signals(self, signals: Dict[str, bool]):
        """신호 초기화"""
        self.initial_signals = signals.copy()
        self.signals = signals.copy()
    
    def set_signal(self, signal_name: str, value: bool):
        """신호 값 설정"""
        self.signals[signal_name] = value
    
    def get_signal(self, signal_name: str, default: bool = False) -> bool:
        """신호 값 가져오기"""
        return self.signals.get(signal_name, default)
    
    def get_all_signals(self) -> Dict[str, bool]:
        """모든 신호 상태 반환"""
        return self.signals.copy()
    
    def reset(self):
        """신호 상태를 초기값으로 리셋"""
        self.signals = self.initial_signals.copy()
    
    def add_signal(self, signal_name: str, initial_value: bool = False):
        """새로운 신호 추가"""
        if signal_name not in self.signals:
            self.signals[signal_name] = initial_value
            self.initial_signals[signal_name] = initial_value