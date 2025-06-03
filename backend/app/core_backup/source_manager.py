"""
소스 블록 관리 모듈
엔티티를 생성하는 소스 블록들을 관리합니다.
"""
import simpy
from typing import Dict, Set, Optional, Any
from .constants import LimitConfig, DEBUG_MODE
import logging

logger = logging.getLogger(__name__)

class SourceManager:
    """소스 블록 관리를 담당하는 클래스"""
    
    def __init__(self):
        self.source_blocks: Set[str] = set()
        self.request_events: Dict[str, simpy.Event] = {}
        self.generated_counts: Dict[str, int] = {}
        self.generation_limits: Dict[str, float] = {}
        self.generation_conditions: Dict[str, Dict[str, Any]] = {}
        
    def register_source_block(self, block_id: str, env: simpy.Environment, 
                            limit: float = LimitConfig.INFINITE_GENERATION,
                            condition: Optional[Dict[str, Any]] = None):
        """소스 블록을 등록합니다."""
        block_id_str = str(block_id)
        self.source_blocks.add(block_id_str)
        self.request_events[block_id_str] = env.event()
        self.generated_counts[block_id_str] = 0
        self.generation_limits[block_id_str] = limit
        
        if condition:
            self.generation_conditions[block_id_str] = condition
            
        logger.debug(f"Source block {block_id} registered with limit {limit}")
        
    def is_source_block(self, block_id: str) -> bool:
        """소스 블록인지 확인합니다."""
        return str(block_id) in self.source_blocks
        
    def get_generated_count(self, block_id: str) -> int:
        """생성된 엔티티 수를 반환합니다."""
        return self.generated_counts.get(str(block_id), 0)
        
    def increment_generated_count(self, block_id: str) -> int:
        """생성 카운트를 증가시키고 새 카운트를 반환합니다."""
        block_id_str = str(block_id)
        self.generated_counts[block_id_str] = self.generated_counts.get(block_id_str, 0) + 1
        return self.generated_counts[block_id_str]
        
    def can_generate(self, block_id: str) -> bool:
        """더 생성할 수 있는지 확인합니다."""
        block_id_str = str(block_id)
        count = self.generated_counts.get(block_id_str, 0)
        limit = self.generation_limits.get(block_id_str, 0)
        return count < limit
        
    def get_request_event(self, block_id: str) -> Optional[simpy.Event]:
        """요청 이벤트를 가져옵니다."""
        return self.request_events.get(str(block_id))
        
    def create_request_event(self, block_id: str, env: simpy.Environment):
        """새로운 요청 이벤트를 생성합니다."""
        block_id_str = str(block_id)
        self.request_events[block_id_str] = env.event()
        if DEBUG_MODE:
            logger.debug(f"Created new request event for source block {block_id}")
        
    def trigger_request_event(self, block_id: str, env: simpy.Environment):
        """요청 이벤트를 트리거합니다."""
        block_id_str = str(block_id)
        if block_id_str in self.request_events:
            event = self.request_events[block_id_str]
            if not event.triggered:
                event.succeed()
                if DEBUG_MODE:
                    logger.debug(f"Triggered request event for source block {block_id}")
            # 새로운 이벤트는 다음 요청 시에 생성
            
    def get_generation_condition(self, block_id: str) -> Optional[Dict[str, Any]]:
        """생성 조건을 가져옵니다."""
        return self.generation_conditions.get(str(block_id))
        
    def trigger_initial_events(self, env: simpy.Environment):
        """초기 이벤트들을 트리거합니다."""
        logger.info(f"Triggering initial events for {len(self.source_blocks)} source blocks")
        for block_id in self.source_blocks:
            logger.info(f"Triggering initial event for source block: {block_id}")
            self.trigger_request_event(block_id, env)
            
    def reset(self):
        """소스 관리자를 초기화합니다."""
        self.source_blocks.clear()
        self.request_events.clear()
        self.generated_counts.clear()
        self.generation_limits.clear()
        self.generation_conditions.clear()