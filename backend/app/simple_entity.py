"""
단순화된 엔티티 클래스
"""
import uuid
from typing import Optional, Any

class SimpleEntity:
    """단순화된 엔티티 클래스"""
    
    def __init__(self, entity_id: Optional[str] = None):
        self.id = entity_id or str(uuid.uuid4())[:8]
        self.current_block = None
        self.current_connector = None
        self.target_block = None
        self.target_connector = None
        self.movement_requested = False
        self.created_at = None
        self.processed_at = None
        self.properties = {}  # 추가 속성 저장용
    
    def reset_movement(self):
        """이동 관련 상태 초기화"""
        self.target_block = None
        self.target_connector = None
        self.movement_requested = False
    
    def set_location(self, block_name: str, connector_name: str = None):
        """현재 위치 설정"""
        self.current_block = block_name
        self.current_connector = connector_name
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """속성 값 가져오기"""
        return self.properties.get(key, default)
    
    def set_property(self, key: str, value: Any):
        """속성 값 설정"""
        self.properties[key] = value
    
    def __str__(self):
        return f"Entity({self.id}@{self.current_block})"
    
    def __repr__(self):
        return self.__str__()