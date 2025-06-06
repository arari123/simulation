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
                 signal_manager=None, max_capacity: int = 100, integer_manager=None, variable_accessor=None):
        self.id = block_id
        self.name = block_name
        self.script_lines = script_lines
        self.signal_manager = signal_manager
        self.max_capacity = max_capacity
        
        # 스크립트 실행기
        self.script_executor = SimpleScriptExecutor(signal_manager, integer_manager, variable_accessor)
        
        # 블록 상태
        self.entities_in_block: List[SimpleEntity] = []
        self.total_processed = 0
        
        # 블록 간 연결 정보
        self.output_connections: Dict[str, str] = {}  # connector_name -> target_block_id
        
        # 경고 시스템
        self.warnings: List[Dict[str, Any]] = []  # 용량 관련 경고 메시지
    
    def add_output_connection(self, connector_name: str, target_block_id: str):
        """출력 연결 추가"""
        self.output_connections[connector_name] = target_block_id
    
    def add_capacity_warning(self, env, target_block_name: str, entity_id: str):
        """용량 초과로 인한 이동 실패 경고 추가"""
        warning = {
            'type': 'capacity_full',
            'message': f"'{target_block_name}' 블록 용량 초과로 엔티티 {entity_id} 이동 실패",
            'timestamp': round(env.now, 1),
            'target_block': target_block_name
        }
        self.warnings.append(warning)
        logger.warning(f"[{self.name}] {warning['message']}")
    
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
    
    def clear_old_warnings(self, env, max_age: float = 5.0):
        """오래된 경고 메시지 제거 (5초 후)"""
        current_time = env.now
        self.warnings = [w for w in self.warnings if current_time - w['timestamp'] <= max_age]
    
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
                logger.info(f"[{env.now:.1f}s] Block {self.name} created entity {entity.id}")
                yield env.timeout(0)
                return entity
        yield env.timeout(0)
        return None
    
    def dispose_entity(self, env: simpy.Environment, entity: SimpleEntity) -> Generator:
        """엔티티 제거 (dispose entity 명령용)"""
        if entity in self.entities_in_block:
            self.remove_entity(entity)
            self.total_processed += 1
            logger.debug(f"Block {self.name} disposed entity {entity.id}")
        yield env.timeout(0)
    
    def process_entity(self, env: simpy.Environment, entity: SimpleEntity) -> Generator:
        """엔티티 도착 시 스크립트를 순차 실행 (Batch 방식)"""
        current_line = 0
        max_iterations = 1000  # 무한 루프 방지
        iteration_count = 0
        
        while current_line < len(self.script_lines) and iteration_count < max_iterations:
            iteration_count += 1
            line = self.script_lines[current_line].strip()
            
            # 빈 줄이나 주석은 건너뛰기
            if not line or line.startswith('//'):
                current_line += 1
                continue
            
            # 스크립트 라인 실행
            logger.debug(f"[{self.name}] Executing line {current_line}: {line}, entity: {entity}")
            result = yield from self.script_executor.execute_script_line(env, line, entity, self.name, self)
            logger.debug(f"[{self.name}] Result: {result}")
            
            # 결과 처리
            if isinstance(result, tuple) and result[0] == 'created_entity':
                # create entity 명령으로 엔티티가 생성된 경우
                entity = result[1]  # 생성된 엔티티로 교체
                logger.info(f"[{self.name}] Entity created and updated: {entity.id}")
                logger.info(f"[{self.name}] Continuing with new entity, next line: {current_line + 1}")
                current_line += 1
            elif result == 'movement':
                # 이동 요청이 있어도 스크립트는 계속 실행
                current_line += 1
            elif result == 'continue':
                # force execution 등의 명령은 그냥 다음 줄로
                current_line += 1
            elif isinstance(result, tuple) and result[0] == 'jump':
                # jump 명령 처리
                target_line = result[1]
                if 0 <= target_line < len(self.script_lines):
                    current_line = target_line
                    continue
                else:
                    current_line += 1
            elif isinstance(result, tuple) and result[0] == 'if':
                # if 조건문 처리
                condition_result = result[1]
                if condition_result:
                    # 조건이 참이면 들여쓰기된 블록 실행
                    current_line += 1
                    # if 블록 내부의 명령들을 실행하고 movement 발생 시 즉시 리턴
                    while current_line < len(self.script_lines):
                        line = self.script_lines[current_line]
                        # 들여쓰기가 없으면 if 블록 종료
                        if not line.startswith('\t') and not line.startswith('    ') and not line.startswith('  '):
                            break
                        
                        stripped_line = line.strip()
                        if not stripped_line or stripped_line.startswith('//'):
                            current_line += 1
                            continue
                        
                        sub_result = yield from self.script_executor.execute_script_line(env, stripped_line, entity, self.name, self)
                        
                        if sub_result == 'movement':
                            # if 블록 내에서 이동이 발생해도 계속 실행
                            pass
                        elif isinstance(sub_result, tuple) and sub_result[0] == 'created_entity':
                            # if 블록 내에서 엔티티가 생성된 경우
                            entity = sub_result[1]  # 생성된 엔티티로 교체
                            logger.info(f"[{self.name}] Entity created in if block: {entity.id}")
                        
                        current_line += 1
                    # if 블록 실행 완료 후 current_line은 이미 if 블록 밖을 가리킴
                else:
                    # 조건이 거짓이면 들여쓰기된 블록 스킵
                    current_line = self._skip_indented_block(current_line)
            else:
                current_line += 1
        
        # 스크립트 실행 완료
        return None
    
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
        # force execution 여부 확인
        is_force_execution = self.has_force_execution()
        
        while True:
            try:
                # 오래된 경고 정리
                self.clear_old_warnings(env)
                
                # 스크립트 상태 확인
                from .script_state_manager import script_state_manager
                state = script_state_manager.get_state(self.id)
                
                # 이미 실행 중인 경우 (force execution으로 생성된 엔티티 처리)
                if state.is_executing and state.entity_ref and state.entity_ref in self.entities_in_block:
                    entity = state.entity_ref
                    logger.debug(f"Block {self.name} continuing with entity {entity.id} from state")
                    
                    # 이동 요청 처리
                    if entity.movement_requested and entity.target_block:
                        target_block_id = self.output_connections.get(entity.target_connector, entity.target_block)
                        
                        # 블록 이름을 ID로 변환
                        if target_block_id not in engine_ref.blocks:
                            resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                            if resolved_id:
                                target_block_id = resolved_id
                                
                        if target_block_id and target_block_id in engine_ref.blocks:
                            target_block = engine_ref.blocks[target_block_id]
                            # 대상 블록이 엔티티를 받을 수 있는지 확인
                            if target_block.can_accept_entity():
                                self.remove_entity(entity)
                                yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                            else:
                                # 용량 초과로 이동 실패, 경고 추가
                                self.add_capacity_warning(env, target_block.name, entity.id)
                                logger.debug(f"Target block {target_block.name} is full, entity {entity.id} stays in block {self.name}")
                        else:
                            # 이동할 수 없으면 엔티티 제거
                            self.remove_entity(entity)
                            self.total_processed += 1
                        
                        # 상태 초기화
                        script_state_manager.end_execution(self.id)
                        
                # 블록에 엔티티가 있으면 처리
                elif self.entities_in_block and not is_force_execution:
                    # force execution 블록이 아닐 때만 일반 처리
                    entity = self.entities_in_block[0]
                    
                    # 스크립트 실행 (기존 process_entity 사용하여 go to 이후 스크립트도 실행)
                    yield from self.process_entity(env, entity)
                    
                    # 이동 요청 처리
                    if entity.movement_requested and entity.target_block:
                        target_block_id = self.output_connections.get(entity.target_connector, entity.target_block)
                        
                        # 블록 이름을 ID로 변환
                        if target_block_id not in engine_ref.blocks:
                            resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                            if resolved_id:
                                target_block_id = resolved_id
                                
                        if target_block_id and target_block_id in engine_ref.blocks:
                            target_block = engine_ref.blocks[target_block_id]
                            # 대상 블록이 엔티티를 받을 수 있는지 확인
                            if target_block.can_accept_entity():
                                self.remove_entity(entity)
                                yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                            else:
                                # 용량 초과로 이동 실패, 경고 추가
                                self.add_capacity_warning(env, target_block.name, entity.id)
                                logger.debug(f"Target block {target_block.name} is full, entity {entity.id} stays in block {self.name}")
                        else:
                            # 이동할 수 없으면 엔티티 제거
                            self.remove_entity(entity)
                            self.total_processed += 1
                elif is_force_execution:
                    # force execution 블록 처리
                    if not self.entities_in_block:
                        # 블록이 비어있을 때만 스크립트 실행
                        logger.debug(f"Block {self.name} executing script without entity (force execution)")
                        yield from self.process_entity(env, None)
                        logger.debug(f"Block {self.name} finished force execution, entities in block: {len(self.entities_in_block)}")
                    else:
                        # 엔티티가 있으면 이동 처리
                        entity = self.entities_in_block[0]
                        if entity.movement_requested and entity.target_block:
                            target_block_id = self.output_connections.get(entity.target_connector, entity.target_block)
                            
                            # 블록 이름을 ID로 변환
                            if target_block_id not in engine_ref.blocks:
                                resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                                if resolved_id:
                                    target_block_id = resolved_id
                                    
                            if target_block_id and target_block_id in engine_ref.blocks:
                                target_block = engine_ref.blocks[target_block_id]
                                # 대상 블록이 엔티티를 받을 수 있는지 확인
                                if target_block.can_accept_entity():
                                    self.remove_entity(entity)
                                    yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                                else:
                                    # 용량 초과로 이동 실패, 경고 추가
                                    self.add_capacity_warning(env, target_block.name, entity.id)
                                    logger.debug(f"Target block {target_block.name} is full, entity {entity.id} stays in block {self.name}")
                            else:
                                # 이동할 수 없으면 엔티티 제거
                                self.remove_entity(entity)
                                self.total_processed += 1
                    
                    # 짧은 대기
                    yield env.timeout(0.01)
                else:
                    # 엔티티가 없으면 잠시 대기
                    yield env.timeout(0.1)
                    
            except Exception as e:
                logger.error(f"Block {self.name} process error: {e}")
                yield env.timeout(0.1)
    
    def _source_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                       engine_ref) -> Generator:
        """소스 블록 프로세스"""
        
        # 스크립트에서 이동 지연 시간 추출
        transit_delay = 0
        for line in self.script_lines:
            stripped_line = line.strip()
            
            # go to 명령어 처리
            if stripped_line.startswith('go to '):
                parts = stripped_line.split(',')
                if len(parts) > 1:
                    try:
                        transit_delay = int(parts[1].strip())
                        break
                    except:
                        pass
            
            # go from 명령어 처리 (새로운 형식)
            elif stripped_line.startswith('go from '):
                # go from R to 공정1.L,3 형태에서 딜레이 추출
                if ' to ' in stripped_line and ',' in stripped_line:
                    # "to" 이후 부분에서 딜레이 찾기
                    to_part = stripped_line.split(' to ', 1)[1]
                    if ',' in to_part:
                        delay_part = to_part.split(',')[1].strip()
                        try:
                            transit_delay = int(delay_part)
                            break
                        except:
                            pass
        
        # 정확한 생성 주기 계산: 이동 시간만 고려
        generation_cycle = transit_delay  # 이동 시간과 동일하게 설정
        last_entity_sent = None  # 마지막으로 보낸 엔티티 추적
        
        while True:  # 계속 엔티티 생성
            # 정확한 생성 시간까지 대기
            if env.now < self.next_generation_time:
                yield env.timeout(self.next_generation_time - env.now)
            
            # 소스 블록 자체가 가득 찼으면 엔티티 생성하지 않음
            if not self.can_accept_entity():
                logger.debug(f"Source block {self.name} is full, skipping entity generation")
                yield env.timeout(1.0)  # 1초 대기로 변경하여 로그 빈도 줄임
                continue
            
            # 블록에 엔티티가 없을 때만 새로 생성 (기존 로직 유지)
            if len(self.entities_in_block) == 0:
                entity = SimpleEntity()
                entity.created_at = round(env.now, 1)
                
                if self.add_entity(entity):
                    logger.debug(f"Source block {self.name} created entity {entity.id}")
                    
                    # 다음 생성 시간 설정 (현재 시간 + 생성 주기)
                    self.next_generation_time = round(env.now + generation_cycle, 1)
                    
                    # 스크립트 실행 (끝까지 실행됨)
                    yield from self.process_entity(env, entity)
                    
                    # 이동 요청 처리
                    if entity.movement_requested and entity.target_block:
                        # 먼저 커넥터로 연결된 블록 찾기
                        target_block_id = self.output_connections.get(entity.target_connector)
                        
                        # 커넥터 연결이 없으면 블록 이름으로 직접 찾기
                        if not target_block_id:
                            target_block_id = entity.target_block
                            # 블록 이름을 블록 ID로 변환
                            resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                            if resolved_id:
                                target_block_id = resolved_id
                        
                        if target_block_id and target_block_id in engine_ref.blocks:
                            target_block = engine_ref.blocks[target_block_id]
                            # 대상 블록이 가득 차 있어도 이동 시도
                            if target_block.can_accept_entity():
                                self.remove_entity(entity)
                                yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                                
                                # 스크립트는 이미 끝까지 실행되었으므로 추가 실행 불필요
                                pass
                            else:
                                # 이동할 수 없으면 소스 블록에 남겨둠, 경고 추가
                                self.add_capacity_warning(env, target_block.name, entity.id)
                                logger.debug(f"Target block {target_block.name} is full, entity {entity.id} stays in source block {self.name}")
                        else:
                            # 대상 블록을 찾을 수 없으면 엔티티 제거
                            logger.warning(f"Target block not found, removing entity {entity.id}")
                            self.remove_entity(entity)
                else:
                    logger.warning(f"Failed to add entity to source block {self.name}")
            
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
        
        # 이동 요청 처리
        if entity.movement_requested and entity.target_block:
            target_block_id = self.output_connections.get(entity.target_connector, entity.target_block)
            
            # 블록 이름을 ID로 변환
            if target_block_id not in engine_ref.blocks:
                resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                if resolved_id:
                    target_block_id = resolved_id
                    
            if target_block_id and target_block_id in engine_ref.blocks:
                target_block = engine_ref.blocks[target_block_id]
                # 대상 블록이 엔티티를 받을 수 있는지 확인
                if target_block.can_accept_entity():
                    self.remove_entity(entity)
                    yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                else:
                    # 용량 초과로 이동 실패, 경고 추가
                    self.add_capacity_warning(env, target_block.name, entity.id)
                    logger.debug(f"Target block {target_block.name} is full, entity {entity.id} stays in block {self.name}")
                
                # 스크립트는 이미 끝까지 실행되었으므로 추가 실행 불필요
                pass
            else:
                # 이동할 수 없으면 엔티티 제거
                self.remove_entity(entity)
                self.total_processed += 1
        
        yield env.timeout(0)  # 즉시 처리
    
    def get_status(self) -> Dict[str, Any]:
        """블록 상태 정보 반환"""
        return {
            'id': self.id,
            'name': self.name,
            'entities_count': len(self.entities_in_block),
            'total_processed': self.total_processed,
            'capacity': f"{len(self.entities_in_block)}/{self.max_capacity}",
            'warnings': self.warnings  # 경고 메시지 포함
        }