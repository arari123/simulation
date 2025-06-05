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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class SimpleSimulationEngine:
    """단순화된 시뮬레이션 엔진"""
    
    def __init__(self):
        self.env: Optional[simpy.Environment] = None
        self.blocks: Dict[str, IndependentBlock] = {}
        self.signal_manager = SimpleSignalManager()
        self.entity_queue: Optional[simpy.Store] = None
        
        # 시뮬레이션 상태
        self.step_count = 0
        self.total_entities_created = 0
        self.total_entities_processed = 0
        self.sim_log: List[Dict[str, Any]] = []
        
        # 설정
        self.max_simulation_time = 1000.0
        self.step_timeout = 10.0
    
    def reset(self):
        """시뮬레이션 초기화"""
        self.env = None
        self.blocks.clear()
        self.signal_manager.reset()
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
        
        # 블록 생성
        for block_config in config.get('blocks', []):
            self._create_block(block_config)
        
        # 연결 설정
        for connection in config.get('connections', []):
            self._setup_connection(connection)
        
        # 블록 프로세스 시작
        for block in self.blocks.values():
            process = block.create_block_process(self.env, self.entity_queue, self)
            self.env.process(process)
        
        logger.info(f"Simulation setup completed with {len(self.blocks)} blocks")
    
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
                        logger.info(f"Block {block_name} using script from actions: {script[:50]}...")
                        script_lines = script.split('\n')
                        logger.info(f"Block {block_name} parsed {len(script_lines)} script lines from actions")
                        break
        
        # 2. script 타입 액션이 없으면 다른 actions 변환
        if not script_lines and 'actions' in block_config:
            logger.info(f"Block {block_name} converting non-script actions to script")
            script_lines = self._convert_actions_to_script(block_config['actions'])
        
        # 3. actions가 없거나 비어있으면 script 필드 사용 (하위 호환성)
        if not script_lines and 'script' in block_config:
            logger.info(f"Block {block_name} using legacy script field: {block_config['script'][:50]}...")
            script_lines = block_config['script'].split('\n')
            logger.info(f"Block {block_name} parsed {len(script_lines)} script lines from legacy field")
        
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
            max_capacity=max_capacity
        )
        
        # 블록 타입 설정
        if block_config.get('type') == 'source' or block_name in ['투입', 'Source']:
            block.set_as_source(block_config.get('generation_interval', 1.0))
        elif block_config.get('type') == 'sink' or block_name in ['배출', 'Sink']:
            block.set_as_sink()
        
        self.blocks[block_id] = block
        logger.info(f"Created block: {block_name}({block_id}) - Source: {block.is_source}, Sink: {block.is_sink}")
    
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
            logger.debug(f"Connection: {from_block_id}.{from_connector} -> {to_block_id}")
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
                logger.debug(f"Entity {entity.id} moved to block {target_block.name}")
                yield env.timeout(0)
            else:
                logger.warning(f"Block {target_block.name} is full, entity {entity.id} discarded")
                yield env.timeout(0)
        else:
            logger.error(f"Target block {target_block_id} not found")
            yield env.timeout(0)
    
    def step_simulation(self) -> Dict[str, Any]:
        """시뮬레이션 1스텝 실행 - 엔티티 이동 기반"""
        if not self.env:
            return {'error': 'Simulation not initialized'}
        
        # 초기 상태 저장
        initial_time = self.env.now
        initial_block_states = self._capture_block_states()
        movement_detected = False
        
        try:
            # 엔티티 이동이 발생할 때까지 실행
            max_iterations = 10000  # 무한 루프 방지
            iteration_count = 0
            
            while iteration_count < max_iterations:
                iteration_count += 1
                
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
            if not movement_detected and self.env.now == initial_time:
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
            
            
            return result
            
        except Exception as e:
            logger.error(f"Step execution error: {e}")
            return {
                'error': str(e),
                'step_count': self.step_count,
                'simulation_time': round(self.env.now, 1)
            }
    
    def _get_total_entity_count(self) -> int:
        """전체 엔티티 개수 반환"""
        total = 0
        for block in self.blocks.values():
            total += len(block.entities_in_block)
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
                'total_processed': status['total_processed']
            }
            total_entities += status['entities_count']
            total_processed += status['total_processed']
        
        # 신호 상태
        signal_states = self.signal_manager.get_all_signals()
        
        return {
            'block_states': block_states,
            'current_signals': signal_states,
            'total_entities_in_system': total_entities,
            'total_entities_processed': total_processed,
            'blocks_info': [block.get_status() for block in self.blocks.values()],
            'event_queue_size': len(self.env._queue) if hasattr(self.env, '_queue') else 0
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
            return {'status': 'not_initialized'}
        
        return {
            'status': 'running',
            'current_time': round(self.env.now, 1),
            'step_count': self.step_count,
            'blocks_count': len(self.blocks),
            'signals': self.signal_manager.get_all_signals(),
            'blocks': [block.get_status() for block in self.blocks.values()]
        }