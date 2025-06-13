"""
독립적인 블록 객체
각 블록이 완전 독립적으로 동작합니다.
"""
import simpy
import logging
from typing import List, Generator, Optional, Dict, Any
from .simple_script_executor import SimpleScriptExecutor
from .simple_entity import SimpleEntity
from .step_mode_wrapper import StepModeWrapper

logger = logging.getLogger(__name__)

class IndependentBlock:
    """완전 독립적인 블록 객체"""
    
    def __init__(self, block_id: str, block_name: str, script_lines: List[str], 
                 signal_manager=None, max_capacity: int = 100, integer_manager=None, variable_accessor=None, debug_manager=None):
        self.id = block_id
        self.name = block_name
        self.script_lines = script_lines
        self.signal_manager = signal_manager
        self.max_capacity = max_capacity
        self.debug_manager = debug_manager
        
        # 스크립트 실행기
        self.script_executor = SimpleScriptExecutor(signal_manager, integer_manager, variable_accessor, debug_manager)
        
        # 블록 상태
        self.entities_in_block: List[SimpleEntity] = []
        self.total_processed = 0
        
        # 블록 간 연결 정보
        self.output_connections: Dict[str, str] = {}  # connector_name -> target_block_id
        
        # 경고 시스템
        self.warnings: List[Dict[str, Any]] = []  # 용량 관련 경고 메시지
        
        # 블록 상태 속성
        self.status: Optional[str] = None
        
        # 엔진 참조 (블록 상태 명령어 처리용)
        self.engine_ref = None
        
        # 실행 상태 관리
        self.execution_state = "idle"  # "idle" or "running"
        self.is_executing_script = False
        self.execute_requested = False  # execute 명령으로 실행 요청됨
        
        # 반복 로그 제한
        self.last_capacity_warning_time = {}  # entity_id -> last_warning_time
        self.capacity_warning_interval = 1.0  # 같은 엔티티에 대해 1초마다만 경고
    
    def add_output_connection(self, connector_name: str, target_block_id: str):
        """출력 연결 추가"""
        self.output_connections[connector_name] = target_block_id
    
    def add_capacity_warning(self, env, target_block_name: str, entity_id: str):
        """용량 초과로 인한 이동 실패 경고 추가 (반복 로그 제한)"""
        current_time = env.now
        
        # 이 엔티티에 대한 마지막 경고 시간 확인
        last_warning_time = self.last_capacity_warning_time.get(entity_id, 0)
        
        # 지정된 간격이 지났을 때만 경고 출력
        if current_time - last_warning_time >= self.capacity_warning_interval:
            warning = {
                'type': 'capacity_full',
                'message': f"'{target_block_name}' 블록 용량 초과로 엔티티 {entity_id} 이동 실패",
                'timestamp': round(env.now, 1),
                'target_block': target_block_name
            }
            self.warnings.append(warning)
            logger.warning(f"[{self.name}] {warning['message']}")
            self.last_capacity_warning_time[entity_id] = current_time
    
    def has_force_execution(self) -> bool:
        """첫 번째 줄이 force execution인지 확인"""
        if self.script_lines:
            first_line = self.script_lines[0].strip()
            return first_line.lower() == 'force execution'
        return False
    
    def get_script_lines_without_force_execution(self) -> List[str]:
        """force execution을 제외한 스크립트 라인 반환"""
        if self.has_force_execution():
            return self.script_lines[1:]  # 첫 번째 줄 제외
        return self.script_lines
    
    def should_execute_script_for_entity(self) -> bool:
        """엔티티 도착 시 스크립트를 실행해야 하는지 확인"""
        # 모든 블록은 엔티티가 도착하면 스크립트 실행
        return True
    
    def clear_old_warnings(self, env, max_age: float = 5.0):
        """오래된 경고 메시지 제거 (5초 후)"""
        current_time = env.now
        self.warnings = [w for w in self.warnings if current_time - w['timestamp'] <= max_age]
    
    def set_status(self, status: str):
        """블록 상태 설정"""
        self.status = status
        logger.info(f"Block {self.name} status changed to: {status}")
    
    def get_status(self) -> Optional[str]:
        """현재 블록 상태 반환"""
        return self.status
    
    def can_accept_entity(self) -> bool:
        """엔티티를 받을 수 있는지 확인"""
        return len(self.entities_in_block) < self.max_capacity
    
    def add_entity(self, entity: SimpleEntity) -> bool:
        """엔티티를 블록에 추가"""
        if self.can_accept_entity():
            entity.set_location(self.name)
            entity.reset_movement()
            # 엔티티 상태를 normal로 복원
            if hasattr(entity, 'state'):
                entity.state = "normal"
            self.entities_in_block.append(entity)
            return True
        return False
    
    def remove_entity(self, entity: SimpleEntity):
        """엔티티를 블록에서 제거"""
        if entity in self.entities_in_block:
            self.entities_in_block.remove(entity)
    
    def create_entity(self, env: simpy.Environment) -> Generator:
        """엔티티 생성 (create entity 명령용)"""
        if self.can_accept_entity():
            entity = SimpleEntity()
            entity.created_at = round(env.now, 1)
            if self.add_entity(entity):
                # logger.info(f"[{env.now:.1f}s] Block {self.name} created entity {entity.id}")
                yield env.timeout(0)
                return entity
        yield env.timeout(0)
        return None
    
    def dispose_entity(self, env: simpy.Environment, entity: SimpleEntity) -> Generator:
        """엔티티 제거 (dispose entity 명령용)"""
        if entity in self.entities_in_block:
            self.remove_entity(entity)
            self.total_processed += 1
            logger.info(f"[{self.name}] Disposed entity {entity.id}, total_processed now: {self.total_processed}")
        yield env.timeout(0)
    
    def process_entity(self, env: simpy.Environment, entity: SimpleEntity) -> Generator:
        """엔티티 도착 시 스크립트를 실행 (디버그 지원 포함)"""
        # 스크립트 실행 상태 관리
        from .script_state_manager import script_state_manager
        
        # 스크립트 실행 시작
        entity_id = entity.id if entity else None
        script_state_manager.start_execution(self.id, entity_id, entity)
        
        try:
            # 전체 스크립트를 문자열로 변환
            script_text = '\n'.join(self.script_lines)
            
            # 스크립트 실행 (디버그 매니저가 브레이크포인트 처리)
            result = yield from self.script_executor.execute_script(script_text, entity, env, self)
            
            # 결과 처리
            if isinstance(result, tuple) and result[0] == 'created_entity':
                # create entity 명령으로 엔티티가 생성된 경우
                entity = result[1]  # 생성된 엔티티로 교체
                logger.info(f"[{self.name}] Entity created and updated: {entity.id}")
            
            # 엔티티가 있으면 이 블록에서 처리되었음을 표시
            if entity:
                entity.processed_by_blocks.add(self.id)
        
        finally:
            # 스크립트 실행 완료 - 상태 초기화
            script_state_manager.end_execution(self.id)
        
        # 스크립트 실행 완료
        return None
    
    def execute_script_by_command(self, env: simpy.Environment) -> Generator:
        """execute 명령어를 통한 스크립트 실행"""
        if self.execution_state == "running":
            logger.info(f"Block {self.name} is already running, execute command ignored")
            return False
        
        # 실행 상태 변경
        self.execution_state = "running"
        self.is_executing_script = True
        logger.info(f"Block {self.name} started execution by command")
        
        try:
            # 블록에 엔티티가 있으면 첫 번째 엔티티로, 없으면 None으로 실행
            entity = self.entities_in_block[0] if self.entities_in_block else None
            yield from self.process_entity(env, entity)
        finally:
            # 실행 완료 후 상태 복원
            self.execution_state = "idle"
            self.is_executing_script = False
            logger.info(f"Block {self.name} finished execution")
        
        return True
    
    def _execute_remaining_script(self, env: simpy.Environment, start_line: int) -> Generator:
        """엔티티 이동 후 남은 스크립트 실행"""
        current_line = start_line
        
        while current_line < len(self.script_lines):
            line = self.script_lines[current_line].strip()
            
            # 빈 줄이나 주석은 건너뛰기
            if not line or line.startswith('//'):
                current_line += 1
                continue
            
            # 스크립트 라인 실행 (엔티티 없이)
            
            # if 조건문 처리
            if line.startswith('if '):
                condition = line[3:].strip()
                condition_result = False
                if ' = ' in condition:
                    parts = condition.split(' = ', 1)
                    signal_name = parts[0].strip()
                    expected_value = parts[1].strip().lower() == 'true'
                    if self.signal_manager:
                        current_value = self.signal_manager.get_signal(signal_name, False)
                        condition_result = current_value == expected_value
                
                if condition_result:
                    # 조건이 참이면 다음 라인 실행
                    current_line += 1
                else:
                    # 조건이 거짓이면 들여쓰기된 블록 스킵
                    current_line = self._skip_indented_block(current_line)
            
            # 신호 설정 명령 실행
            elif ' = ' in line and not line.startswith('wait '):
                parts = line.split(' = ', 1)
                signal_name = parts[0].strip()
                value = parts[1].strip()
                bool_value = value.lower() == 'true'
                if self.signal_manager:
                    self.signal_manager.set_signal(signal_name, bool_value)
                current_line += 1
            
            # go to/go from 명령은 무시 (이미 엔티티가 이동했으므로)
            elif line.startswith('go to ') or line.startswith('go from '):
                current_line += 1
            
            # product type 명령도 무시 (엔티티가 없으므로)
            elif 'product type' in line:
                current_line += 1
            
            else:
                current_line += 1
        
        yield env.timeout(0)
    
    def _skip_indented_block(self, if_line_index: int) -> int:
        """if 조건이 거짓일 때 들여쓰기된 블록을 스킵"""
        current_line = if_line_index + 1
        
        while current_line < len(self.script_lines):
            line = self.script_lines[current_line]
            stripped_line = line.lstrip()
            
            # 빈 줄은 건너뛰기
            if not stripped_line:
                current_line += 1
                continue
            
            # 들여쓰기가 있으면 스킵, 없으면 종료
            if line.startswith('\t') or line.startswith('    ') or line.startswith('  '):
                current_line += 1
            else:
                break
        
        return current_line
    
    def create_block_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                           engine_ref) -> Generator:
        """통합 블록 프로세스 - 모든 블록이 동일하게 동작"""
        # 엔진 참조 저장
        self.engine_ref = engine_ref
        
        # force execution 여부 확인
        is_force_execution = self.has_force_execution()
        
        while True:
            try:
                # 오래된 경고 정리
                self.clear_old_warnings(env)
                
                # 스크립트 상태 확인
                from .script_state_manager import script_state_manager
                state = script_state_manager.get_state(self.id)
                
                # 디버그: 매 루프마다 상태 출력 (force execution 블록만)
                if is_force_execution and env.now < 5:  # 처음 5초만 로그
                    logger.info(f"[LOOP] Block {self.name} at {env.now:.1f}s: entities={len(self.entities_in_block)}, is_executing={state.is_executing}, is_executing_script={self.is_executing_script}")
                
                # 이미 실행 중인 경우 (force execution으로 생성된 엔티티 처리)
                if state.is_executing and state.entity_ref and state.entity_ref in self.entities_in_block:
                    entity = state.entity_ref
                    # logger.debug(f"Block {self.name} continuing with entity {entity.id} from state")
                    
                    # go 명령이 동기적으로 처리되므로 여기서는 이동 처리하지 않음
                    # 상태 초기화
                    script_state_manager.end_execution(self.id)
                        
                # 엔티티 도착 시 자동 스크립트 실행 제거 - execute 명령어를 통해서만 실행
                
                # force execution이고 엔티티가 없으면 스크립트 실행
                # force execution은 is_executing 상태와 관계없이 실행 (wait에서 대기 중일 수 있음)
                elif is_force_execution:
                    # 로그 제한: 상태가 변경될 때만 출력
                    if not hasattr(self, '_last_force_exec_log_state'):
                        self._last_force_exec_log_state = None
                    
                    current_state = (len(self.entities_in_block), self.is_executing_script, state.is_executing)
                    if current_state != self._last_force_exec_log_state:
                        logger.info(f"[FORCE_EXEC_CHECK] Block {self.name}: entities={len(self.entities_in_block)}, is_executing_script={self.is_executing_script}, state.is_executing={state.is_executing}")
                        self._last_force_exec_log_state = current_state
                    
                    if not self.entities_in_block and not self.is_executing_script and not state.is_executing:
                        logger.info(f"Block {self.name} starting force execution (no entities in block)")
                        logger.info(f"Block {self.name} state: is_executing={state.is_executing}, entities_count={len(self.entities_in_block)}, execution_state={self.execution_state}")
                        
                        # force execution은 execution_state를 체크하지 않음 (무한 루프)
                        # 임시로 실행 중 표시
                        self.is_executing_script = True
                        
                        # 엔티티 없이 스크립트 실행
                        yield from self.process_entity(env, None)
                        
                        # 실행 완료 후 플래그만 해제 (execution_state는 변경하지 않음)
                        self.is_executing_script = False
                    
                    # go 명령이 동기적으로 처리되므로 여기서는 이동 처리하지 않음
                    
                    # 짧은 대기
                    yield env.timeout(0.01)
                else:
                    # 대기
                    yield env.timeout(0.01)
                    
            except Exception as e:
                logger.error(f"Block {self.name} process error: {e}")
                yield env.timeout(0.1)
    
    def _source_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                       engine_ref) -> Generator:
        """소스 블록 프로세스"""
        
        # 스크립트에서 이동 지연 시간 추출 (새로운 go 형식)
        transit_delay = 0
        for line in self.script_lines:
            stripped_line = line.strip()
            
            # 새로운 go 명령어 형식: go R to 공정1.L(0,3)
            if stripped_line.startswith('go '):
                import re
                # go R to 공정1.L(0,3) 형태 파싱
                go_pattern = r'^go\s+[^\s]+\s+to\s+[^(]+(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$'
                match = re.match(go_pattern, stripped_line, re.IGNORECASE)
                if match:
                    delay_str = match.group(2)  # 딜레이 부분
                    if delay_str:
                        try:
                            transit_delay = float(delay_str)
                            break
                        except:
                            pass
        
        # 정확한 생성 주기 계산: 이동 시간만 고려
        generation_cycle = transit_delay if transit_delay > 0 else 3  # 기본값 3초
        last_entity_sent = None  # 마지막으로 보낸 엔티티 추적
        
        while True:  # 계속 엔티티 생성
            # 정확한 생성 시간까지 대기
            if env.now < self.next_generation_time:
                yield env.timeout(self.next_generation_time - env.now)
            
            # 소스 블록 자체가 가득 찼으면 엔티티 생성하지 않음
            if not self.can_accept_entity():
                # logger.debug(f"Source block {self.name} is full, skipping entity generation")
                yield env.timeout(1.0)  # 1초 대기로 변경하여 로그 빈도 줄임
                continue
            
            # 블록에 엔티티가 없을 때만 새로 생성 (기존 로직 유지)
            if len(self.entities_in_block) == 0:
                entity = SimpleEntity()
                entity.created_at = round(env.now, 1)
                
                if self.add_entity(entity):
                    # logger.debug(f"Source block {self.name} created entity {entity.id}")
                    
                    # 다음 생성 시간 설정 (현재 시간 + 생성 주기)
                    self.next_generation_time = round(env.now + generation_cycle, 1)
                    
                    # 스크립트 실행 (끝까지 실행됨)
                    yield from self.process_entity(env, entity)
                    
                    # go 명령이 동기적으로 처리되므로 여기서는 이동 처리하지 않음
                else:
                    # logger.warning(f"Failed to add entity to source block {self.name}")
                    pass
            
            # 다음 생성까지 대기
            yield env.timeout(0.01)  # 매우 짧은 간격으로 확인
    
    def _regular_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                        engine_ref) -> Generator:
        """일반 블록 프로세스"""
        # 대기 중인 엔티티가 있는지 확인
        if not self.entities_in_block:
            yield env.timeout(0.1)
            return
        
        # 첫 번째 엔티티 처리
        entity = self.entities_in_block[0]
        
        # 스크립트 실행 (끝까지 실행됨)
        yield from self.process_entity(env, entity)
        
        # go 명령이 동기적으로 처리되므로 여기서는 이동 처리하지 않음
        
        yield env.timeout(0)  # 즉시 처리
    
    def get_status(self) -> Dict[str, Any]:
        """블록 상태 정보 반환"""
        return {
            'id': self.id,
            'name': self.name,
            'entities_count': len(self.entities_in_block),
            'total_processed': self.total_processed,
            'capacity': f"{len(self.entities_in_block)}/{self.max_capacity}",
            'warnings': self.warnings,  # 경고 메시지 포함
            'status': self.status  # 블록 상태 속성 추가
        }
    
    def get_script_logs(self) -> List[Dict[str, Any]]:
        """블록의 스크립트 실행 로그 반환"""
        if self.script_executor:
            return self.script_executor.get_simulation_logs()
        return []