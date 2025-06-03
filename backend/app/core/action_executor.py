"""
액션 실행 모듈
블록과 커넥터의 액션들을 실행합니다.
"""
import simpy
from typing import Dict, List, Optional, Any, Generator
from .constants import ActionType, TimeoutConfig, EntityState, MONITORING_MODE
from .entity_manager import EntityManager
from .signal_manager import SignalManager
from .pipe_manager import PipeManager
from ..utils import parse_delay_value
from .script_executor import ScriptExecutor
import logging

logger = logging.getLogger(__name__)

class ActionExecutor:
    """액션 실행을 담당하는 클래스"""
    
    def __init__(self, entity_manager: EntityManager, signal_manager: SignalManager, 
                 pipe_manager: PipeManager):
        self.entity_manager = entity_manager
        self.signal_manager = signal_manager
        self.pipe_manager = pipe_manager
        self.sim_log = []
        self.script_executor = ScriptExecutor(signal_manager, pipe_manager, entity_manager)
        
    def execute_action(self, env: simpy.Environment, action: Any, entity: Any, 
                      context: Dict[str, Any]) -> Generator:
        """단일 액션을 실행합니다."""
        action_type = action.type
        params = action.parameters
        
        # 모니터링 로깅 - 액션 시작 (entity가 None이 아닐 때만)
        if MONITORING_MODE and entity is not None:
            from .monitoring import simulation_monitor
            block_name = context.get('block_name', 'Unknown')
            simulation_monitor.log_entity_action(
                entity.id, action.name, action_type, block_name, env.now
            )
        
        if action_type == ActionType.DELAY:
            yield from self._execute_delay(env, params)
            
        elif action_type == ActionType.SIGNAL_WAIT:
            yield from self._execute_signal_wait(env, params)
            
        elif action_type == ActionType.SIGNAL_UPDATE:
            self._execute_signal_update(env, params)
            
        elif action_type == ActionType.ROUTE_TO_CONNECTOR:
            if entity is None:
                logger.error("route_to_connector action requires an entity but entity is None")
                return 'route_error'
            result = yield from self._execute_route_to_connector(env, params, entity, context)
            return result
            
        elif action_type == ActionType.CONDITIONAL_BRANCH:
            if entity is None:
                logger.error("conditional_branch action requires an entity but entity is None")
                return 'continue'
            result = yield from self._execute_conditional_branch(env, params, entity, context)
            return result
            
        elif action_type == ActionType.BLOCK_ENTRY:
            if entity is None:
                logger.error("block_entry action requires an entity but entity is None")
                return 'continue'
            yield from self._execute_block_entry(env, params, entity, context)
            
        elif action_type == ActionType.CUSTOM_SINK:
            if entity is None:
                logger.warning("custom_sink action executed without an entity")
                return 'continue'
            return 'processed'
            
        return 'continue'
        
    def _execute_delay(self, env: simpy.Environment, params: Dict[str, Any]) -> Generator:
        """딜레이 액션을 실행합니다."""
        duration = parse_delay_value(str(params.get("duration", 0)))
        if duration > 0:
            yield env.timeout(duration)
        else:
            yield env.timeout(TimeoutConfig.MINIMAL_DELAY)
            
    def _execute_signal_wait(self, env: simpy.Environment, params: Dict[str, Any]) -> Generator:
        """신호 대기 액션을 실행합니다."""
        signal_name = params.get("signal_name")
        expected_value = params.get("expected_value", True)
        
        if signal_name:
            # 현재 값 확인
            current_value = self.signal_manager.get_signal(signal_name, False)
            if current_value != expected_value:
                yield from self.signal_manager.wait_for_signal(signal_name, expected_value, env)
                
    def _execute_signal_update(self, env: simpy.Environment, params: Dict[str, Any]):
        """신호 업데이트 액션을 실행합니다."""
        signal_name = params.get("signal_name")
        value = params.get("value", False)
        
        if signal_name:
            self.signal_manager.set_signal(signal_name, value, env)
            
    def _execute_route_to_connector(self, env: simpy.Environment, params: Dict[str, Any], 
                                   entity: Any, context: Dict[str, Any]) -> Generator:
        """라우팅 액션을 실행합니다."""
        # 딜레이 처리
        delay = params.get("delay", "0")
        if delay and delay != "0":
            delay_time = parse_delay_value(str(delay))
            yield env.timeout(delay_time)
            
        # 라우팅 정보 가져오기 - 두 가지 방식 지원
        # 1. connector_id를 통한 방식 (블록 액션)
        # 2. target_block_id/target_connector_id를 통한 방식 (커넥터 액션)
        
        connector_id = params.get("connector_id")
        target_block_id = params.get("target_block_id")
        target_connector_id = params.get("target_connector_id")
        target_block_name = params.get("target_block_name", "")
        
        # 자기 자신의 커넥터로 이동하는 경우 특별 처리
        if connector_id and target_block_name == "self":
            # 블록에서 자신의 커넥터로 이동 - 커넥터 액션 실행 필요
            return 'route_to_self_connector'
        
        if connector_id:
            # connector_id를 통한 라우팅 (블록 액션에서 사용)
            out_pipes = context.get('out_pipes', {})
            if connector_id not in out_pipes:
                logger.error(f"route_to_connector: connector {connector_id} not found in out_pipes")
                return 'route_error'
                
            # out_pipes[connector_id]가 리스트인 경우 첫 번째 연결 사용
            pipe_info_data = out_pipes[connector_id]
            if isinstance(pipe_info_data, list):
                if len(pipe_info_data) == 0:
                    logger.error(f"route_to_connector: no connections for connector {connector_id}")
                    return 'route_error'
                pipe_info = pipe_info_data[0]  # 첫 번째 연결 사용
            else:
                # 구 형식 지원
                pipe_info = pipe_info_data
                
            target_block_id = pipe_info.get('block_id')
            target_connector_id = pipe_info.get('connector_name')
            target_block_name = pipe_info.get('block_name')
            pipe_id = pipe_info.get('pipe_id')
            from_connector_id = connector_id
        elif target_block_id and target_connector_id:
            # 직접 지정 방식 (커넥터 액션에서 사용)
            target_block_name = params.get("target_block_name", f"Block {target_block_id}")
            from_block_id = context.get('block_id')
            from_connector_id = context.get('connector_id')
            
            if not from_connector_id:
                logger.error(f"route_to_connector: from_connector_id not found in context")
                return 'route_error'
                
            pipe_id = self.pipe_manager.create_pipe_id(
                str(from_block_id), from_connector_id,
                str(target_block_id), target_connector_id
            )
        else:
            logger.error(f"route_to_connector: neither connector_id nor target_block_id/target_connector_id provided")
            return 'route_error'
        
        if not pipe_id:
            logger.error(f"route_to_connector: pipe_id not found")
            return 'route_error'
            
        # pipe_id는 이미 out_pipes에서 가져왔으므로 다시 생성할 필요 없음
        pipe = self.pipe_manager.get_pipe(pipe_id)
        if not pipe:
            logger.error(f"route_to_connector: Pipe {pipe_id} not found in pipe_manager")
            logger.error(f"Available pipes: {list(self.pipe_manager.pipes.keys())}")
            return 'route_error'
            
        # Transit 상태로 설정
        from_block_name = context.get('block_name', 'Unknown')
        self.entity_manager.set_entity_transit(entity, from_block_name, target_block_name)
        
        # 파이프에 넣기
        yield pipe.put(entity)
        
        # 로그
        self.sim_log.append({
            "time": env.now,
            "entity_id": entity.id,
            "event": f"Entity {entity.id} routed from {from_block_name} to {target_block_name}",
            "transit_from": from_block_name,
            "transit_to": target_block_name
        })
        
        return 'route_out'
        
    def _execute_conditional_branch(self, env: simpy.Environment, params: Dict[str, Any], 
                                   entity: Any, context: Dict[str, Any]) -> Generator:
        """조건부 분기 액션을 실행합니다."""
        script = params.get("script", "")
        if script:
            act_log = []
            out_pipes = context.get('out_pipes', {})
            from_block_name = context.get('block_name', 'Unknown')
            yield from self.script_executor.execute_conditional_branch_script(env, script, entity, act_log, out_pipes, from_block_name)
            
            if any("moved to" in log for log in act_log):
                return 'route_out'
                
        return 'continue'
        
    def _execute_block_entry(self, env: simpy.Environment, params: Dict[str, Any], 
                            entity: Any, context: Dict[str, Any]) -> Generator:
        """블록 진입 액션을 실행합니다."""
        delay = params.get("delay", "1")
        
        if delay and delay != "0":
            delay_time = parse_delay_value(str(delay))
            yield env.timeout(delay_time)
            
        # 엔티티 위치는 이미 블록에 있으므로 추가 작업 불필요