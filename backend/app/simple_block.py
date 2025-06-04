"""
독립적인 블록 객체
각 블록이 완전 독립적으로 동작합니다.
"""
import simpy
from typing import List, Generator, Optional, Dict, Any
from .simple_script_executor import SimpleScriptExecutor
from .simple_entity import SimpleEntity

class IndependentBlock:
    """완전 독립적인 블록 객체"""
    
    def __init__(self, block_id: str, block_name: str, script_lines: List[str], 
                 signal_manager=None, max_capacity: int = 100):
        self.id = block_id
        self.name = block_name
        self.script_lines = script_lines
        self.signal_manager = signal_manager
        self.max_capacity = max_capacity
        
        # 스크립트 실행기
        self.script_executor = SimpleScriptExecutor(signal_manager)
        
        # 블록 상태
        self.entities_in_block: List[SimpleEntity] = []
        self.total_processed = 0
        self.is_source = False
        self.is_sink = False
        
        # 블록 간 연결 정보
        self.output_connections: Dict[str, str] = {}  # connector_name -> target_block_id
        
    def set_as_source(self, generation_interval: float = 1.0):
        """소스 블록으로 설정"""
        self.is_source = True
        self.generation_interval = generation_interval
        self.next_generation_time = 0  # 다음 생성 예정 시간
    
    def set_as_sink(self):
        """싱크 블록으로 설정"""
        self.is_sink = True
    
    def add_output_connection(self, connector_name: str, target_block_id: str):
        """출력 연결 추가"""
        self.output_connections[connector_name] = target_block_id
    
    def can_accept_entity(self) -> bool:
        """엔티티를 받을 수 있는지 확인"""
        return len(self.entities_in_block) < self.max_capacity
    
    def add_entity(self, entity: SimpleEntity) -> bool:
        """엔티티를 블록에 추가"""
        if self.can_accept_entity():
            entity.set_location(self.name)
            entity.reset_movement()
            self.entities_in_block.append(entity)
            return True
        return False
    
    def remove_entity(self, entity: SimpleEntity):
        """엔티티를 블록에서 제거"""
        if entity in self.entities_in_block:
            self.entities_in_block.remove(entity)
    
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
            print(f"DEBUG: Block {self.name} executing line {current_line}: {line}")
            result = yield from self.script_executor.execute_script_line(env, line, entity)
            print(f"DEBUG: Block {self.name} line {current_line} result: {result}")
            
            # 결과 처리
            if result == 'movement':
                # 이동 요청 시 현재 라인 반환 (남은 스크립트 실행을 위해)
                return current_line
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
                    # 조건이 참이면 다음 라인 실행
                    current_line += 1
                else:
                    # 조건이 거짓이면 들여쓰기된 블록 스킵
                    current_line = self._skip_indented_block(current_line)
            else:
                current_line += 1
        
        # 싱크 블록이면 처리 완료
        if self.is_sink:
            self.total_processed += 1
            yield env.timeout(0)
        
        return current_line
    
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
            print(f"DEBUG: Block {self.name} executing remaining line {current_line}: {line}")
            
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
                    print(f"DEBUG: Block {self.name} if condition True, continuing")
                    current_line += 1
                else:
                    # 조건이 거짓이면 들여쓰기된 블록 스킵
                    print(f"DEBUG: Block {self.name} if condition False, skipping block")
                    current_line = self._skip_indented_block(current_line)
            
            # 신호 설정 명령 실행
            elif ' = ' in line and not line.startswith('wait '):
                parts = line.split(' = ', 1)
                signal_name = parts[0].strip()
                value = parts[1].strip()
                bool_value = value.lower() == 'true'
                if self.signal_manager:
                    self.signal_manager.set_signal(signal_name, bool_value)
                    print(f"DEBUG: Block {self.name} set signal {signal_name} = {bool_value}")
                current_line += 1
            
            # go to/go from 명령은 무시 (이미 엔티티가 이동했으므로)
            elif line.startswith('go to ') or line.startswith('go from '):
                print(f"DEBUG: Block {self.name} skipping go command in remaining script")
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
            if line.startswith('\t') or line.startswith('    '):
                current_line += 1
            else:
                break
        
        return current_line
    
    def create_block_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                           engine_ref) -> Generator:
        """블록별 독립 프로세스"""
        while True:
            try:
                # 소스 블록의 경우 엔티티 생성
                if self.is_source:
                    yield from self._source_process(env, entity_queue, engine_ref)
                else:
                    # 일반 블록의 경우 엔티티 대기
                    yield from self._regular_process(env, entity_queue, engine_ref)
                    
            except Exception as e:
                print(f"Block {self.name} process error: {e}")
                yield env.timeout(0.1)
    
    def _source_process(self, env: simpy.Environment, entity_queue: simpy.Store, 
                       engine_ref) -> Generator:
        """소스 블록 프로세스"""
        print(f"DEBUG: Source process started for block {self.name}")
        
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
        
        while True:  # 계속 엔티티 생성
            # 정확한 생성 시간까지 대기
            if env.now < self.next_generation_time:
                yield env.timeout(self.next_generation_time - env.now)
            
            # 블록에 엔티티가 없을 때만 새로 생성
            if len(self.entities_in_block) == 0:
                entity = SimpleEntity()
                entity.created_at = round(env.now, 1)
                
                if self.add_entity(entity):
                    print(f"DEBUG: Entity {entity.id} created in {self.name} at time {round(env.now, 1)}")
                    print(f"DEBUG: Block {self.name} has {len(self.script_lines)} script lines")
                    if self.script_lines:
                        print(f"DEBUG: First script line: {self.script_lines[0]}")
                    
                    # 다음 생성 시간 설정 (현재 시간 + 생성 주기)
                    self.next_generation_time = round(env.now + generation_cycle, 1)
                    
                    # 스크립트 실행
                    current_line = yield from self.process_entity(env, entity)
                    
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
                            self.remove_entity(entity)
                            yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                            
                            # 소스 블록은 남은 스크립트를 실행하지 않음
                            # (각 엔티티마다 전체 스크립트를 새로 실행해야 함)
                        else:
                            # 이동할 수 없으면 엔티티 제거
                            self.remove_entity(entity)
            
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
        
        # 스크립트 실행
        current_line = yield from self.process_entity(env, entity)
        
        # 이동 요청 처리
        if entity.movement_requested and entity.target_block:
            target_block_id = self.output_connections.get(entity.target_connector, entity.target_block)
            
            # 블록 이름을 ID로 변환
            if target_block_id not in engine_ref.blocks:
                resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                if resolved_id:
                    target_block_id = resolved_id
                    
            if target_block_id and target_block_id in engine_ref.blocks:
                self.remove_entity(entity)
                yield from engine_ref.move_entity_to_block(env, entity, target_block_id)
                
                # 이동 후 남은 스크립트 실행
                if current_line + 1 < len(self.script_lines):
                    yield from self._execute_remaining_script(env, current_line + 1)
            else:
                # 이동할 수 없으면 엔티티 제거 (싱크로 처리)
                self.remove_entity(entity)
                self.total_processed += 1
        elif self.is_sink:
            # 싱크 블록에서 이동 요청이 없으면 처리 완료
            self.remove_entity(entity)
        
        yield env.timeout(0)  # 즉시 처리
    
    def get_status(self) -> Dict[str, Any]:
        """블록 상태 정보 반환"""
        return {
            'id': self.id,
            'name': self.name,
            'entities_count': len(self.entities_in_block),
            'total_processed': self.total_processed,
            'is_source': self.is_source,
            'is_sink': self.is_sink,
            'capacity': f"{len(self.entities_in_block)}/{self.max_capacity}"
        }