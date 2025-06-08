"""
완전히 새로운 단순화된 시뮬레이션 엔진
블록 중심의 독립적 처리 방식
"""
import simpy
import logging
from typing import Dict, List, Optional, Any, Generator
from .simple_block import IndependentBlock
from .simple_entity import SimpleEntity
from .simple_signal_manager import SimpleSignalManager
from .core.integer_variable_manager import IntegerVariableManager
from .core.unified_variable_accessor import UnifiedVariableAccessor
from .core.debug_manager import DebugManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SimpleSimulationEngine:
    """단순화된 시뮬레이션 엔진"""
    
    def set_debug_manager(self, debug_manager):
        """디버그 매니저 설정"""
        self.debug_manager = debug_manager
        # Debug manager set
        
        # 이미 설정된 블록들의 스크립트 실행기에도 디버그 매니저 설정
        if hasattr(self, 'blocks'):
            for block in self.blocks.values():
                if hasattr(block, 'script_executor') and block.script_executor:
                    block.script_executor.debug_manager = debug_manager
                    # Debug manager set for block
    
    def __init__(self):
        self.env: Optional[simpy.Environment] = None
        self.blocks: Dict[str, IndependentBlock] = {}
        self.signal_manager = SimpleSignalManager()
        self.integer_manager = IntegerVariableManager()
        self.variable_accessor = UnifiedVariableAccessor(self.signal_manager, self.integer_manager)
        self.debug_manager = None  # 외부에서 설정
        self.entity_queue: Optional[simpy.Store] = None
        
        # 시뮬레이션 상태
        self.step_count = 0
        self.total_entities_created = 0
        self.total_entities_processed = 0
        self.sim_log: List[Dict[str, Any]] = []
        
        # 설정
        self.max_simulation_time = 1000.0
        self.step_timeout = 10.0
        
        # 실행 모드 관련
        self.execution_mode = "default"
        self.time_step_duration = 1.0  # 시간 스텝 모드에서 1스텝당 시간(초)
        self.high_speed_config = {}  # 고속 모드 설정
    
    def reset(self):
        """시뮬레이션 초기화"""
        self.env = None
        self.blocks.clear()
        self.signal_manager.reset()
        self.integer_manager.reset()
        if self.debug_manager:
            self.debug_manager.reset()
        self.entity_queue = None
        self.step_count = 0
        self.total_entities_created = 0
        self.total_entities_processed = 0
        self.sim_log.clear()
    
    def setup_simulation(self, config: Dict[str, Any]):
        """시뮬레이션 설정"""
        self.env = simpy.Environment()
        self.entity_queue = simpy.Store(self.env)
        
        # 신호 초기화
        if 'initial_signals' in config:
            self.signal_manager.initialize_signals(config['initial_signals'])
        
        # 전역 신호/변수 초기화 (통합 형식)
        if 'globalSignals' in config:
            self.variable_accessor.initialize_from_config(config['globalSignals'])
        
        # 블록 생성
        for block_config in config.get('blocks', []):
            self._create_block(block_config)
        
        # 연결 설정
        for connection in config.get('connections', []):
            self._setup_connection(connection)
        
        # 블록 프로세스 시작
        for block_id, block in self.blocks.items():
            # logger.info(f"Starting process for block '{block.name}' (ID: {block_id}), has_force_execution: {block.has_force_execution()}")
            process = block.create_block_process(self.env, self.entity_queue, self)
            self.env.process(process)
        
        logger.info(f"Simulation setup completed with {len(self.blocks)} blocks")
        # Debug manager status checked
    
    def set_execution_mode(self, mode: str, config: Dict[str, Any] = None):
        """실행 모드 설정"""
        valid_modes = ["default", "time_step", "high_speed"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid execution mode: {mode}. Valid modes: {valid_modes}")
        
        self.execution_mode = mode
        
        if config:
            if mode == "time_step" and "step_duration" in config:
                self.time_step_duration = float(config["step_duration"])
                logger.info(f"Time step mode configured: {self.time_step_duration} seconds per step")
            elif mode == "high_speed":
                # 고속 모드 설정
                self.high_speed_config = config
                logger.info(f"High speed mode configured: {config}")
    
    def get_execution_mode(self) -> str:
        """현재 실행 모드 반환"""
        return self.execution_mode
    
    def get_mode_config(self) -> Dict[str, Any]:
        """현재 모드 설정 반환"""
        if self.execution_mode == "time_step":
            return {"step_duration": self.time_step_duration}
        elif self.execution_mode == "high_speed":
            return self.high_speed_config
        return {}
    
    def _create_block(self, block_config: Dict[str, Any]):
        """블록 생성"""
        block_id = str(block_config['id'])
        block_name = block_config['name']
        
        # 스크립트 추출 - actions의 script 타입을 우선 사용
        script_lines = []
        
        # 1. actions에서 script 타입 액션 찾기 (최우선)
        if 'actions' in block_config:
            for action in block_config['actions']:
                # Pydantic 모델인 경우 딕셔너리로 변환
                if hasattr(action, 'model_dump'):
                    action_dict = action.model_dump()
                elif hasattr(action, 'dict'):
                    action_dict = action.dict()
                else:
                    action_dict = action
                
                if isinstance(action_dict, dict) and action_dict.get('type') == 'script':
                    script = action_dict.get('parameters', {}).get('script', '')
                    if script:
                        # logger.info(f"Block {block_name} using script from actions: {script[:50]}...")
                        script_lines = script.split('\n')
                        # logger.info(f"Block {block_name} parsed {len(script_lines)} script lines from actions")
                        break
        
        # 2. script 타입 액션이 없으면 다른 actions 변환
        if not script_lines and 'actions' in block_config:
            # logger.info(f"Block {block_name} converting non-script actions to script")
            script_lines = self._convert_actions_to_script(block_config['actions'])
        
        # 3. actions가 없거나 비어있으면 script 필드 사용 (하위 호환성)
        if not script_lines and 'script' in block_config:
            # logger.info(f"Block {block_name} using legacy script field: {block_config['script'][:50]}...")
            script_lines = block_config['script'].split('\n')
            # logger.info(f"Block {block_name} parsed {len(script_lines)} script lines from legacy field")
        
        # 커넥터에서 스크립트 추출 (ex4.json 형식 지원)
        if not script_lines and 'connectionPoints' in block_config:
            for conn in block_config['connectionPoints']:
                if 'actions' in conn:
                    for action in conn['actions']:
                        if isinstance(action, dict) and action.get('type') == 'conditional_branch':
                            script = action.get('parameters', {}).get('script', '')
                            if script:
                                script_lines.extend(script.split('\n'))
                                logger.info(f"Extracted script from connector for block {block_name}: {len(script_lines)} lines")
        
        # 블록 생성
        # ProcessBlockConfig 모델은 'capacity' 필드를 사용하므로 둘 다 확인
        max_capacity = block_config.get('capacity', block_config.get('maxCapacity', 100))
        block = IndependentBlock(
            block_id=block_id,
            block_name=block_name,
            script_lines=script_lines,
            signal_manager=self.signal_manager,
            max_capacity=max_capacity,
            integer_manager=self.integer_manager,
            variable_accessor=self.variable_accessor,
            debug_manager=self.debug_manager
        )
        
        # 블록 상태 초기화 - 시뮬레이션 초기화 시 상태를 명시적으로 None으로 설정
        block.status = None
        
        # 블록 타입 설정 제거 - 모든 블록이 동일하게 동작
        
        self.blocks[block_id] = block
        # Block created
    
    def _convert_actions_to_script(self, actions: List[Any]) -> List[str]:
        """기존 actions를 스크립트로 변환"""
        script_lines = []
        
        for action in actions:
            # Pydantic 모델인 경우 딕셔너리로 변환
            if hasattr(action, 'model_dump'):
                action_dict = action.model_dump()
            elif hasattr(action, 'dict'):
                action_dict = action.dict()
            else:
                action_dict = action
                
            action_type = action_dict.get('type', '') if isinstance(action_dict, dict) else ''
            params = action_dict.get('parameters', {}) if isinstance(action_dict, dict) else {}
            
            if action_type == 'delay':
                duration = params.get('duration', 1)
                script_lines.append(f"delay {duration}")
            
            elif action_type == 'signal_update':
                signal_name = params.get('signal_name', '')
                value = params.get('value', True)
                script_lines.append(f"{signal_name} = {str(value).lower()}")
            
            elif action_type == 'signal_wait':
                signal_name = params.get('signal_name', '')
                expected_value = params.get('expected_value', True)
                script_lines.append(f"wait {signal_name} = {str(expected_value).lower()}")
            
            elif action_type == 'route_to_connector':
                target_block = params.get('target_block_id', '')
                target_connector = params.get('target_connector_id', 'L')
                delay = params.get('delay', 0)
                if delay > 0:
                    script_lines.append(f"go to {target_block}.{target_connector},{delay}")
                else:
                    script_lines.append(f"go to {target_block}.{target_connector}")
            
            elif action_type == 'conditional_branch':
                condition = params.get('condition', '')
                script = params.get('script', '')
                if script:
                    # script만 있는 경우 (조건 없이)
                    for line in script.split('\n'):
                        if line.strip():
                            script_lines.append(line.strip())
            
            elif action_type == 'script':
                # script 타입 액션은 _create_block에서 별도 처리하므로 여기서는 건너뛰기
                continue
        
        return script_lines
    
    def _setup_connection(self, connection: Dict[str, Any]):
        """연결 설정"""
        from_block_id = str(connection.get('fromBlockId', ''))
        from_connector = connection.get('fromConnectorId', 'R')
        to_block_id = str(connection.get('toBlockId', ''))
        
        if from_block_id in self.blocks:
            self.blocks[from_block_id].add_output_connection(from_connector, to_block_id)
            # Connection established
        else:
            logger.warning(f"Block {from_block_id} not found for connection")
    
    def get_block_id_by_name(self, block_name: str) -> Optional[str]:
        """블록 이름으로 블록 ID 찾기"""
        for block_id, block in self.blocks.items():
            if block.name == block_name:
                return block_id
        return None

    def move_entity_to_block(self, env: simpy.Environment, entity: SimpleEntity, 
                           target_block_id: str) -> Generator:
        """엔티티를 다른 블록으로 이동"""
        # 블록 이름인 경우 ID로 변환
        if target_block_id not in self.blocks:
            resolved_id = self.get_block_id_by_name(target_block_id)
            if resolved_id:
                target_block_id = resolved_id
        
        if target_block_id in self.blocks:
            target_block = self.blocks[target_block_id]
            if target_block.add_entity(entity):
                # Entity moved
                yield env.timeout(0)
            else:
                logger.warning(f"Block {target_block.name} is full, entity {entity.id} discarded")
                yield env.timeout(0)
        else:
            logger.error(f"Target block {target_block_id} not found")
            yield env.timeout(0)
    
    def step_simulation_time_based(self, step_duration: Optional[float] = None) -> Dict[str, Any]:
        """시간 기반 시뮬레이션 스텝 실행"""
        if not self.env:
            return {'error': 'Simulation not initialized'}
        
        # 블록이 없으면 초기화되지 않은 것으로 간주
        if not self.blocks:
            logger.warning("No blocks found - simulation not properly initialized")
            return {'error': 'Simulation not initialized - no blocks found'}
        
        # 스텝 지속 시간 결정 (매개변수 > 모드 설정 > 기본값)
        duration = step_duration or self.time_step_duration
        
        # 시작 시간과 목표 시간 설정
        start_time = self.env.now
        target_time = start_time + duration
        
        logger.info(f"Time step execution: {start_time} -> {target_time} (duration: {duration}s)")
        
        try:
            # 디버그 매니저가 방금 재개되었는지 확인
            if self.debug_manager and getattr(self.debug_manager, 'just_resumed', False):
                self.debug_manager.just_resumed = False
            
            # 지정된 시간까지 실행
            while self.env.now < target_time:
                # 디버그 매니저가 일시정지 상태인지 확인
                if self.debug_manager and self.debug_manager.debug_state.is_paused:
                    logger.info(f"Execution paused at breakpoint at time {self.env.now}")
                    break
                
                # 다음 이벤트가 없으면 목표 시간까지 진행
                if self.env.peek() >= float('inf'):
                    self.env.run(until=target_time)
                    break
                
                # 다음 이벤트가 목표 시간을 초과하면 목표 시간까지만 진행
                next_event_time = self.env.peek()
                if next_event_time > target_time:
                    self.env.run(until=target_time)
                    break
                
                # 다음 이벤트 실행
                self.env.step()
            
            self.step_count += 1
            
            # 결과 수집
            result = self._collect_simulation_results()
            result['step_count'] = self.step_count
            result['simulation_time'] = round(self.env.now, 1)
            result['time_advanced'] = round(self.env.now - start_time, 1)
            result['target_time_reached'] = self.env.now >= target_time
            result['execution_mode'] = 'time_step'
            result['step_duration'] = duration
            
            return result
            
        except Exception as e:
            logger.error(f"Time step execution error: {e}")
            return {
                'error': str(e),
                'step_count': self.step_count,
                'simulation_time': round(self.env.now, 1),
                'execution_mode': 'time_step'
            }
    
    def step_simulation_high_speed(self) -> Dict[str, Any]:
        """고속 모드 시뮬레이션 실행 - 큰 시간 스텝으로 종료 조건까지 실행"""
        if not self.env:
            return {'error': 'Simulation not initialized'}
        
        # 블록이 없으면 초기화되지 않은 것으로 간주
        if not self.blocks:
            logger.warning("No blocks found - simulation not properly initialized")
            return {'error': 'Simulation not initialized - no blocks found'}
        
        # 고속 모드 설정 가져오기
        config = self.high_speed_config
        large_time_step = config.get('large_time_step', 9000000)  # 기본 9백만초 (매우 큰 값)
        target_entity_count = config.get('target_entity_count', None)
        target_simulation_time = config.get('target_simulation_time', None)
        
        logger.info(f"High speed mode execution: large_time_step={large_time_step}, target_entity_count={target_entity_count}, target_time={target_simulation_time}")
        
        try:
            # 시작 상태 저장
            start_time = self.env.now
            start_entities_processed = self._get_total_entities_processed()
            
            # 종료 조건 체크 함수
            def check_termination_conditions():
                current_entities_processed = self._get_total_entities_processed()
                
                # 1. 목표 엔티티 개수 달성
                if target_entity_count and current_entities_processed >= target_entity_count:
                    return True, f"Target entity count reached: {current_entities_processed}/{target_entity_count}"
                
                # 2. 목표 시뮬레이션 시간 달성
                if target_simulation_time and self.env.now >= target_simulation_time:
                    return True, f"Target simulation time reached: {self.env.now:.1f}/{target_simulation_time}"
                
                return False, None
            
            # 첫 번째 종료 조건 체크
            should_terminate, termination_reason = check_termination_conditions()
            if should_terminate:
                logger.info(f"High speed mode - already at termination condition: {termination_reason}")
                result = self._collect_simulation_results()
                result['execution_mode'] = 'high_speed'
                result['termination_reason'] = termination_reason
                result['time_advanced'] = 0
                return result
            
            # 큰 시간 스텝으로 실행
            target_time = start_time + large_time_step
            
            # 디버그 매니저가 방금 재개되었는지 확인
            if self.debug_manager and getattr(self.debug_manager, 'just_resumed', False):
                self.debug_manager.just_resumed = False
            
            # 종료 조건이 만족될 때까지 실행
            max_iterations = 1000  # 무한 루프 방지
            iteration_count = 0
            
            while iteration_count < max_iterations:
                iteration_count += 1
                
                # 종료 조건 체크
                should_terminate, termination_reason = check_termination_conditions()
                if should_terminate:
                    logger.info(f"High speed mode termination: {termination_reason}")
                    break
                
                # 디버그 매니저가 일시정지 상태인지 확인
                if self.debug_manager and self.debug_manager.debug_state.is_paused:
                    logger.info(f"High speed mode paused at breakpoint at time {self.env.now}")
                    break
                
                # 다음 이벤트가 없으면 목표 시간까지 진행
                if self.env.peek() >= float('inf'):
                    # 이벤트가 없으면 목표 시간까지 즉시 진행
                    if target_simulation_time and self.env.now < target_simulation_time:
                        self.env.run(until=target_simulation_time)
                    else:
                        self.env.run(until=target_time)
                    break
                
                # 다음 이벤트가 목표 시간을 초과하면 목표 시간까지만 진행
                next_event_time = self.env.peek()
                
                # 종료 조건에 따른 실행 제한
                effective_target_time = target_time
                if target_simulation_time and target_simulation_time < effective_target_time:
                    effective_target_time = target_simulation_time
                
                if next_event_time > effective_target_time:
                    self.env.run(until=effective_target_time)
                    break
                
                # 다음 이벤트 실행
                self.env.step()
            
            self.step_count += 1
            
            # 최종 종료 조건 체크
            should_terminate, termination_reason = check_termination_conditions()
            
            # 결과 수집
            result = self._collect_simulation_results()
            result['step_count'] = self.step_count
            result['simulation_time'] = round(self.env.now, 1)
            result['time_advanced'] = round(self.env.now - start_time, 1)
            result['execution_mode'] = 'high_speed'
            result['large_time_step'] = large_time_step
            result['entities_processed_this_step'] = self._get_total_entities_processed() - start_entities_processed
            
            # 종료 조건 정보 추가
            if should_terminate:
                result['termination_condition_met'] = True
                result['termination_reason'] = termination_reason
            else:
                result['termination_condition_met'] = False
                result['termination_reason'] = "Max iterations reached or other stop condition"
            
            return result
            
        except Exception as e:
            logger.error(f"High speed execution error: {e}")
            return {
                'error': str(e),
                'step_count': self.step_count,
                'simulation_time': round(self.env.now, 1),
                'execution_mode': 'high_speed'
            }
    
    def step_simulation(self) -> Dict[str, Any]:
        """시뮬레이션 1스텝 실행 - 실행 모드에 따라 적절한 방법 선택"""
        # 실행 모드에 따라 다른 실행 방법 사용
        if self.execution_mode == "time_step":
            return self.step_simulation_time_based()
        elif self.execution_mode == "high_speed":
            return self.step_simulation_high_speed()
        else:
            # 기본 모드 (엔티티 이동 기반)
            return self._step_simulation_default()
    
    def _step_simulation_default(self) -> Dict[str, Any]:
        """기본 모드 시뮬레이션 1스텝 실행 - 엔티티 이동 기반"""
        if not self.env:
            return {'error': 'Simulation not initialized'}
        
        # 블록이 없으면 초기화되지 않은 것으로 간주
        if not self.blocks:
            logger.warning("No blocks found - simulation not properly initialized")
            return {'error': 'Simulation not initialized - no blocks found'}
        
        # 초기 상태 저장
        initial_time = self.env.now
        initial_block_states = self._capture_block_states()
        movement_detected = False
        
        try:
            # 엔티티 이동이 발생할 때까지 실행
            max_iterations = 10000  # 무한 루프 방지
            iteration_count = 0
            
            # 디버그 매니저가 방금 재개되었는지 확인
            if self.debug_manager and getattr(self.debug_manager, 'just_resumed', False):
                # Continuing from breakpoint
                self.debug_manager.just_resumed = False  # 플래그 리셋
                # 브레이크포인트에서 재개된 경우 바로 실행 계속
            
            while iteration_count < max_iterations:
                iteration_count += 1
                
                # 디버그 매니저가 일시정지 상태인지 확인
                if self.debug_manager and self.debug_manager.debug_state.is_paused:
                    # 브레이크포인트에서 멈춘 상태이므로 더 이상 진행하지 않음
                    break
                
                # 이벤트가 없으면 종료
                if self.env.peek() >= float('inf'):
                    break
                
                # 이벤트 하나 실행
                self.env.step()
                
                # 블록 상태 변화 확인 (엔티티 이동 감지)
                current_block_states = self._capture_block_states()
                if self._check_entity_movement_between_states(initial_block_states, current_block_states):
                    movement_detected = True
                    break
            
            # 이동이 없었다면 최소한 시간은 진행되었음을 보장
            # 단, 디버그 모드에서 일시정지 상태가 아닐 때만
            if not movement_detected and self.env.now == initial_time:
                if not (self.debug_manager and self.debug_manager.debug_state.is_paused):
                    # 다음 이벤트까지 실행
                    if self.env.peek() < float('inf'):
                        self.env.run(until=self.env.peek())
            
            self.step_count += 1
            
            # 결과 수집
            result = self._collect_simulation_results()
            result['step_count'] = self.step_count
            result['simulation_time'] = round(self.env.now, 1)
            result['time_advanced'] = round(self.env.now - initial_time, 1)
            result['movement_detected'] = movement_detected
            result['execution_mode'] = 'default'
            
            return result
            
        except Exception as e:
            logger.error(f"Step execution error: {e}")
            return {
                'error': str(e),
                'step_count': self.step_count,
                'simulation_time': round(self.env.now, 1),
                'execution_mode': 'default'
            }
    
    def _get_total_entity_count(self) -> int:
        """전체 엔티티 개수 반환"""
        total = 0
        for block in self.blocks.values():
            total += len(block.entities_in_block)
        return total
    
    def _get_total_entities_processed(self) -> int:
        """전체 처리된 엔티티 개수 반환"""
        total = 0
        for block in self.blocks.values():
            status = block.get_status()
            total += status.get('total_processed', 0)
        return total
    
    def _capture_block_states(self) -> Dict[str, List[str]]:
        """각 블록의 엔티티 ID 목록을 캡처"""
        states = {}
        for block_id, block in self.blocks.items():
            states[block_id] = [entity.id for entity in block.entities_in_block]
        return states
    
    def _check_entity_movement_between_states(self, initial_states: Dict[str, List[str]], 
                                            current_states: Dict[str, List[str]]) -> bool:
        """두 상태 간 엔티티 이동이 있었는지 확인"""
        # 각 블록의 엔티티 목록이 다른지 확인
        for block_id in initial_states:
            if set(initial_states.get(block_id, [])) != set(current_states.get(block_id, [])):
                return True
        return False
    
    def _run_until_timeout(self, timeout_event) -> Generator:
        """타임아웃까지 실행"""
        try:
            yield timeout_event
        except simpy.Interrupt:
            pass
    
    def collect_script_logs(self) -> List[Dict[str, Any]]:
        """모든 블록의 스크립트 로그 수집"""
        all_logs = []
        for block in self.blocks.values():
            logs = block.get_script_logs()
            all_logs.extend(logs)
        
        # 시간순 정렬
        all_logs.sort(key=lambda x: x['time'])
        return all_logs
    
    def _collect_simulation_results(self) -> Dict[str, Any]:
        """시뮬레이션 결과 수집"""
        # 블록 상태 수집
        block_states = {}
        total_entities = 0
        total_processed = 0
        
        for block_id, block in self.blocks.items():
            status = block.get_status()
            block_states[block_id] = {
                'name': status['name'],
                'entities': [{
                    'id': e.id, 
                    'location': e.current_block,
                    'state': getattr(e, 'state', 'normal'),
                    'color': getattr(e, 'color', None),
                    'custom_attributes': list(getattr(e, 'custom_attributes', set()))
                } for e in block.entities_in_block],
                'entities_count': status['entities_count'],
                'total_processed': status['total_processed'],
                'warnings': status.get('warnings', []),  # 경고 메시지 포함
                'status': status.get('status')  # 블록 상태 속성 추가
            }
            total_entities += status['entities_count']
            total_processed += status['total_processed']
        
        # 신호 상태
        signal_states = self.signal_manager.get_all_signals()
        
        # 전역 신호/변수 (통합 형식)
        global_signals = self.variable_accessor.to_config_format()
        
        # 스크립트 로그 수집
        script_logs = self.collect_script_logs()
        
        return {
            'block_states': block_states,
            'current_signals': signal_states,
            'globalSignals': global_signals,
            'total_entities_in_system': total_entities,
            'total_entities_processed': total_processed,
            'blocks_info': [block.get_status() for block in self.blocks.values()],
            'event_queue_size': len(self.env._queue) if hasattr(self.env, '_queue') else 0,
            'script_logs': script_logs,
            'debug_info': self.debug_manager.get_debug_info() if self.debug_manager else {}
        }
    
    def run_simulation(self, max_steps: int = 100) -> Dict[str, Any]:
        """시뮬레이션 연속 실행"""
        results = []
        
        for step in range(max_steps):
            result = self.step_simulation()
            results.append(result)
            
            if 'error' in result:
                break
            
            # 종료 조건 체크
            if self.env.now >= self.max_simulation_time:
                break
        
        return {
            'steps_executed': len(results),
            'final_result': results[-1] if results else {},
            'all_results': results
        }
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """현재 시뮬레이션 상태 반환"""
        if not self.env:
            return {
                'status': 'not_initialized',
                'globalSignals': self.variable_accessor.to_config_format()
            }
        
        return {
            'status': 'running',
            'current_time': round(self.env.now, 1),
            'step_count': self.step_count,
            'blocks_count': len(self.blocks),
            'signals': self.signal_manager.get_all_signals(),
            'globalSignals': self.variable_accessor.to_config_format(),
            'blocks': [block.get_status() for block in self.blocks.values()]
        }