"""
블록 프로세서 모듈
블록의 메인 프로세스 로직을 처리합니다.
"""
import simpy
from typing import Dict, List, Optional, Any, Generator
from .constants import ActionType, TimeoutConfig, FormatConfig, DEBUG_MODE, PERFORMANCE_MODE
from .entity_manager import EntityManager
from .signal_manager import SignalManager
from .pipe_manager import PipeManager
from .source_manager import SourceManager
from .action_executor import ActionExecutor
import logging

logger = logging.getLogger(__name__)

class BlockProcessor:
    """블록 프로세스를 처리하는 클래스"""
    
    def __init__(self, entity_manager: EntityManager, signal_manager: SignalManager,
                 pipe_manager: PipeManager, source_manager: SourceManager,
                 action_executor: ActionExecutor):
        self.entity_manager = entity_manager
        self.signal_manager = signal_manager
        self.pipe_manager = pipe_manager
        self.source_manager = source_manager
        self.action_executor = action_executor
        self.sim_log = []
        self.processed_entities_count = 0
        
    def reset(self):
        """블록 프로세서를 초기화합니다."""
        self.sim_log.clear()
        self.processed_entities_count = 0
        
    def create_block_process(self, env: simpy.Environment, block_config: Any) -> Generator:
        """블록 프로세스를 생성합니다."""
        block_id = str(block_config.id)
        block_log_prefix = FormatConfig.LOG_PREFIX_FORMAT.format(
            name=block_config.name,
            id=block_config.id
        )
        
        # 블록 타입 판별
        in_pipes = self.pipe_manager.get_input_pipes(block_id)
        out_pipes = self.pipe_manager.get_output_pipes(block_id)
        has_custom_sink = any(action.type == ActionType.CUSTOM_SINK for action in block_config.actions)
        is_source = self.source_manager.is_source_block(block_id)
        
        # 투입 블록인 경우 강제로 소스로 설정
        if block_config.name == "투입" or (not in_pipes and not has_custom_sink):
            is_source = True
            if DEBUG_MODE:
                logger.debug(f"{env.now:.2f}: {block_log_prefix} Forcing as source block")
        
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} Process started. "
                        f"Is source: {is_source}, Has sink: {has_custom_sink}, "
                        f"In pipes: {len(in_pipes)}, Out pipes: {len(out_pipes)}")
        
        self.sim_log.append({"time": env.now, "event": f"{block_log_prefix} process started."})
        
        while True:
            try:
                # 엔티티 획득
                if DEBUG_MODE:
                    logger.debug(f"{env.now:.2f}: {block_log_prefix} Trying to get entity...")
                
                entity = yield from self._get_entity_for_block(
                    env, block_config, is_source, has_custom_sink, in_pipes, block_log_prefix
                )
                
                if not entity:
                    if DEBUG_MODE:
                        logger.debug(f"{env.now:.2f}: {block_log_prefix} No entity available, waiting...")
                    yield env.timeout(TimeoutConfig.NO_ENTITY_TIMEOUT)
                    continue
            except Exception as e:
                logger.error(f"{env.now:.2f}: {block_log_prefix} Error getting entity: {e}")
                import traceback
                logger.error(traceback.format_exc())
                yield env.timeout(TimeoutConfig.NO_ENTITY_TIMEOUT)
                continue
                
            # 액션 실행
            if DEBUG_MODE:
                logger.debug(f"{env.now:.2f}: {block_log_prefix} Got entity {entity.id}, executing actions...")
            yield from self._execute_block_actions(
                env, block_config, entity, out_pipes, block_log_prefix
            )
            
            # 소스 블록인 경우 짧은 대기 후 계속 진행
            if is_source:
                yield env.timeout(0.1)  # 짧은 대기 후 다음 엔티티 생성 체크
            # 싱크 블록인 경우에도 짧은 대기를 추가하여 처리 사이클 보장
            elif has_custom_sink:
                yield env.timeout(0.01)  # 매우 짧은 대기로 다음 엔티티 처리 준비
            
    def _get_entity_for_block(self, env: simpy.Environment, block_config: Any,
                             is_source: bool, has_custom_sink: bool,
                             in_pipes: List[str], block_log_prefix: str) -> Generator:
        """블록에 맞는 엔티티를 획득합니다."""
        if is_source:
            return (yield from self._get_source_entity(env, block_config, block_log_prefix))
        elif has_custom_sink or in_pipes:
            return (yield from self._get_pipe_entity(env, block_config, in_pipes, block_log_prefix))
        else:
            if DEBUG_MODE:
                logger.debug(f"{env.now:.2f}: {block_log_prefix} No valid input method. Idling.")
            yield env.timeout(TimeoutConfig.IDLE_TIMEOUT)
            return None
            
    def _get_source_entity(self, env: simpy.Environment, block_config: Any, 
                          block_log_prefix: str) -> Generator:
        """소스 블록에서 엔티티를 생성합니다."""
        block_id = str(block_config.id)
        
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} Source entity generation started")
        
        # 생성 수 확인
        generated_count = self.source_manager.get_generated_count(block_id)
        
        # 첫 번째 엔티티 생성 시에만 request event 대기
        if generated_count == 0:
            request_event = self.source_manager.get_request_event(block_id)
            if request_event and not request_event.triggered:
                if DEBUG_MODE:
                    logger.debug(f"{env.now:.2f}: {block_log_prefix} Waiting for request event...")
                yield request_event
        else:
            # 이후 엔티티들은 블록이 비어있을 때만 생성
            current_count = self.entity_manager.get_block_entity_count(block_config.id)
            if current_count > 0:
                # 블록에 엔티티가 있으면 대기
                yield env.timeout(TimeoutConfig.NO_ENTITY_TIMEOUT)
                return None
        
        # 수용량 확인
        max_capacity = getattr(block_config, 'maxCapacity', None) or getattr(block_config, 'capacity', None)
        if not self.entity_manager.check_block_capacity(block_config.id, max_capacity):
            if not PERFORMANCE_MODE:
                current_count = self.entity_manager.get_block_entity_count(block_config.id)
                logger.info(f"{env.now:.2f}: {block_log_prefix} Source block at capacity "
                           f"({current_count}/{max_capacity}). Waiting for space...")
            yield env.timeout(TimeoutConfig.CAPACITY_RETRY_TIMEOUT)
            return None
            
        # 생성 조건 확인
        condition = self.source_manager.get_generation_condition(block_id)
        if condition:
            signal_name = condition.get('signal_name')
            expected_value = condition.get('expected_value', True)
            
            if signal_name:
                current_value = self.signal_manager.get_signal(signal_name, False)
                if current_value != expected_value:
                    if not PERFORMANCE_MODE:
                        logger.info(f"{env.now:.2f}: {block_log_prefix} Waiting for signal '{signal_name}'...")
                    yield from self.signal_manager.wait_for_signal(signal_name, expected_value, env)
                    
        # 수용량 재확인
        if not self.entity_manager.check_block_capacity(block_config.id, max_capacity):
            yield env.timeout(TimeoutConfig.NO_ENTITY_TIMEOUT)
            return None
            
        # 엔티티 생성
        new_count = self.source_manager.increment_generated_count(block_id)
        entity = self.entity_manager.create_entity(env, block_config.id, new_count)
        self.entity_manager.update_entity_location(entity, block_config.id, block_config.name)
        
        if not PERFORMANCE_MODE:
            current_count = self.entity_manager.get_block_entity_count(block_config.id)
            logger.info(f"{env.now:.2f}: {block_log_prefix} Generated Entity {entity.id} "
                      f"(총 {new_count}번째, 용량: {current_count}/{max_capacity or 'None'})")
                  
        self.sim_log.append({
            "time": env.now,
            "entity_id": entity.id,
            "event": f"Entity {entity.id} generated at Source {block_config.name}"
        })
        
        # 엔티티 생성 후 스텝 경계 생성
        # 매우 짧은 시간 후에 이벤트를 발생시켜 스텝이 완료되도록 함
        yield env.timeout(0.001)
        
        return entity
        
    def _get_pipe_entity(self, env: simpy.Environment, block_config: Any,
                        in_pipes: List[str], block_log_prefix: str) -> Generator:
        """파이프에서 엔티티를 가져옵니다."""
        # 파이프가 없으면 None 반환
        if not in_pipes:
            return None
            
        # 모든 입력 파이프를 확인하여 엔티티가 있는 첫 번째 파이프에서 가져오기
        # SimPy의 AnyOf를 사용하여 여러 파이프 중 하나에서 엔티티가 도착하면 즉시 처리
        pipe_events = []
        pipes_map = {}
        
        for pipe_id in in_pipes:
            pipe = self.pipe_manager.get_pipe(pipe_id)
            if pipe and len(pipe.items) > 0:
                # 즉시 사용 가능한 엔티티가 있는 경우
                if DEBUG_MODE:
                    logger.debug(f"{env.now:.2f}: {block_log_prefix} Found entity in pipe {pipe_id} (items: {len(pipe.items)})")
                entity = yield pipe.get()
                if DEBUG_MODE:
                    logger.debug(f"{env.now:.2f}: {block_log_prefix} Retrieved entity {entity.id} from pipe {pipe_id}")
                
                # 도착한 파이프 ID를 저장하여 커넥터 액션 실행 시 사용
                self._last_arrival_pipe = pipe_id
                return entity
        
        # 모든 파이프가 비어있는 경우, 첫 번째 파이프에서 대기
        pipe_id = in_pipes[0]
        pipe = self.pipe_manager.get_pipe(pipe_id)
        
        if not pipe:
            logger.error(f"{env.now:.2f}: {block_log_prefix} ERROR: Pipe {pipe_id} not found")
            return None
            
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} All pipes empty, waiting on first pipe {pipe_id}")
            
        # 엔티티 가져오기 - 파이프에서 블로킹 대기
        entity = yield pipe.get()
        self._last_arrival_pipe = pipe_id
        
        if DEBUG_MODE:
            logger.debug(f"{env.now:.2f}: {block_log_prefix} Retrieved entity {entity.id} from pipe {pipe_id}")
        
        # 수용량 확인
        max_capacity = getattr(block_config, 'maxCapacity', None) or getattr(block_config, 'capacity', None)
        if not self.entity_manager.check_block_capacity(block_config.id, max_capacity):
            # 다시 파이프에 넣기
            if DEBUG_MODE:
                logger.debug(f"{env.now:.2f}: {block_log_prefix} Block at capacity, returning entity {entity.id} to pipe")
            yield pipe.put(entity)
            yield env.timeout(TimeoutConfig.NO_ENTITY_TIMEOUT)
            return None
            
        # 엔티티 위치 업데이트
        self.entity_manager.update_entity_location(entity, block_config.id, block_config.name)
        
        if not PERFORMANCE_MODE:
            current_count = self.entity_manager.get_block_entity_count(block_config.id)
            logger.info(f"{env.now:.2f}: {block_log_prefix} Received Entity {entity.id} "
                      f"from TRANSIT state (capacity: {current_count}/{max_capacity or 'None'})")
                          
        # 커넥터 액션 실행 - 저장된 arrival pipe 사용
        arrival_pipe = getattr(self, '_last_arrival_pipe', pipe_id)
        yield from self._execute_connector_actions(env, block_config, entity, arrival_pipe, block_log_prefix)
        
        return entity
        
    def _execute_connector_actions(self, env: simpy.Environment, block_config: Any,
                                  entity: Any, arrival_pipe_id: str, block_log_prefix: str) -> Generator:
        """커넥터 액션을 실행합니다."""
        # 도착한 커넥터 찾기
        target_connector = None
        if hasattr(block_config, 'connectionPoints') and block_config.connectionPoints:
            for connector in block_config.connectionPoints:
                if arrival_pipe_id.endswith(f"to_{block_config.id}_{connector.id}"):
                    target_connector = connector
                    break
                    
        if not target_connector:
            return
            
        # 커넥터 액션이 없는 경우, 기본적으로 블록 진입만 처리
        if not hasattr(target_connector, 'actions') or not target_connector.actions:
            # 엔티티가 이미 블록에 위치 업데이트됨 (파이프에서 나올 때)
            # 추가 처리 없이 반환
            return
            
        # 커넥터 액션 실행
        connector_log_prefix = f"{block_log_prefix} [Connector:{target_connector.id}] [E:{entity.id}]"
        remaining_actions = []
        entity_routed = False
        
        for idx, action in enumerate(target_connector.actions):
            if not PERFORMANCE_MODE:
                logger.info(f"{env.now:.2f}: {connector_log_prefix} Executing connector action: "
                          f"{action.name} ({action.type})")
                      
            context = {
                'block_id': block_config.id,
                'block_name': block_config.name,
                'connector_id': target_connector.id,
                'out_pipes': self.pipe_manager.get_output_pipes(str(block_config.id))
            }
            
            result = yield from self.action_executor.execute_action(env, action, entity, context)
            
            if result == 'route_out':
                
                # 나머지 액션은 별도로 실행
                entity_routed = True
                remaining_actions = target_connector.actions[idx+1:]
                break
                
        # 엔티티가 라우팅된 후 나머지 액션을 별도 프로세스로 실행
        if entity_routed and remaining_actions:
            out_pipes = self.pipe_manager.get_output_pipes(str(block_config.id))
            env.process(self._execute_remaining_actions(env, block_config, remaining_actions, out_pipes, block_log_prefix))
                
    def _execute_block_actions(self, env: simpy.Environment, block_config: Any,
                              entity: Any, out_pipes: Dict[str, Any], block_log_prefix: str) -> Generator:
        """블록 액션을 실행합니다."""
        entity_log_prefix = f"{block_log_prefix} [E:{entity.id}]"
        
        # 액션 실행은 두 부분으로 나뉨: 
        # 1. 라우팅 전 액션들
        # 2. 라우팅 액션 이후 나머지 액션들 (별도 프로세스로 실행)
        remaining_actions = []
        entity_routed = False
        
        for idx, action in enumerate(block_config.actions):
            if not PERFORMANCE_MODE:
                logger.info(f"{env.now:.2f}: {entity_log_prefix} Executing action: "
                          f"{action.name} ({action.type})")
                      
            context = {
                'block_id': block_config.id,
                'block_name': block_config.name,
                'out_pipes': out_pipes
            }
            
            result = yield from self.action_executor.execute_action(env, action, entity, context)
            
            if result == 'route_out':
                
                # 나머지 액션은 별도로 실행
                entity_routed = True
                remaining_actions = block_config.actions[idx+1:]  # 나머지 액션들 저장
                break
            elif result == 'processed':
                self.processed_entities_count += 1
                self.entity_manager.process_entity(entity)
                # 엔티티가 처리된 후에도 나머지 액션들을 실행해야 함 (주로 신호 업데이트)
                remaining_actions = block_config.actions[idx+1:]
                if remaining_actions:
                    env.process(self._execute_remaining_actions(env, block_config, remaining_actions, out_pipes, block_log_prefix))
                break
            elif result == 'route_to_self_connector':
                # 자기 자신의 커넥터로 이동 - 커넥터 액션 실행
                connector_id = action.parameters.get('connector_id')
                if connector_id and hasattr(block_config, 'connectionPoints'):
                    for connector in block_config.connectionPoints:
                        if connector.id == connector_id:
                            # 커넥터 액션 실행
                            connector_log_prefix = f"{block_log_prefix} [Connector:{connector.id}] [E:{entity.id}]"
                            
                            for conn_action in connector.actions:
                                if not PERFORMANCE_MODE:
                                    logger.info(f"{env.now:.2f}: {connector_log_prefix} Executing connector action: "
                                              f"{conn_action.name} ({conn_action.type})")
                                              
                                conn_context = {
                                    'block_id': block_config.id,
                                    'block_name': block_config.name,
                                    'connector_id': connector.id,
                                    'out_pipes': out_pipes
                                }
                                
                                conn_result = yield from self.action_executor.execute_action(env, conn_action, entity, conn_context)
                                
                                if conn_result == 'route_out':
                                    entity_routed = True
                                    # 커넥터 액션 중 라우팅 이후의 액션들과 블록의 나머지 액션들을 모두 실행해야 함
                                    remaining_connector_actions = connector.actions[connector.actions.index(conn_action)+1:]
                                    remaining_actions = remaining_connector_actions + block_config.actions[idx+1:]
                                    break
                            # self-connector 액션 실행 후에도 블록 액션 계속 실행
                            continue
                            
        # 엔티티가 라우팅된 후 나머지 액션을 별도 프로세스로 실행
        if entity_routed and remaining_actions:
            env.process(self._execute_remaining_actions(env, block_config, remaining_actions, out_pipes, block_log_prefix))
            
    def _execute_remaining_actions(self, env: simpy.Environment, block_config: Any,
                                  actions: List[Any], out_pipes: Dict[str, Any], block_log_prefix: str) -> Generator:
        """엔티티가 라우팅된 후 나머지 액션을 실행합니다."""
        
        # 라우팅 딜레이를 고려하여 신호 복원을 지연시킴
        # 일반적으로 라우팅에 설정된 딜레이만큼 대기해야 함
        # 여기서는 최소한의 지연을 추가하여 엔티티가 파이프에 들어간 후 실행되도록 함
        yield env.timeout(0.1)
        
        for action in actions:
            if not PERFORMANCE_MODE:
                logger.info(f"{env.now:.2f}: {block_log_prefix} Executing remaining action: "
                          f"{action.name} ({action.type})")
                          
            # 엔티티 없이 실행 가능한 액션만 실행 (주로 신호 설정, 딜레이, 신호 대기 등)
            if action.type in [ActionType.SET_SIGNAL, ActionType.SIGNAL_UPDATE, ActionType.SIGNAL_WAIT, ActionType.DELAY, ActionType.CUSTOM_SINK]:
                context = {
                    'block_id': block_config.id,
                    'block_name': block_config.name,
                    'out_pipes': out_pipes
                }
                
                # 엔티티 없이 액션 실행
                yield from self.action_executor.execute_action(env, action, None, context)
            else:
                # 엔티티가 필요한 액션은 스킵
                if not PERFORMANCE_MODE:
                    logger.warning(f"{env.now:.2f}: {block_log_prefix} Skipping action {action.name} "
                                 f"({action.type}) - requires entity but entity is None")
                                 
    def _execute_remaining_actions_with_transaction(self, env: simpy.Environment, block_config: Any,
                                                   actions: List[Any], out_pipes: Dict[str, Any], 
                                                   block_log_prefix: str, source: str) -> Generator:
        """엔티티가 라우팅된 후 나머지 액션을 트랜잭션으로 실행합니다."""
        
        # 신호 변경을 위한 트랜잭션 시작
        transaction = None
        if self.signal_manager.transaction_manager:
            transaction = self.signal_manager.transaction_manager.begin_transaction(
                "post-routing", source
            )
        
        for action in actions:
            if not PERFORMANCE_MODE:
                logger.info(f"{env.now:.2f}: {block_log_prefix} Executing remaining action: "
                          f"{action.name} ({action.type})")
                          
            # 엔티티 없이 실행 가능한 액션만 실행 (주로 신호 설정, 딜레이, 신호 대기 등)
            if action.type in [ActionType.SET_SIGNAL, ActionType.SIGNAL_UPDATE, ActionType.SIGNAL_WAIT, ActionType.DELAY, ActionType.CUSTOM_SINK]:
                context = {
                    'block_id': block_config.id,
                    'block_name': block_config.name,
                    'out_pipes': out_pipes
                }
                
                # 엔티티 없이 액션 실행
                yield from self.action_executor.execute_action(env, action, None, context)
            else:
                # 엔티티가 필요한 액션은 스킵
                if not PERFORMANCE_MODE:
                    logger.warning(f"{env.now:.2f}: {block_log_prefix} Skipping action {action.name} "
                                 f"({action.type}) - requires entity but entity is None")
        
        # 트랜잭션 커밋
        if transaction:
            self.signal_manager.transaction_manager.commit_transaction(transaction)