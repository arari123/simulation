"""
단순화된 엔티티 클래스
"""
import uuid
from typing import Optional, Any, Set

class SimpleEntity:
    """단순화된 엔티티 클래스"""
    
    def __init__(self, entity_id: Optional[str] = None):
        self.id = entity_id or str(uuid.uuid4())[:8]
        self.current_block = None
        self.current_connector = None
        self.target_block = None
        self.target_connector = None
        self.movement_requested = False
        self.movement_completed = False  # 이동 완료 플래그
        self.movement_failed = False  # 이동 실패 플래그 (용량 초과 등)
        self.created_at = None
        self.processed_at = None
        self.properties = {}  # 추가 속성 저장용
        
        # 엔티티 속성 추가
        self.state: str = "normal"  # "normal" | "transit"
        self.custom_attributes: Set[str] = set()  # 커스텀 속성들 (예: {"flip", "1c"})
        self.color: Optional[str] = None  # "gray", "blue", "green", "red", "black", "white"
        
        # 스크립트 처리 추적
        self.processed_by_blocks: Set[str] = set()  # 이미 스크립트를 실행한 블록들의 ID
    
    def reset_movement(self):
        """이동 관련 상태 초기화"""
        self.target_block = None
        self.target_connector = None
        self.movement_requested = False
        self.movement_completed = False
        self.movement_failed = False
    
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
    
    def to_dict(self) -> dict:
        """엔티티를 딕셔너리로 변환 (직렬화)"""
        return {
            'id': self.id,
            'current_block': self.current_block,
            'current_connector': self.current_connector,
            'state': self.state,
            'custom_attributes': list(self.custom_attributes),  # set을 list로 변환
            'color': self.color,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SimpleEntity':
        """딕셔너리에서 엔티티 생성 (역직렬화)"""
        entity = cls(data.get('id'))
        entity.current_block = data.get('current_block')
        entity.current_connector = data.get('current_connector')
        entity.state = data.get('state', 'normal')
        entity.custom_attributes = set(data.get('custom_attributes', []))
        entity.color = data.get('color')
        entity.properties = data.get('properties', {})
        return entity
    
    def __str__(self):
        return f"Entity({self.id}@{self.current_block})"
    
    def __repr__(self):
        return self.__str__()