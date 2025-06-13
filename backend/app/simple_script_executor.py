"""
단순화된 스크립트 실행기
각 스크립트 명령어를 독립적인 함수로 처리합니다.
"""
import simpy
import re
import random
import logging
from typing import Generator, Dict, Any, Optional, List

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
    
    def __init__(self, signal_manager=None, integer_manager=None, variable_accessor=None, debug_manager=None):
        self.signal_manager = signal_manager
        self.integer_manager = integer_manager
        self.variable_accessor = variable_accessor
        self.debug_manager = debug_manager
        self.simulation_logs = []  # 시뮬레이션 로그 저장
        self.command_functions = {
            'delay': self.execute_delay,
            'signal_set': self.execute_signal_set,
            'signal_wait': self.execute_signal_wait,
            'if': self.execute_if,
            'jump': self.execute_jump,
            'wait': self.execute_wait,
            'product_type_add': self.execute_product_type_add,
            'product_type_remove': self.execute_product_type_remove,
            'log': self.execute_log,
            'create': self.execute_create,
            'dispose': self.execute_dispose,
            'int_operation': self.execute_int_operation,
            'block_status': self.execute_block_status
        }
        
        # 성능 최적화: 정규식 사전 컴파일
        self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """정규식 패턴 사전 컴파일"""
        # 자주 사용되는 정규식 패턴들을 미리 컴파일
        self.re_product_type_index = re.compile(r'^product\s+type\((\d+)\)\s*=\s*(.+)$')
        self.re_product_type_index_not = re.compile(r'^product\s+type\((\d+)\)\s*!=\s*(.+)$')
        self.re_int_operation = re.compile(r'^int\s+([\w가-힣]+)\s*([\+\-\*\/]?=)\s*(.+)$')
        self.re_go_command = re.compile(r'^go\s+([^\s]+)\s+to\s+([^(]+)(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$', re.IGNORECASE)
        self.re_variable_pattern = re.compile(r'\{([^}]+)\}')
        self.re_entity_index = re.compile(r'entity\((\d+)\)\.(.+)')
        self.re_color_extract = re.compile(r'\(([^)]+)\)')
    
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
            # logger.debug(f"Signal '{signal_name}' current value: {current_value}, expected: {expected_value}")
            return current_value == expected_value
        
        return False
    
    def _evaluate_integer_comparison(self, condition: str) -> bool:
        """정수 변수 비교 조건 평가"""
        if not self.integer_manager:
            return False
        
        # 지원하는 연산자들을 긴 것부터 확인 (>= 가 > 보다 먼저)
        operators = ['>=', '<=', '!=', '=', '>', '<']
        
        for op in operators:
            if f' {op} ' in condition:
                parts = condition.split(f' {op} ', 1)
                if len(parts) != 2:
                    continue
                
                var_name = parts[0].strip()
                right_side = parts[1].strip()
                
                # 왼쪽이 정수 변수인지 확인
                if not self.integer_manager.has_variable(var_name):
                    continue
                
                # 오른쪽 값 평가
                try:
                    # 숫자 리터럴인 경우
                    if right_side.lstrip('-').isdigit():
                        compare_value = int(right_side)
                    # 다른 변수 참조인 경우
                    elif self.variable_accessor and self.variable_accessor.has_variable(right_side):
                        val = self.variable_accessor.get_value(right_side)
                        if isinstance(val, int):
                            compare_value = val
                        else:
                            continue
                    else:
                        continue
                    
                    # 비교 수행
                    return self.integer_manager.compare(var_name, op, compare_value)
                    
                except (ValueError, TypeError):
                    continue
        
        return False
    
    def execute_wait(self, env: simpy.Environment, condition: str, entity: Any = None) -> Generator:
        """wait 명령 실행 (신호 및 엔티티 속성 대기 지원, OR/AND 조건 지원)"""
        # wait 조건이 이미 만족되는지 먼저 확인
        if self._evaluate_if_condition(condition, entity):
            yield env.timeout(0)
            return
        
        # 조건이 만족될 때까지 대기
        while True:
            yield env.timeout(0.01)
            if self._evaluate_if_condition(condition, entity):
                return
    
    
    def execute_go_move(self, env: simpy.Environment, params: Dict, entity: Any, block: Any) -> Generator:
        """새로운 go 명령 실행 (go R to 공정1.L(0,3) 형식)"""
        from_connector = params.get('from_connector')
        to_target = params.get('to_target')
        entity_index = params.get('entity_index', 0)
        delay = params.get('delay', None)
        
        # 디버그 로그 제거 - 성능 향상
        
        # 블록에서 해당 인덱스의 엔티티 가져오기
        if block and hasattr(block, 'entities_in_block'):
            if 0 <= entity_index < len(block.entities_in_block):
                target_entity = block.entities_in_block[entity_index]
                
                # 이미 transit 상태인 엔티티는 이동 명령 무시
                if hasattr(target_entity, 'state') and target_entity.state == 'transit':
                    logger.warning(f"Entity {target_entity.id} at index {entity_index} is already in transit")
                    yield env.timeout(0)
                    return
                
                # 타겟 파싱
                if '.' in to_target:
                    block_name, connector_name = to_target.split('.', 1)
                    target_entity.target_block = block_name.strip()
                    target_entity.target_connector = connector_name.strip()
                else:
                    target_entity.target_block = to_target.strip()
                    target_entity.target_connector = None
                
                # 엔티티 상태를 transit으로 변경
                if hasattr(target_entity, 'state'):
                    target_entity.state = "transit"
                
                # 이동 시작 로그
                logger.info(f"[{env.now:.1f}s] Entity {target_entity.id} at index {entity_index} moving from {from_connector} to {to_target}")
                
                # 딜레이 실행
                if delay:
                    delay_time = parse_delay_value(delay)
                    if delay_time > 0:
                        yield env.timeout(delay_time)
                
                # 엔진 참조가 있으면 직접 이동 처리
                if block and hasattr(block, 'engine_ref') and block.engine_ref:
                    engine_ref = block.engine_ref
                    
                    # 출력 커넥터로 연결된 블록 찾기
                    target_block_id = block.output_connections.get(target_entity.target_connector, target_entity.target_block)
                    
                    # 블록 이름을 ID로 변환
                    if target_block_id not in engine_ref.blocks:
                        resolved_id = engine_ref.get_block_id_by_name(target_block_id)
                        if resolved_id:
                            target_block_id = resolved_id
                    
                    if target_block_id and target_block_id in engine_ref.blocks:
                        target_block = engine_ref.blocks[target_block_id]
                        # 대상 블록이 엔티티를 받을 수 있는지 확인
                        if target_block.can_accept_entity():
                            block.remove_entity(target_entity)
                            yield from engine_ref.move_entity_to_block(env, target_entity, target_block_id)
                            target_entity.movement_completed = True
                            target_entity.movement_requested = False
                            logger.info(f"[{env.now:.1f}s] Entity {target_entity.id} movement completed to {to_target}")
                        else:
                            # 용량 초과로 이동 실패
                            block.add_capacity_warning(env, target_block.name, target_entity.id)
                            target_entity.movement_failed = True
                            target_entity.movement_requested = False
                            target_entity.state = "normal"  # transit 상태 해제
                            logger.warning(f"[{env.now:.1f}s] Entity {target_entity.id} movement failed to {to_target} (capacity exceeded)")
                    else:
                        # 대상 블록을 찾을 수 없음
                        target_entity.movement_failed = True
                        target_entity.movement_requested = False
                        target_entity.state = "normal"  # transit 상태 해제
                        logger.warning(f"[{env.now:.1f}s] Target block not found for entity {target_entity.id}")
                else:
                    # 엔진 참조가 없는 경우 기존 방식 (비동기 이동)
                    target_entity.movement_requested = True
                    target_entity.movement_completed = False
                    target_entity.movement_failed = False
                    logger.info(f"[{env.now:.1f}s] Entity {target_entity.id} at index {entity_index} movement requested (async)")
            else:
                logger.warning(f"Invalid entity index: {entity_index}. Block has {len(block.entities_in_block)} entities.")
        
        yield env.timeout(0)
    
    def execute_if(self, env: simpy.Environment, condition: str, entity: Any = None, block: Any = None) -> bool:
        """if 조건문 평가 (엔티티 속성 체크 지원)"""
        # 디버그 매니저가 있으면 조건 평가 결과를 컨텍스트에 추가
        result = self._evaluate_if_condition(condition, entity, block)
        # logger.debug(f"IF condition '{condition}' evaluated to: {result}")
        if self.debug_manager and hasattr(self, '_current_if_depth'):
            # if 문 진입 시 컨텍스트 추가 (execute_script에서 관리)
            pass
        return result
        
    def _evaluate_if_condition(self, condition: str, entity: Any = None, block: Any = None) -> bool:
        """실제 if 조건 평가 로직"""
        # product type(index) != value 형식 체크 (새로운 문법 - not equal)
        product_index_not_match = self.re_product_type_index_not.match(condition.strip())
        if product_index_not_match:
            index = int(product_index_not_match.group(1))
            value = product_index_not_match.group(2).strip()
            
            # 블록에서 해당 인덱스의 엔티티 가져오기
            if block and hasattr(block, 'entities_in_block'):
                if 0 <= index < len(block.entities_in_block):
                    target_entity = block.entities_in_block[index]
                    
                    # transit/normal 상태 체크 (반대)
                    if value == 'transit':
                        return target_entity.state != 'transit'
                    elif value == 'normal':
                        return target_entity.state != 'normal'
                    # 사용자 정의 속성 체크 (반대)
                    else:
                        return value not in target_entity.custom_attributes
            return False
        
        # product type(index) = value 형식 체크 (새로운 문법)
        product_index_match = self.re_product_type_index.match(condition.strip())
        if product_index_match:
            index = int(product_index_match.group(1))
            value = product_index_match.group(2).strip()
            
            # 블록에서 해당 인덱스의 엔티티 가져오기
            if block and hasattr(block, 'entities_in_block'):
                if 0 <= index < len(block.entities_in_block):
                    target_entity = block.entities_in_block[index]
                    
                    # transit/normal 상태 체크
                    if value == 'transit':
                        return target_entity.state == 'transit'
                    elif value == 'normal':
                        return target_entity.state == 'normal'
                    # 사용자 정의 속성 체크
                    else:
                        return value in target_entity.custom_attributes
            return False
        
        # product type != 조건 체크 (not equal) - 기존 문법
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
        
        # 일반 AND 조건 체크 (신호, product type, 정수 비교 혼합 지원)
        elif ' and ' in condition:
            conditions = condition.split(' and ')
            for cond in conditions:
                cond = cond.strip()
                # product type 조건 확인
                if 'product type' in cond:
                    # 재귀적으로 _evaluate_if_condition 호출하여 product type 조건 평가
                    if not self._evaluate_if_condition(cond, entity, block):
                        return False
                # 정수 비교 조건 확인
                elif any(op in cond for op in ['>=', '<=', '!=', '>', '<']) or (self.integer_manager and ' = ' in cond and self.integer_manager.has_variable(cond.split(' = ')[0].strip())):
                    if not self._evaluate_integer_comparison(cond):
                        return False
                # 일반 신호 조건
                elif ' = ' in cond:
                    if not self._evaluate_single_signal_condition(cond):
                        return False
                else:
                    # 인식할 수 없는 조건
                    return False
            return True
        
        # 일반 신호 OR 조건 체크 (product type, 정수 비교 조건 포함)
        elif ' or ' in condition:
            conditions = condition.split(' or ')
            for cond in conditions:
                cond = cond.strip()
                # product type 조건 확인
                if 'product type' in cond:
                    # 재귀적으로 _evaluate_if_condition 호출하여 product type 조건 평가
                    if self._evaluate_if_condition(cond, entity, block):
                        return True
                # 정수 비교 조건 확인
                elif any(op in cond for op in ['>=', '<=', '!=', '>', '<']) or (self.integer_manager and ' = ' in cond and self.integer_manager.has_variable(cond.split(' = ')[0].strip())):
                    if self._evaluate_integer_comparison(cond):
                        return True
                # 일반 신호 조건
                elif ' = ' in cond:
                    if self._evaluate_single_signal_condition(cond):
                        return True
            return False
        
        # 정수 비교 조건 (단일)
        elif any(op in condition for op in ['>=', '<=', '!=', '>', '<']):
            return self._evaluate_integer_comparison(condition)
        
        # 기존 신호 체크 로직 (단일 조건) - 정수 변수 = 체크도 포함
        elif ' = ' in condition:
            # 정수 변수인 경우 먼저 확인
            parts = condition.split(' = ', 1)
            var_name = parts[0].strip()
            if self.integer_manager and self.integer_manager.has_variable(var_name):
                return self._evaluate_integer_comparison(condition)
            else:
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
            # logger.debug(f"Entity {entity.id} is in transit, ignoring product type change")
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
            # logger.debug(f"Entity {entity.id} is in transit, ignoring product type change")
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
        """log 명령어 실행 - 변수 치환 및 엔티티 속성 지원"""
        # 메시지에서 변수 참조 찾아서 치환
        interpolated_message = message
        
        # 엔티티 속성을 가져오기 위해 현재 엔티티 참조
        current_entity = None
        if hasattr(self, 'current_entity'):
            current_entity = self.current_entity
        
        # 현재 블록의 엔티티 목록 가져오기
        block_entities = []
        if hasattr(self, 'current_block') and self.current_block and hasattr(self.current_block, 'entities_in_block'):
            block_entities = self.current_block.entities_in_block
        
        # 간단한 변수 치환 - "text {variable}" 형식 지원
        if self.variable_accessor or current_entity or block_entities:
            # 정규식을 사용하여 {변수명} 패턴을 찾아 치환
            import re
            pattern = r'\{([^}]+)\}'
            
            def replace_variable(match):
                var_name = match.group(1)
                
                # 인덱스가 있는 엔티티 속성 확인 (entity(0).attributes, entity(1).color 등)
                entity_index_match = re.match(r'entity\((\d+)\)\.(.+)', var_name)
                if entity_index_match and block_entities:
                    index = int(entity_index_match.group(1))
                    attr_name = entity_index_match.group(2)
                    
                    if 0 <= index < len(block_entities):
                        target_entity = block_entities[index]
                        
                        if attr_name == 'attributes':
                            # 엔티티의 custom_attributes를 문자열로 변환
                            if hasattr(target_entity, 'custom_attributes'):
                                attrs = list(target_entity.custom_attributes)
                                return ','.join(attrs) if attrs else 'none'
                        elif attr_name == 'color':
                            # 엔티티의 색상
                            if hasattr(target_entity, 'color'):
                                color_value = target_entity.color if target_entity.color else 'default'
                                return color_value
                        elif attr_name == 'state':
                            # 엔티티의 상태
                            if hasattr(target_entity, 'state'):
                                return target_entity.state
                        elif attr_name == 'id':
                            # 엔티티 ID
                            if hasattr(target_entity, 'id'):
                                return target_entity.id
                    else:
                        logger.warning(f"[replace_variable] Entity index {index} out of range (0-{len(block_entities)-1})")
                    return match.group(0)  # 인덱스 범위 초과 또는 알 수 없는 속성
                
                # 기존 엔티티 속성 확인 (entity.attributes, entity.color 등)
                if current_entity and var_name.startswith('entity.'):
                    attr_name = var_name[7:]  # 'entity.' 제거
                    if attr_name == 'attributes':
                        # 엔티티의 custom_attributes를 문자열로 변환
                        if hasattr(current_entity, 'custom_attributes'):
                            attrs = list(current_entity.custom_attributes)
                            return ','.join(attrs) if attrs else 'none'
                    elif attr_name == 'color':
                        # 엔티티의 색상
                        if hasattr(current_entity, 'color'):
                            color_value = current_entity.color if current_entity.color else 'default'
                            return color_value
                    elif attr_name == 'state':
                        # 엔티티의 상태
                        if hasattr(current_entity, 'state'):
                            return current_entity.state
                    elif attr_name == 'id':
                        # 엔티티 ID
                        if hasattr(current_entity, 'id'):
                            return current_entity.id
                    return match.group(0)  # 알 수 없는 속성
                
                # 일반 변수 확인
                if self.variable_accessor:
                    value = self.variable_accessor.get_value(var_name)
                    return str(value) if value is not None else match.group(0)
                
                return match.group(0)
            
            interpolated_message = re.sub(pattern, replace_variable, message)
            
            # 중괄호 없이 변수명만 있는 경우도 처리 (기존 테스트 케이스 호환)
            words = interpolated_message.split()
            result_words = []
            for word in words:
                if self.variable_accessor and self.variable_accessor.has_variable(word):
                    value = self.variable_accessor.get_value(word)
                    result_words.append(str(value))
                else:
                    result_words.append(word)
            
            interpolated_message = ' '.join(result_words)
        
        timestamp = f"{env.now:.1f}"
        log_entry = f"[{timestamp}s] {f'[{block_name}]' if block_name else ''} {interpolated_message}"
        
        # 백엔드 로그
        logger.info(f"시뮬레이션 로그: {log_entry}")
        
        # 프론트엔드로 전송할 로그 저장
        if hasattr(self, 'simulation_logs'):
            self.simulation_logs.append({
                'time': env.now,
                'block': block_name,
                'message': interpolated_message
            })
        
        yield env.timeout(0)
    
    def execute_create(self, env: simpy.Environment, params: str, block) -> Generator:
        """create product 명령어 실행 - 엔티티 생성"""
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
        """dispose product 명령어 실행 - 엔티티 제거"""
        if entity and hasattr(block, 'dispose_entity'):
            yield from block.dispose_entity(env, entity)
            logger.info(f"[{env.now:.1f}s] Block {block.name} disposed entity {entity.id}")
        yield env.timeout(0)
    
    def execute_product_type_assign(self, env: simpy.Environment, params: Dict, block: Any) -> Generator:
        """product type(index) = value 명령 실행"""
        index = params['index']
        value = params['value']
        
        # 블록에서 해당 인덱스의 엔티티 가져오기
        if block and hasattr(block, 'entities_in_block'):
            if 0 <= index < len(block.entities_in_block):
                target_entity = block.entities_in_block[index]
                
                # transit 상태일 때는 속성 변경 불가
                if hasattr(target_entity, 'state') and target_entity.state == 'transit':
                    logger.warning(f"Cannot modify entity in transit state: {target_entity.id}")
                    yield env.timeout(0)
                    return
                
                # 사용자 정의 속성 설정
                if not hasattr(target_entity, 'custom_attributes'):
                    target_entity.custom_attributes = set()
                
                # 기존 속성 모두 제거하고 새 속성 설정
                target_entity.custom_attributes.clear()
                
                # 색상 설정 체크
                color_match = re.search(r'\(([^)]+)\)', value)
                if color_match:
                    color = color_match.group(1)
                    if color in ['gray', 'blue', 'green', 'red', 'black', 'white', 'default']:
                        target_entity.color = None if color == 'default' else color
                        # 색상 부분 제거
                        value = value[:value.index('(')].strip()
                
                # 속성 추가
                if value and value not in ['transit', 'normal']:
                    if ',' in value:
                        attributes = [attr.strip() for attr in value.split(',')]
                        target_entity.custom_attributes.update(attributes)
                    else:
                        target_entity.custom_attributes.add(value)
                
                logger.info(f"[{env.now:.1f}s] Entity {target_entity.id} at index {index}: attributes set to {target_entity.custom_attributes}")
            else:
                logger.warning(f"Invalid entity index: {index}. Block has {len(block.entities_in_block)} entities.")
        
        yield env.timeout(0)
    
    def get_simulation_logs(self) -> List[Dict[str, Any]]:
        """현재까지 수집된 시뮬레이션 로그 반환"""
        return self.simulation_logs.copy()
    
    def clear_logs(self):
        """로그 초기화 (선택적)"""
        self.simulation_logs = []
    
    def execute_int_operation(self, env: simpy.Environment, params: Dict[str, str]) -> Generator:
        """int 변수 산술 연산 실행"""
        if not self.integer_manager:
            logger.warning("Integer manager not available")
            yield env.timeout(0)
            return
        
        var_name = params['var_name']
        operator = params['operator']
        value_expr = params['value']
        
        try:
            # 값 파싱 - 다른 변수 참조 가능
            if value_expr.isdigit() or (value_expr.startswith('-') and value_expr[1:].isdigit()):
                operand = int(value_expr)
            else:
                # 다른 변수 참조
                if self.variable_accessor:
                    ref_value = self.variable_accessor.get_value(value_expr)
                    if ref_value is not None and isinstance(ref_value, int):
                        operand = ref_value
                    else:
                        logger.warning(f"Cannot resolve integer value for: {value_expr}")
                        yield env.timeout(0)
                        return
                else:
                    logger.warning(f"Variable accessor not available for: {value_expr}")
                    yield env.timeout(0)
                    return
            
            # 연산 수행
            old_value = self.integer_manager.get_variable(var_name, 0)
            new_value = self.integer_manager.perform_operation(var_name, operator, operand)
            logger.info(f"Integer variable '{var_name}' changed: {old_value} -> {new_value} (operator: {operator}, operand: {operand})")
            
        except Exception as e:
            logger.error(f"Error executing int operation: {e}")
        
        yield env.timeout(0)
    
    def execute_block_status(self, env: simpy.Environment, params: Dict[str, str], current_block: Any, engine_ref: Any = None) -> Generator:
        """블록 상태 설정 명령 실행"""
        if not params:
            yield env.timeout(0)
            return
            
        block_name = params.get('block_name', '')
        status_value = params.get('status', '')
        
        if not block_name or not status_value:
            logger.warning("Invalid block status command: missing block name or status value")
            yield env.timeout(0)
            return
        
        # 현재 블록을 찾거나 엔진에서 블록 찾기
        target_block = None
        
        # 현재 블록이 대상인 경우
        if current_block and hasattr(current_block, 'name') and current_block.name == block_name:
            target_block = current_block
        # 엔진에서 블록 찾기
        elif engine_ref and hasattr(engine_ref, 'blocks'):
            # 이름으로 블록 찾기
            for block_id, block in engine_ref.blocks.items():
                if block.name == block_name:
                    target_block = block
                    break
        
        if target_block and hasattr(target_block, 'set_status'):
            target_block.set_status(status_value)
            logger.info(f"[{env.now:.1f}s] Block '{block_name}' status set to: {status_value}")
        else:
            logger.warning(f"Block '{block_name}' not found or does not support status")
        
        yield env.timeout(0)
    
    def execute_block(self, env: simpy.Environment, target_block_name: str, engine_ref: Any) -> Generator:
        """execute 명령어로 지정된 블록의 스크립트 실행"""
        # 디버그 로그 제거 - 성능 향상
        
        if not engine_ref or not hasattr(engine_ref, 'blocks'):
            logger.warning(f"No engine reference to execute block '{target_block_name}'")
            yield env.timeout(0)
            return
        
        # 블록 이름으로 찾기
        target_block = None
        # 디버그 로그 제거 - 성능 향상
        for block_id, block in engine_ref.blocks.items():
            # 디버그 로그 제거 - 성능 향상
            if block.name == target_block_name:
                target_block = block
                # 디버그 로그 제거 - 성능 향상
                break
        
        if not target_block:
            logger.warning(f"Block '{target_block_name}' not found")
            yield env.timeout(0)
            return
        
        # 블록의 execute_script_by_command 메서드 호출
        if hasattr(target_block, 'execute_script_by_command'):
            entity_info = f"with entity {target_block.entities_in_block[0].id}" if target_block.entities_in_block else "without entity"
            logger.info(f"Executing block '{target_block_name}' via execute command ({entity_info})")
            # execute 명령은 비동기적으로 실행 (블로킹하지 않음)
            env.process(target_block.execute_script_by_command(env))
            logger.info(f"Block '{target_block_name}' execution started asynchronously")
        else:
            logger.warning(f"Block '{target_block_name}' does not support execute command")
        
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
        
        # int 변수 산술 연산 (int 변수명 += 5) - 한글 변수명 지원
        if line.startswith('int '):
            # int 변수명 연산자 값 형태 파싱
            int_match = re.match(r'^int\s+([\w가-힣]+)\s*([\+\-\*\/]?=)\s*(.+)$', line)
            if int_match:
                var_name = int_match.group(1)
                operator = int_match.group(2)
                value_expr = int_match.group(3).strip()
                return 'int_operation', {
                    'var_name': var_name,
                    'operator': operator,
                    'value': value_expr
                }
        
        # 블록 상태 설정 (블록이름.status = "값")
        if '.status = ' in line:
            parts = line.split('.status = ', 1)
            block_name = parts[0].strip()
            status_value = parts[1].strip()
            # 따옴표 제거
            if (status_value.startswith('"') and status_value.endswith('"')) or \
               (status_value.startswith("'") and status_value.endswith("'")):
                status_value = status_value[1:-1]
            return 'block_status', {'block_name': block_name, 'status': status_value}
        
        # product type(index) = value 형식을 먼저 체크 (신호 설정보다 우선)
        product_assign_match = re.match(r'^product\s+type\((\d+)\)\s*=\s*(.+)$', line)
        if product_assign_match:
            index = int(product_assign_match.group(1))
            value = product_assign_match.group(2).strip()
            # 디버그 로그 제거 - 성능 향상
            return 'product_type_assign', {'index': index, 'value': value}
        
        # 신호 설정 (신호명 = 값)
        if ' = ' in line and not line.startswith('if ') and not line.startswith('elif ') and not line.startswith('wait ') and not line.startswith('int '):
            parts = line.split(' = ', 1)
            signal_name = parts[0].strip()
            value = parts[1].strip()
            return 'signal_set', {'signal_name': signal_name, 'value': value}
        
        # wait 명령
        if line.startswith('wait '):
            condition = line[5:].strip()
            return 'wait', condition
        
        # go 명령 (새로운 형식: go R to 공정1.L(0,3))
        if line.startswith('go '):
            # go R to 공정1.L(0,3) 형태 파싱
            go_pattern = r'^go\s+([^\s]+)\s+to\s+([^(]+)(?:\((\d+)(?:,\s*(\d+(?:\.\d+)?))?\))?$'
            match = re.match(go_pattern, line, re.IGNORECASE)
            if match:
                from_connector = match.group(1).strip()
                to_target = match.group(2).strip()
                entity_index = match.group(3)  # 엔티티 인덱스 (옵션)
                delay = match.group(4)  # 딜레이 (옵션)
                
                # 파라미터 조합
                params = {
                    'from_connector': from_connector,
                    'to_target': to_target
                }
                
                if entity_index is not None:
                    params['entity_index'] = int(entity_index)
                else:
                    params['entity_index'] = 0  # 기본값은 0번 엔티티
                    
                if delay:
                    params['delay'] = delay
                    
                return 'go_move', params
            else:
                # 파싱 실패 시 에러
                return None, None
        
        # if 명령
        if line.startswith('if '):
            condition = line[3:].strip()
            return 'if', condition
        
        # elif 명령
        if line.startswith('elif '):
            condition = line[5:].strip()
            return 'elif', condition
        
        # else 명령
        if line.strip() == 'else':
            return 'else', None
        
        # jump 명령
        if line.startswith('jump to '):
            target = line[8:].strip()
            return 'jump', target
        
        # product type += 명령 (기존 문법 - 첫 번째 엔티티에 적용)
        if 'product type +=' in line:
            params = line.split('product type +=', 1)[1].strip()
            return 'product_type_add', params
        
        # product type -= 명령 (기존 문법 - 첫 번째 엔티티에 적용)
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
        
        # create product 명령
        if line.strip() == 'create product':
            return 'create', ''
        
        # dispose product 명령
        if line.strip() == 'dispose product':
            return 'dispose', ''
        
        # force execution 명령
        if line.strip() == 'force execution':
            return 'force_execution', ''
        
        # execute 명령
        if line.startswith('execute '):
            target_block = line[8:].strip()
            return 'execute', target_block
        
        return None, None
    
    def execute_script_line(self, env: simpy.Environment, line: str, entity: Any, block_name: str = None, block: Any = None) -> Generator:
        """단일 스크립트 라인 실행"""
        command, params = self.parse_script_line(line)
        # logger.debug(f"Parsed command: {command}, params: {params}")
        
        if command == 'delay':
            yield from self.execute_delay(env, params)
        
        elif command == 'signal_set':
            yield from self.execute_signal_set(env, params['signal_name'], params['value'])
        
        elif command == 'wait':
            yield from self.execute_wait(env, params, entity)
        
        elif command == 'go_move':
            # 새로운 go 명령 처리
            yield from self.execute_go_move(env, params, entity, block)
            return 'movement'  # 이동 신호
        
        elif command == 'if':
            condition_result = self.execute_if(env, params, entity, block)
            return ('if', condition_result)
        
        elif command == 'elif':
            condition_result = self.execute_if(env, params, entity, block)
            return ('elif', condition_result)
        
        elif command == 'else':
            return ('else', True)  # else는 항상 true
        
        elif command == 'jump':
            target_line = self.execute_jump(env, params)
            return ('jump', target_line)
        
        elif command == 'product_type_assign':
            yield from self.execute_product_type_assign(env, params, block)
        
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
            # logger.debug(f"Executing create command, block: {block}")
            if block:
                result = yield from self.execute_create(env, params, block)
                # logger.debug(f"Create command result: {result}")
                if result and isinstance(result, tuple) and result[0] == 'created_entity':
                    # 디버그 로그 제거 - 성능 향상
                    return result  # 생성된 엔티티 정보 반환
                else:
                    # logger.debug(f"Create command returned None or invalid result")
                    return None
            else:
                # logger.debug(f"No block provided for create command")
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
        
        elif command == 'int_operation':
            yield from self.execute_int_operation(env, params)
        
        elif command == 'block_status':
            # 블록 상태 설정 명령
            engine_ref = None
            if block and hasattr(block, 'engine_ref'):
                engine_ref = block.engine_ref
            yield from self.execute_block_status(env, params, block, engine_ref)
        
        elif command == 'execute':
            # execute 명령 실행
            # 디버그 로그 제거 - 성능 향상
            if block and hasattr(block, 'engine_ref') and block.engine_ref:
                yield from self.execute_block(env, params, block.engine_ref)
            else:
                logger.warning(f"Cannot execute block '{params}': no engine reference")
                yield env.timeout(0)
        
        else:
            logger.warning(f"Unknown command: {command}")
            return 'continue'
    
    def execute_script(self, script: str, entity: Any, env: simpy.Environment, block: Any = None) -> Generator:
        """스크립트 실행 (디버그 지원 포함)"""
        # 현재 엔티티를 저장하여 log 명령어에서 사용할 수 있도록 함
        self.current_entity = entity
        # 현재 블록을 저장하여 log 명령어에서 엔티티 목록에 접근할 수 있도록 함
        self.current_block = block
        
        lines = script.strip().split('\n')
        
        # 성능 최적화: 스크립트 라인 전처리
        processed_lines = []
        for line in lines:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip()) if line else 0
            processed_lines.append((line, stripped, indent))
        
        line_index = 0
        if_depth = 0
        if_stack = []  # 조건부 실행 스택
        current_if_block = None  # 현재 if/elif/else 블록 추적
        
        while line_index < len(processed_lines):
            original_line, line, current_indent = processed_lines[line_index]
            
            # 빈 줄이나 주석은 건너뛰기
            if not line or line.startswith('//'):
                line_index += 1
                continue
            
            # 디버그 브레이크포인트 체크 - 브레이크포인트가 있을 때만 체크
            if self.debug_manager and block and hasattr(self.debug_manager, 'has_breakpoints') and self.debug_manager.has_breakpoints(block.id):
                yield from self.debug_manager.check_breakpoint(
                    block.id, 
                    line_index + 1,  # 1-based line number
                    env
                )
            
            # if 블록 탈출 처리
            while if_stack and current_indent <= if_stack[-1][1]:
                if_stack.pop()
                if self.debug_manager:
                    self.debug_manager.pop_execution_context()
            
            # 현재 false 조건 내부인지 확인
            skip_line = False
            for _, _, condition_met in if_stack:
                if not condition_met:
                    skip_line = True
                    break
            
            if skip_line:
                line_index += 1
                continue
            
            # 실제 명령 실행
            result = yield from self.execute_script_line(env, original_line, entity, getattr(block, 'name', None), block)
            
            # if/elif/else 조건 처리
            if isinstance(result, tuple) and result[0] in ['if', 'elif', 'else']:
                cmd_type = result[0]
                condition_met = result[1]
                
                # if 명령인 경우 새로운 if 블록 시작
                if cmd_type == 'if':
                    current_if_block = {
                        'indent': current_indent,
                        'any_condition_met': condition_met,
                        'current_condition_met': condition_met
                    }
                    if_stack.append((line_index, current_indent, condition_met))
                    if self.debug_manager:
                        self.debug_manager.push_execution_context('if', condition_met)
                
                # elif 명령인 경우
                elif cmd_type == 'elif':
                    if current_if_block and current_indent == current_if_block['indent']:
                        # 이전 조건이 이미 만족되었으면 이 elif는 실행하지 않음
                        if current_if_block['any_condition_met']:
                            condition_met = False
                        current_if_block['current_condition_met'] = condition_met
                        if condition_met:
                            current_if_block['any_condition_met'] = True
                        
                        # 스택에서 이전 if/elif 제거하고 새로운 것 추가
                        if if_stack and if_stack[-1][1] == current_indent:
                            if_stack.pop()
                            if self.debug_manager:
                                self.debug_manager.pop_execution_context()
                        if_stack.append((line_index, current_indent, condition_met))
                        if self.debug_manager:
                            self.debug_manager.push_execution_context('elif', condition_met)
                    else:
                        logger.warning(f"elif without matching if at line {line_index + 1}")
                        condition_met = False
                
                # else 명령인 경우
                elif cmd_type == 'else':
                    if current_if_block and current_indent == current_if_block['indent']:
                        # 이전 조건이 하나라도 만족되었으면 else는 실행하지 않음
                        condition_met = not current_if_block['any_condition_met']
                        current_if_block['current_condition_met'] = condition_met
                        
                        # 스택에서 이전 if/elif 제거하고 새로운 것 추가
                        if if_stack and if_stack[-1][1] == current_indent:
                            if_stack.pop()
                            if self.debug_manager:
                                self.debug_manager.pop_execution_context()
                        if_stack.append((line_index, current_indent, condition_met))
                        if self.debug_manager:
                            self.debug_manager.push_execution_context('else', condition_met)
                    else:
                        logger.warning(f"else without matching if at line {line_index + 1}")
                        condition_met = False
                
                # 조건이 false면 블록 스킵
                if not condition_met:
                    # 다음 라인부터 들여쓰기가 끝날 때까지 스킵
                    line_index += 1
                    while line_index < len(processed_lines):
                        _, next_line_stripped, next_indent = processed_lines[line_index]
                        
                        # 빈 줄은 계속 진행
                        if not next_line_stripped:
                            line_index += 1
                            continue
                        
                        # 같은 들여쓰기의 elif/else인지 확인
                        next_cmd = None
                        if next_line_stripped.startswith('elif '):
                            next_cmd = 'elif'
                        elif next_line_stripped == 'else':
                            next_cmd = 'else'
                        
                        # 같은 들여쓰기의 elif/else면 거기서 멈춤
                        if next_cmd and next_indent == current_indent:
                            break
                        
                        # 들여쓰기가 현재 if보다 크면 스킵
                        if next_indent > current_indent:
                            line_index += 1
                        else:
                            # 들여쓰기가 같거나 작으면 if 블록 종료
                            current_if_block = None
                            break
                else:
                    line_index += 1
            
            # jump 처리
            elif isinstance(result, tuple) and result[0] == 'jump':
                target_line = result[1]
                if 0 <= target_line < len(processed_lines):
                    line_index = target_line
                else:
                    line_index += 1
            
            # 이동 명령 처리
            elif result == 'movement':
                # 이동 요청 후 스크립트 계속 실행
                line_index += 1
            
            # 엔티티 생성 처리
            elif isinstance(result, tuple) and result[0] == 'created_entity':
                # force execution에서 엔티티가 생성된 경우
                created_entity = result[1]
                # 생성된 엔티티를 current_entity로 설정하여 이후 log 명령에서 사용할 수 있도록 함
                self.current_entity = created_entity
                # force execution에서 생성된 엔티티는 이미 처리된 것으로 표시
                if block and hasattr(created_entity, 'processed_by_blocks'):
                    created_entity.processed_by_blocks.add(block.id)
                
                # force execution 중이면 계속 진행
                # (entity가 None이거나, 이미 생성된 엔티티가 있어도 계속 진행)
                line_index += 1
            
            else:
                line_index += 1
        
        # 스크립트 종료 시 남은 컨텍스트 정리
        if self.debug_manager:
            while if_stack:
                if_stack.pop()
                self.debug_manager.pop_execution_context()
        
        # Force execution 블록이면 yield로 다른 프로세스가 실행될 기회를 줌
        if block and hasattr(block, 'has_force_execution') and block.has_force_execution():
            yield env.timeout(0)