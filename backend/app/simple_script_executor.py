"""
단순화된 스크립트 실행기
각 스크립트 명령어를 독립적인 함수로 처리합니다.
"""
import simpy
import re
import random
import logging
from typing import Generator, Dict, Any, Optional

logger = logging.getLogger(__name__)

def parse_delay_value(duration_str: str) -> float:
    """딜레이 값을 파싱합니다."""
    duration_str = duration_str.strip()
    
    if '-' in duration_str:
        parts = duration_str.split('-')
        if len(parts) == 2:
            min_val = float(parts[0].strip())
            max_val = float(parts[1].strip())
            return random.uniform(min_val, max_val)
    
    return float(duration_str)

class SimpleScriptExecutor:
    """단순화된 스크립트 실행기"""
    
    def __init__(self, signal_manager=None):
        self.signal_manager = signal_manager
        self.simulation_logs = []  # 시뮬레이션 로그 저장
        self.command_functions = {
            'delay': self.execute_delay,
            'signal_set': self.execute_signal_set,
            'signal_wait': self.execute_signal_wait,
            'go_to': self.execute_go_to,
            'if': self.execute_if,
            'jump': self.execute_jump,
            'wait': self.execute_wait,
            'product_type_add': self.execute_product_type_add,
            'product_type_remove': self.execute_product_type_remove,
            'log': self.execute_log,
            'create': self.execute_create,
            'dispose': self.execute_dispose
        }
    
    def execute_delay(self, env: simpy.Environment, delay_str: str) -> Generator:
        """delay 5 형태의 명령 실행"""
        delay_time = parse_delay_value(delay_str)
        yield env.timeout(delay_time)
    
    def execute_signal_set(self, env: simpy.Environment, signal_name: str, value: str) -> Generator:
        """신호명 = true 형태의 명령 실행"""
        bool_value = value.lower() == 'true'
        if self.signal_manager:
            old_value = self.signal_manager.get_signal(signal_name, None)
            self.signal_manager.set_signal(signal_name, bool_value)
            logger.info(f"Signal '{signal_name}' changed: {old_value} -> {bool_value}")
        yield env.timeout(0)  # 즉시 완료
    
    def execute_signal_wait(self, env: simpy.Environment, signal_name: str, expected_value: str) -> Generator:
        """wait 신호명 = true 형태의 명령 실행"""
        expected_bool = expected_value.lower() == 'true'
        
        while True:
            if self.signal_manager:
                current_value = self.signal_manager.get_signal(signal_name, False)
                if current_value == expected_bool:
                    break
            yield env.timeout(0.01)  # 0.01초마다 체크
    
    def _evaluate_single_signal_condition(self, condition: str) -> bool:
        """단일 신호 조건 평가 헬퍼 함수"""
        if ' = ' not in condition:
            return False
        
        parts = condition.split(' = ', 1)
        signal_name = parts[0].strip()
        expected_value = parts[1].strip().lower() == 'true'
        
        if self.signal_manager:
            current_value = self.signal_manager.get_signal(signal_name, False)
            return current_value == expected_value
        
        return False
    
    def execute_wait(self, env: simpy.Environment, condition: str, entity: Any = None) -> Generator:
        """wait 명령 실행 (신호 및 엔티티 속성 대기 지원, OR/AND 조건 지원)"""
        # wait 조건이 이미 만족되는지 먼저 확인
        if self.execute_if(env, condition, entity):
            yield env.timeout(0)
            return
        
        # 조건이 만족될 때까지 대기
        while True:
            yield env.timeout(0.01)
            if self.execute_if(env, condition, entity):
                return
    
    def execute_go_to(self, env: simpy.Environment, target: str, entity: Any) -> Generator:
        """go to 블록명.커넥터명,딜레이 형태의 명령 실행"""
        # 엔티티가 없으면 실행하지 않음
        if entity is None:
            yield env.timeout(0)
            return
        
        # 이미 transit 상태인 엔티티는 이동 명령 무시
        if hasattr(entity, 'state') and entity.state == 'transit':
            logger.debug(f"Entity {entity.id} is already in transit, ignoring go to {target}")
            yield env.timeout(0)
            return
            
        # 타겟 파싱 먼저 수행
        target_str = target
        delay_time = 0
        if ',' in target:
            parts = target.split(',', 1)
            target_str = parts[0].strip()
            delay_str = parts[1].strip()
            delay_time = parse_delay_value(delay_str)
        
        if '.' in target_str:
            block_name, connector_name = target_str.split('.', 1)
            entity.target_block = block_name.strip()
            entity.target_connector = connector_name.strip()
        else:
            entity.target_block = target_str.strip()
            entity.target_connector = None
        
        # 엔티티 상태를 transit으로 변경
        if hasattr(entity, 'state'):
            entity.state = "transit"
        
        # 딜레이 실행
        if delay_time > 0:
            yield env.timeout(delay_time)
        
        # 이동 완료 신호
        entity.movement_requested = True
        yield env.timeout(0)
    
    def execute_if(self, env: simpy.Environment, condition: str, entity: Any = None) -> bool:
        """if 조건문 평가 (엔티티 속성 체크 지원)"""
        # product type != 조건 체크 (not equal)
        if 'product type !=' in condition and entity:
            if not hasattr(entity, 'custom_attributes') or not hasattr(entity, 'state'):
                return False
            
            # product type != 뒤의 조건 추출
            attr_condition = condition.split('product type !=', 1)[1].strip()
            
            # transit 상태 체크 (반대)
            if attr_condition == 'transit':
                return entity.state != 'transit'
            
            # normal 상태 체크 (반대)
            if attr_condition == 'normal':
                return entity.state != 'normal'
            
            # 단일 속성 체크 (반대)
            return attr_condition not in entity.custom_attributes
        
        # product type = 조건 체크
        elif 'product type =' in condition and entity:
            if not hasattr(entity, 'custom_attributes') or not hasattr(entity, 'state'):
                return False
            
            # product type = 뒤의 조건 추출
            attr_condition = condition.split('product type =', 1)[1].strip()
            
            # transit 상태 체크
            if attr_condition == 'transit':
                return entity.state == 'transit'
            
            # normal 상태 체크
            if attr_condition == 'normal':
                return entity.state == 'normal'
            
            # AND 조건 처리
            if ' and ' in attr_condition:
                conditions = [cond.strip() for cond in attr_condition.split(' and ')]
                # 모든 속성이 있어야 true
                for cond in conditions:
                    if cond == 'transit':
                        if entity.state != 'transit':
                            return False
                    elif cond not in entity.custom_attributes:
                        return False
                return True
            
            # OR 조건 처리
            elif ' or ' in attr_condition:
                conditions = [cond.strip() for cond in attr_condition.split(' or ')]
                # 하나라도 있으면 true
                for cond in conditions:
                    if cond == 'transit':
                        if entity.state == 'transit':
                            return True
                    elif cond in entity.custom_attributes:
                        return True
                return False
            
            # 단일 속성 체크
            else:
                return attr_condition in entity.custom_attributes
        
        # 일반 AND 조건 체크 (신호와 product type 혼합 지원)
        elif ' and ' in condition:
            conditions = condition.split(' and ')
            for cond in conditions:
                cond = cond.strip()
                # product type 조건 확인
                if 'product type' in cond:
                    # 재귀적으로 execute_if 호출하여 product type 조건 평가
                    if not self.execute_if(env, cond, entity):
                        return False
                # 일반 신호 조건
                elif ' = ' in cond:
                    if not self._evaluate_single_signal_condition(cond):
                        return False
                else:
                    # 인식할 수 없는 조건
                    return False
            return True
        
        # 일반 신호 OR 조건 체크 (product type 조건 포함)
        elif ' or ' in condition:
            conditions = condition.split(' or ')
            for cond in conditions:
                cond = cond.strip()
                # product type 조건 확인
                if 'product type' in cond:
                    # 재귀적으로 execute_if 호출하여 product type 조건 평가
                    if self.execute_if(env, cond, entity):
                        return True
                # 일반 신호 조건
                elif ' = ' in cond:
                    if self._evaluate_single_signal_condition(cond):
                        return True
            return False
        
        # 기존 신호 체크 로직 (단일 조건)
        elif ' = ' in condition:
            return self._evaluate_single_signal_condition(condition)
        
        return False
    
    def execute_jump(self, env: simpy.Environment, target_line: str) -> int:
        """jump to 1 형태의 명령 실행"""
        try:
            line_number = int(target_line.strip())
            return line_number - 1  # 0-based 인덱스로 변환
        except ValueError:
            return -1
    
    def execute_product_type_add(self, env: simpy.Environment, params_str: str, entity: Any) -> Generator:
        """product type += attributes(color) 형태의 명령 실행"""
        if not hasattr(entity, 'custom_attributes') or not hasattr(entity, 'color'):
            yield env.timeout(0)
            return
        
        # transit 상태의 엔티티는 속성 변경 무시
        if hasattr(entity, 'state') and entity.state == 'transit':
            logger.debug(f"Entity {entity.id} is in transit, ignoring product type change")
            yield env.timeout(0)
            return
        
        # 색상 파싱 (괄호 안의 내용)
        color = None
        if '(' in params_str and ')' in params_str:
            color_match = re.search(r'\(([^)]+)\)', params_str)
            if color_match:
                color = color_match.group(1).strip()
                # 색상 부분 제거
                params_str = params_str[:params_str.index('(')].strip()
        
        # 속성 파싱 (쉼표로 구분)
        if params_str:
            attributes = [attr.strip() for attr in params_str.split(',') if attr.strip()]
            for attr in attributes:
                entity.custom_attributes.add(attr)
        
        # 색상 설정
        if color:
            entity.color = color
        
        
        yield env.timeout(0)
    
    def execute_product_type_remove(self, env: simpy.Environment, params_str: str, entity: Any) -> Generator:
        """product type -= attributes 형태의 명령 실행"""
        if not hasattr(entity, 'custom_attributes'):
            yield env.timeout(0)
            return
        
        # transit 상태의 엔티티는 속성 변경 무시
        if hasattr(entity, 'state') and entity.state == 'transit':
            logger.debug(f"Entity {entity.id} is in transit, ignoring product type change")
            yield env.timeout(0)
            return
        
        # 색상 초기화 요청 확인
        if '(' in params_str and ')' in params_str:
            color_match = re.search(r'\(([^)]+)\)', params_str)
            if color_match and color_match.group(1).strip() == 'default':
                entity.color = None
                # 색상 부분 제거
                params_str = params_str[:params_str.index('(')].strip()
        
        # 속성 제거 (쉼표로 구분)
        if params_str:
            attributes = [attr.strip() for attr in params_str.split(',') if attr.strip()]
            for attr in attributes:
                entity.custom_attributes.discard(attr)
        
        yield env.timeout(0)
    
    def execute_log(self, env: simpy.Environment, message: str, block_name: str = None) -> Generator:
        """log 명령어 실행"""
        timestamp = f"{env.now:.1f}"
        log_entry = f"[{timestamp}s] {f'[{block_name}]' if block_name else ''} {message}"
        
        # 백엔드 로그
        logger.info(f"시뮬레이션 로그: {log_entry}")
        
        # 프론트엔드로 전송할 로그 저장
        if hasattr(self, 'simulation_logs'):
            self.simulation_logs.append({
                'time': env.now,
                'block': block_name,
                'message': message
            })
        
        yield env.timeout(0)
    
    def execute_create(self, env: simpy.Environment, params: str, block) -> Generator:
        """create entity 명령어 실행 - 엔티티 생성"""
        if hasattr(block, 'create_entity'):
            entity = yield from block.create_entity(env)
            if entity:
                logger.info(f"[{env.now:.1f}s] Block {block.name} created entity {entity.id}")
                return ('created_entity', entity)  # 생성된 엔티티 반환
            else:
                return None
        else:
            yield env.timeout(0)
            return None
    
    def execute_dispose(self, env: simpy.Environment, entity: Any, block) -> Generator:
        """dispose entity 명령어 실행 - 엔티티 제거"""
        if entity and hasattr(block, 'dispose_entity'):
            yield from block.dispose_entity(env, entity)
            logger.info(f"[{env.now:.1f}s] Block {block.name} disposed entity {entity.id}")
        yield env.timeout(0)
    
    def parse_script_line(self, line: str) -> tuple:
        """스크립트 라인을 파싱하여 명령어와 파라미터를 반환"""
        line = line.strip()
        
        # 빈 줄이나 주석
        if not line or line.startswith('//'):
            return None, None
        
        # delay 명령
        if line.startswith('delay '):
            return 'delay', line[6:].strip()
        
        # 신호 설정 (신호명 = 값)
        if ' = ' in line and not line.startswith('if ') and not line.startswith('wait '):
            parts = line.split(' = ', 1)
            signal_name = parts[0].strip()
            value = parts[1].strip()
            return 'signal_set', {'signal_name': signal_name, 'value': value}
        
        # wait 명령
        if line.startswith('wait '):
            condition = line[5:].strip()
            return 'wait', condition
        
        # go from 명령 (새로운 형식)
        if line.startswith('go from '):
            # go from R to 공정1.L,3 형태 파싱
            go_from_pattern = r'^go\s+from\s+([^\s]+)\s+to\s+(.+)$'
            import re
            match = re.match(go_from_pattern, line, re.IGNORECASE)
            if match:
                from_connector = match.group(1).strip()
                to_target = match.group(2).strip()
                # go from은 go to와 동일하게 처리 (출발 커넥터 정보는 프론트엔드에서 연결선 생성용)
                return 'go_to', to_target
            else:
                # 파싱 실패 시 기본 처리
                target = line[8:].strip()  # "go from " 제거
                return 'go_to', target
        
        # go to 명령 (기존 형식)
        if line.startswith('go to '):
            target = line[6:].strip()
            return 'go_to', target
        
        # if 명령
        if line.startswith('if '):
            condition = line[3:].strip()
            return 'if', condition
        
        # jump 명령
        if line.startswith('jump to '):
            target = line[8:].strip()
            return 'jump', target
        
        # product type += 명령
        if 'product type +=' in line:
            params = line.split('product type +=', 1)[1].strip()
            return 'product_type_add', params
        
        # product type -= 명령
        if 'product type -=' in line:
            params = line.split('product type -=', 1)[1].strip()
            return 'product_type_remove', params
        
        # log 명령
        if line.startswith('log '):
            message = line[4:].strip()
            # 따옴표 제거
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            return 'log', message
        
        # create entity 명령
        if line.strip() == 'create entity':
            return 'create', ''
        
        # dispose entity 명령
        if line.strip() == 'dispose entity':
            return 'dispose', ''
        
        # force execution 명령
        if line.strip() == 'force execution':
            return 'force_execution', ''
        
        return None, None
    
    def execute_script_line(self, env: simpy.Environment, line: str, entity: Any, block_name: str = None, block: Any = None) -> Generator:
        """단일 스크립트 라인 실행"""
        command, params = self.parse_script_line(line)
        logger.debug(f"Parsed command: {command}, params: {params}")
        
        if command == 'delay':
            yield from self.execute_delay(env, params)
        
        elif command == 'signal_set':
            yield from self.execute_signal_set(env, params['signal_name'], params['value'])
        
        elif command == 'wait':
            yield from self.execute_wait(env, params, entity)
        
        elif command == 'go_to':
            yield from self.execute_go_to(env, params, entity)
            return 'movement'  # 이동 신호
        
        elif command == 'if':
            condition_result = self.execute_if(env, params, entity)
            return ('if', condition_result)
        
        elif command == 'jump':
            target_line = self.execute_jump(env, params)
            return ('jump', target_line)
        
        elif command == 'product_type_add':
            yield from self.execute_product_type_add(env, params, entity)
        
        elif command == 'product_type_remove':
            yield from self.execute_product_type_remove(env, params, entity)
        
        elif command == 'log':
            # 블록 이름은 매개변수로 전달받거나 엔티티에서 가져옴
            if block_name is None and entity:
                block_name = getattr(entity, 'current_block_name', None)
            yield from self.execute_log(env, params, block_name)
        
        elif command == 'create':
            logger.debug(f"Executing create command, block: {block}")
            if block:
                result = yield from self.execute_create(env, params, block)
                logger.debug(f"Create command result: {result}")
                if result and isinstance(result, tuple) and result[0] == 'created_entity':
                    logger.info(f"Returning created entity result: {result}")
                    return result  # 생성된 엔티티 정보 반환
                else:
                    logger.debug(f"Create command returned None or invalid result")
                    return None
            else:
                logger.debug(f"No block provided for create command")
                yield env.timeout(0)
                return None
        
        elif command == 'dispose':
            if block:
                yield from self.execute_dispose(env, entity, block)
            else:
                yield env.timeout(0)
        
        elif command == 'force_execution':
            # force execution은 아무것도 하지 않음
            yield env.timeout(0)
            return 'continue'
        
        else:
            logger.warning(f"Unknown command: {command}")
            return 'continue'