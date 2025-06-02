from typing import Dict, Optional, List
from .models import EntityState

# 전역 엔티티 레지스트리 (순환 import 방지를 위해 여기서 관리)
active_entities_registry: Dict[str, 'Entity'] = {}

class Entity:
    """시뮬레이션 엔티티 클래스"""
    
    def __init__(self, entity_id: str, current_block_id: str, current_block_name: str, creation_time: float):
        self.id = entity_id
        self.current_block_id = current_block_id
        self.current_block_name = current_block_name
        self.creation_time = creation_time
        
        # 엔티티 레지스트리에 등록
        active_entities_registry[entity_id] = self
        
        # 블록별 엔티티 수 업데이트
        self._update_block_count(current_block_id, 1)
    
    def _update_block_count(self, block_id: str, delta: int):
        """블록별 엔티티 수 업데이트"""
        from .state_manager import block_entity_counts
        if block_id not in block_entity_counts:
            block_entity_counts[block_id] = 0
        block_entity_counts[block_id] += delta
        if block_entity_counts[block_id] <= 0:
            block_entity_counts[block_id] = 0
    
    def update_location(self, new_block_id: str, new_block_name: str):
        """엔티티 위치 업데이트"""
        old_block_id = self.current_block_id
        
        # 이전 블록에서 엔티티 수 감소
        self._update_block_count(old_block_id, -1)
        
        # 새 블록으로 이동
        self.current_block_id = new_block_id
        self.current_block_name = new_block_name
        
        # 새 블록에서 엔티티 수 증가
        self._update_block_count(new_block_id, 1)
    
    def remove(self):
        """엔티티 제거"""
        # 현재 블록에서 엔티티 수 감소
        self._update_block_count(self.current_block_id, -1)
        
        # 레지스트리에서 제거
        if self.id in active_entities_registry:
            del active_entities_registry[self.id]
    
    def to_state(self) -> EntityState:
        """EntityState 객체로 변환"""
        return EntityState(
            id=self.id,
            current_block_id=self.current_block_id,
            current_block_name=self.current_block_name
        )

def get_block_entity_count(block_id: str) -> int:
    """특정 블록의 엔티티 수 반환"""
    from .state_manager import block_entity_counts
    return block_entity_counts.get(block_id, 0)

def get_active_entity_states() -> List[EntityState]:
    """현재 활성 엔티티 상태들을 반환"""
    return [entity.to_state() for entity in active_entities_registry.values()]

# 임시 호환성을 위한 EntityPool 클래스 (기존 시뮬레이션 엔진과의 호환성)
class EntityPool:
    def __init__(self):
        pass
    
    def get_entity(self, env, entity_id: str, name: str = "Product") -> 'Entity':
        """새 엔티티 생성"""
        return Entity(entity_id, "1", name, env.now)  # 기본값으로 블록 ID "1" 사용
    
    def return_entity(self, entity: 'Entity'):
        """엔티티 제거"""
        entity.remove()

# 전역 엔티티 풀 인스턴스
entity_pool = EntityPool() 