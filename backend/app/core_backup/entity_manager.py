"""
엔티티 관리 모듈
엔티티의 생성, 삭제, 상태 관리를 담당합니다.
"""
import simpy
from typing import Dict, List, Optional, Set
from ..entity import Entity, entity_pool, active_entities_registry
from .constants import EntityState, FormatConfig, TimeoutConfig, MONITORING_MODE
import logging

logger = logging.getLogger(__name__)

class EntityManager:
    """엔티티 생성과 관리를 담당하는 클래스"""
    
    def __init__(self):
        self.entity_counts: Dict[str, int] = {}
        self.block_entity_counts: Dict[str, int] = {}
        
    def create_entity(self, env: simpy.Environment, block_id: str, entity_number: int) -> Entity:
        """새 엔티티를 생성합니다."""
        entity_id = FormatConfig.ENTITY_ID_FORMAT.format(
            block_id=block_id,
            count=entity_number
        )
        # EntityPool.get_entity는 env, entity_id, name을 받음
        entity = entity_pool.get_entity(env, entity_id, "Product")
        return entity
        
    def update_entity_location(self, entity: Entity, location_id: str, location_name: str):
        """엔티티의 위치를 업데이트합니다."""
        old_location = entity.current_block_name
        entity.update_location(location_id, location_name)
        
        # Transit 관련 속성 제거 (목적지 도착)
        if hasattr(entity, 'transit_to_block_id'):
            delattr(entity, 'transit_to_block_id')
        if hasattr(entity, 'transit_to_block'):
            delattr(entity, 'transit_to_block')
        
        # 모니터링 로깅 (env가 있는 경우에만)
        if MONITORING_MODE and old_location != location_name and hasattr(entity, 'env') and entity.env:
            from .monitoring import simulation_monitor
            simulation_monitor.log_entity_movement(entity.id, old_location, location_name, entity.env.now)
        
    def set_entity_transit(self, entity: Entity, from_block: str, to_block: str):
        """엔티티를 transit 상태로 설정합니다."""
        transit_display = FormatConfig.TRANSIT_DISPLAY_FORMAT.format(
            from_block=from_block,
            to_block=to_block
        )
        entity.update_location(EntityState.TRANSIT, transit_display)
        
        # Transit 대상 블록 정보 저장 (용량 체크를 위해)
        entity.transit_to_block = to_block
        
    def process_entity(self, entity: Entity) -> None:
        """엔티티를 처리(제거)합니다."""
        # 모니터링 로깅
        if MONITORING_MODE and hasattr(entity, 'env') and entity.env:
            from .monitoring import simulation_monitor
            simulation_monitor.log_entity_processed(
                entity.id, 
                entity.current_block_name, 
                entity.env.now,
                # 처리된 엔티티 수는 block_processor에서 관리
                0  # 여기서는 개별 카운트만
            )
        entity_pool.return_entity(entity)
        
    def get_block_entity_count(self, block_id: str) -> int:
        """블록에 있는 엔티티 수를 반환합니다."""
        from ..entity import get_block_entity_count
        return get_block_entity_count(block_id)
        
    def get_active_entities(self) -> List[Dict]:
        """활성 엔티티들의 상태를 반환합니다."""
        from ..entity import get_active_entity_states
        return get_active_entity_states()
        
    def check_block_capacity(self, block_id: str, max_capacity: Optional[int]) -> bool:
        """블록의 수용량을 확인합니다. (Transit 상태 포함)"""
        if max_capacity is None:
            return True
        
        # 블록에 있는 엔티티 수
        current_count = self.get_block_entity_count(block_id)
        
        # Transit 상태로 해당 블록으로 향하는 엔티티 수도 포함
        from ..entity import active_entities_registry
        transit_count = 0
        for entity in active_entities_registry.values():
            # transit_to_block_id가 있으면 그것을 사용
            if hasattr(entity, 'transit_to_block_id') and str(entity.transit_to_block_id) == str(block_id):
                transit_count += 1
                    
        total_count = current_count + transit_count
        return total_count < max_capacity