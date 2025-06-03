"""
시뮬레이션 모니터링 모듈
시뮬레이션의 전체 상태를 추적하고 로깅합니다.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SimulationMonitor:
    """시뮬레이션 상태를 모니터링하는 클래스"""
    
    def __init__(self):
        self.step_count = 0
        self.last_event_time = 0.0
        
    def log_simulation_state(self, 
                           step_num: int,
                           sim_time: float,
                           event_queue_size: int,
                           active_entities: List[Any],
                           processed_count: int,
                           signals: Dict[str, Any],
                           current_event: Optional[str] = None,
                           actions_in_progress: Optional[List[Dict]] = None) -> None:
        """시뮬레이션의 전체 상태를 로깅합니다."""
        
        self.step_count = step_num
        
        # 기본 상태 정보
        logger.info(f"{'=' * 80}")
        logger.info(f"[MONITOR] 스텝 #{step_num} - 시간: {sim_time:.2f}s")
        logger.info(f"[MONITOR] 이벤트 큐: {event_queue_size}개, 처리된 엔티티: {processed_count}개")
        
        # 현재 이벤트
        if current_event:
            logger.info(f"[MONITOR] 현재 이벤트: {current_event}")
        
        # 엔티티 상태
        if active_entities:
            logger.info(f"[MONITOR] 활성 엔티티 ({len(active_entities)}개):")
            entity_by_location = {}
            transit_entities = []
            
            for entity in active_entities:
                # Check if entity is in transit by looking at current_block_id
                if entity.current_block_id == 'transit':
                    transit_entities.append(entity)
                else:
                    loc = entity.current_block_name or entity.current_block_id
                    if loc not in entity_by_location:
                        entity_by_location[loc] = []
                    entity_by_location[loc].append(entity.id)
            
            # 블록별 엔티티
            for location, entities in entity_by_location.items():
                logger.info(f"  - {location}: {', '.join(entities)}")
            
            # 이동 중인 엔티티
            if transit_entities:
                logger.info(f"  - 이동 중:")
                for entity in transit_entities:
                    # For transit entities, current_block_name contains the transit display like "블록1→블록2"
                    transit_info = entity.current_block_name or "Unknown→Unknown"
                    logger.info(f"    * {entity.id}: {transit_info}")
        else:
            logger.info(f"[MONITOR] 활성 엔티티 없음")
        
        # 신호 상태
        if signals:
            logger.info(f"[MONITOR] 글로벌 신호:")
            for signal_name, signal_value in signals.items():
                logger.info(f"  - {signal_name}: {signal_value}")
        
        # 진행 중인 액션
        if actions_in_progress:
            logger.info(f"[MONITOR] 진행 중인 액션:")
            for action in actions_in_progress:
                logger.info(f"  - {action.get('entity_id', 'Unknown')}: "
                          f"{action.get('action_name', 'Unknown')} "
                          f"({action.get('action_type', 'Unknown')})")
        
        # 시간 진행 확인
        if sim_time == self.last_event_time:
            logger.warning(f"[MONITOR] ⚠️  시간이 진행되지 않음 (동일 시간에 여러 이벤트)")
        self.last_event_time = sim_time
        
        logger.info(f"{'=' * 80}")
        
    def log_entity_action(self, entity_id: str, action_name: str, 
                         action_type: str, block_name: str, 
                         start_time: float, details: Optional[str] = None) -> None:
        """엔티티의 액션 실행을 로깅합니다."""
        log_msg = f"[ACTION] {start_time:.2f}s: [{block_name}] Entity {entity_id} - {action_name} ({action_type})"
        if details:
            log_msg += f" - {details}"
        logger.info(log_msg)
        
    def log_entity_movement(self, entity_id: str, from_block: str, 
                           to_block: str, time: float) -> None:
        """엔티티의 이동을 로깅합니다."""
        logger.info(f"[MOVEMENT] {time:.2f}s: Entity {entity_id} moved from {from_block} to {to_block}")
        
    def log_signal_change(self, signal_name: str, old_value: Any, 
                         new_value: Any, time: float) -> None:
        """신호 변경을 로깅합니다."""
        logger.info(f"[SIGNAL] {time:.2f}s: Signal '{signal_name}' changed from {old_value} to {new_value}")
        
    def log_entity_processed(self, entity_id: str, block_name: str, 
                            time: float, total_processed: int) -> None:
        """엔티티 처리 완료를 로깅합니다."""
        logger.info(f"[PROCESSED] {time:.2f}s: Entity {entity_id} processed at {block_name} "
                   f"(Total: {total_processed})")
        
    def log_warning(self, message: str, time: float) -> None:
        """경고 메시지를 로깅합니다."""
        logger.warning(f"[WARNING] {time:.2f}s: {message}")
        
    def log_error(self, message: str, time: float) -> None:
        """에러 메시지를 로깅합니다."""
        logger.error(f"[ERROR] {time:.2f}s: {message}")

# 글로벌 모니터 인스턴스
simulation_monitor = SimulationMonitor()