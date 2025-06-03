"""
스크립트 실행 모듈 (v2)
조건부 분기 스크립트를 실행하며 signal_manager를 통해 신호를 관리합니다.
"""
import re
from typing import Optional, Any, Dict, List, Generator, Tuple
from ..utils import parse_delay_value
import logging

logger = logging.getLogger(__name__)

class ScriptExecutor:
    """스크립트 실행을 담당하는 클래스"""
    
    def __init__(self, signal_manager, pipe_manager, entity_manager=None):
        self.signal_manager = signal_manager
        self.pipe_manager = pipe_manager
        self.entity_manager = entity_manager
        
    def execute_script_line(self, env, line: str, entity: Any, act_log: List[str], 
                           out_pipe_connectors: Optional[Dict] = None, from_block_name: str = 'Unknown') -> Generator:
        """단일 스크립트 라인을 실행합니다."""
        line = line.strip()
        
        # 빈 줄이나 주석은 건너뛰기
        if not line or line.startswith('//'):
            return 'continue'
        
        # delay 명령어 처리
        if line.startswith('delay '):
            delay_str = line[6:].strip()
            try:
                delay_time = parse_delay_value(delay_str)
                yield env.timeout(delay_time)
                act_log.append(f"{env.now:.2f}: Delayed for {delay_time:.2f} seconds")
                logger.debug(f"{env.now:.2f}: Entity {entity.id} delayed for {delay_time:.2f} seconds")
            except ValueError as e:
                logger.error(f"{env.now:.2f}: Error in delay command: {e}")
                act_log.append(f"{env.now:.2f}: Error in delay command: {e}")
            return 'continue'
        
        # 신호 설정 명령어 처리 (signal_name = value)
        if ' = ' in line and not line.startswith('if ') and not line.startswith('wait '):
            parts = line.split(' = ', 1)
            if len(parts) == 2:
                signal_name = parts[0].strip()
                value_str = parts[1].strip()
                
                if value_str.lower() in ['true', 'false']:
                    value = value_str.lower() == 'true'
                    self.signal_manager.set_signal(signal_name, value, env)
                    act_log.append(f"{env.now:.2f}: Set signal '{signal_name}' to {value}")
                    logger.debug(f"{env.now:.2f}: Entity {entity.id} set signal '{signal_name}' to {value}")
                else:
                    logger.error(f"{env.now:.2f}: Invalid signal value: {value_str}")
                    act_log.append(f"{env.now:.2f}: Invalid signal value: {value_str}")
            return 'continue'
        
        # 신호 대기 명령어 처리 (wait signal_name = value 또는 wait condition1 or condition2)
        if line.startswith('wait '):
            wait_part = line[5:].strip()
            
            # OR 조건 확인
            if ' or ' in wait_part.lower():
                # OR 조건 처리
                # OR로 분리 (대소문자 구분 없이)
                import re
                conditions = re.split(r'\s+or\s+', wait_part, flags=re.IGNORECASE)
                
                while True:
                    # 각 조건 확인
                    for condition in conditions:
                        condition = condition.strip()
                        if ' = ' in condition:
                            parts = condition.split(' = ', 1)
                            if len(parts) == 2:
                                signal_name = parts[0].strip()
                                value_str = parts[1].strip()
                                
                                if value_str.lower() in ['true', 'false']:
                                    expected_value = value_str.lower() == 'true'
                                    current_value = self.signal_manager.get_signal(signal_name, False)
                                    
                                    if current_value == expected_value:
                                        logger.debug(f"{env.now:.2f}: Entity {entity.id} OR condition met: '{condition}'")
                                        act_log.append(f"{env.now:.2f}: OR condition met: '{condition}'")
                                        return 'continue'
                    
                    # 모든 조건이 false면 잠시 대기
                    logger.debug(f"{env.now:.2f}: Entity {entity.id} waiting for OR conditions: {wait_part}")
                    act_log.append(f"{env.now:.2f}: Waiting for OR conditions: {wait_part}")
                    yield env.timeout(0.1)
                    
            elif ' = ' in wait_part:
                # 단일 조건 처리 (기존 코드)
                parts = wait_part.split(' = ', 1)
                if len(parts) == 2:
                    signal_name = parts[0].strip()
                    value_str = parts[1].strip()
                    
                    if value_str.lower() in ['true', 'false']:
                        expected_value = value_str.lower() == 'true'
                        
                        logger.debug(f"{env.now:.2f}: Entity {entity.id} waiting for signal '{signal_name}' = {expected_value}")
                        act_log.append(f"{env.now:.2f}: Waiting for signal '{signal_name}' = {expected_value}")
                        
                        # 신호 대기
                        yield from self.signal_manager.wait_for_signal(signal_name, expected_value, env)
                        
                        logger.debug(f"{env.now:.2f}: Entity {entity.id} signal wait completed for '{signal_name}' = {expected_value}")
                        act_log.append(f"{env.now:.2f}: Signal wait completed for '{signal_name}' = {expected_value}")
                    else:
                        logger.error(f"{env.now:.2f}: Invalid signal value in wait: {value_str}")
                        act_log.append(f"{env.now:.2f}: Invalid signal value in wait: {value_str}")
            return 'continue'
        
        # go to 명령어 처리
        if line.startswith('go to '):
            target = line[6:].strip()
            
            # 딜레이가 포함된 경우 처리
            delay_time = 0
            if ',' in target:
                parts = target.split(',', 1)
                target = parts[0].strip()
                delay_str = parts[1].strip()
                try:
                    delay_time = parse_delay_value(delay_str)
                except ValueError as e:
                    logger.error(f"{env.now:.2f}: Error parsing delay in go to: {e}")
                    act_log.append(f"{env.now:.2f}: Error parsing delay in go to: {e}")
            
            # 딜레이 실행
            if delay_time > 0:
                yield env.timeout(delay_time)
                act_log.append(f"{env.now:.2f}: Delayed for {delay_time:.2f} seconds before moving")
                logger.debug(f"{env.now:.2f}: Entity {entity.id} delayed for {delay_time:.2f} seconds before moving")
            
            # 다른 블록.커넥터 형식 처리
            if '.' in target:
                block_name, connector_name = target.split('.', 1)
                block_name = block_name.strip()
                connector_name = connector_name.strip()
                
                # 해당 블록의 특정 커넥터로 이동
                if out_pipe_connectors:
                    moved = False
                    for connector_id, pipe_info_list in out_pipe_connectors.items():
                        # pipe_info_list가 리스트인 경우 (여러 연결 지원)
                        if isinstance(pipe_info_list, list):
                            for block_info in pipe_info_list:
                                # 블록 이름 또는 블록 ID로 매칭
                                block_match = (block_info.get('block_name') == block_name or 
                                             str(block_info.get('block_id')) == block_name)
                                connector_match = (block_info.get('connector_name') == connector_name or
                                                 block_info.get('connector_id') == connector_name)
                                
                                if block_match and connector_match:
                                    pipe_id = block_info.get('pipe_id')
                                    if pipe_id:
                                        pipe = self.pipe_manager.get_pipe(pipe_id)
                                        if pipe:
                                            # Transit 상태 설정
                                            if self.entity_manager:
                                                self.entity_manager.set_entity_transit(entity, from_block_name, block_name)
                                            
                                            yield pipe.put(entity)
                                            act_log.append(f"{env.now:.2f}: Moved to {block_name}.{connector_name}")
                                            logger.info(f"{env.now:.2f}: Entity {entity.id} moved to {block_name}.{connector_name}")
                                            moved = True
                                            break
                        # 구 형식 지원 (단일 dict)
                        elif isinstance(pipe_info_list, dict):
                            block_info = pipe_info_list
                            # 블록 이름 또는 블록 ID로 매칭
                            block_match = (block_info.get('block_name') == block_name or 
                                         str(block_info.get('block_id')) == block_name)
                            connector_match = (block_info.get('connector_name') == connector_name or
                                             block_info.get('connector_id') == connector_name)
                            
                            if block_match and connector_match:
                                pipe_id = block_info.get('pipe_id')
                                if pipe_id:
                                    pipe = self.pipe_manager.get_pipe(pipe_id)
                                    if pipe:
                                        # Transit 상태 설정
                                        if self.entity_manager:
                                            self.entity_manager.set_entity_transit(entity, from_block_name, block_name)
                                        
                                        yield pipe.put(entity)
                                        act_log.append(f"{env.now:.2f}: Moved to {block_name}.{connector_name}")
                                        logger.info(f"{env.now:.2f}: Entity {entity.id} moved to {block_name}.{connector_name}")
                                        moved = True
                                        break
                        if moved:
                            break
                    
                    if not moved:
                        logger.error(f"{env.now:.2f}: No route found to {block_name}.{connector_name}")
                        logger.error(f"Available routes from out_pipe_connectors: {out_pipe_connectors}")
                        act_log.append(f"{env.now:.2f}: No route found to {block_name}.{connector_name}")
                
                return 'break'  # 블록 이동 시 현재 프로세스 종료
            
            return 'continue'
        
        # jump to 명령어 처리
        if line.startswith('jump to '):
            target = line[8:].strip()
            act_log.append(f"{env.now:.2f}: Jump to {target}")
            logger.debug(f"{env.now:.2f}: Entity {entity.id} jumping to {target}")
            return ('jump', target)
        
        # if 조건문 처리
        if line.startswith('if '):
            condition = line[3:].strip()
            
            if ' = ' in condition:
                parts = condition.split(' = ', 1)
                if len(parts) == 2:
                    signal_name = parts[0].strip()
                    value_str = parts[1].strip()
                    
                    if value_str.lower() in ['true', 'false']:
                        expected_value = value_str.lower() == 'true'
                        
                        # signal_manager를 통해 신호 값 확인
                        current_value = self.signal_manager.get_signal(signal_name, False)
                        
                        if current_value == expected_value:
                            act_log.append(f"{env.now:.2f}: Condition '{condition}' is true")
                            logger.debug(f"{env.now:.2f}: Entity {entity.id} condition '{condition}' is true")
                            return 'continue'  # 조건이 참이면 계속 실행
                        else:
                            act_log.append(f"{env.now:.2f}: Condition '{condition}' is false")
                            logger.debug(f"{env.now:.2f}: Entity {entity.id} condition '{condition}' is false")
                            return 'skip_block'  # 조건이 거짓이면 블록 스킵
            
            return 'continue'
        
        # 인식되지 않는 명령어
        logger.warning(f"{env.now:.2f}: Unknown command: {line}")
        act_log.append(f"{env.now:.2f}: Unknown command: {line}")
        return 'continue'
    
    def execute_conditional_branch_script(self, env, script: str, entity: Any, 
                                        act_log: List[str], out_pipe_connectors: Optional[Dict] = None, 
                                        from_block_name: str = 'Unknown') -> Generator:
        """조건부 분기 스크립트를 실행합니다."""
        lines = script.split('\n')
        current_line = 0
        skip_until_indent = -1
        max_iterations = 1000  # 무한 루프 방지
        iteration_count = 0
        
        while current_line < len(lines) and iteration_count < max_iterations:
            iteration_count += 1
            
            line = lines[current_line]
            stripped_line = line.lstrip()
            
            if not stripped_line:  # 빈 줄은 건너뛰기
                current_line += 1
                continue
                
            indent = len(line) - len(stripped_line)
            
            # 스킵 중인 경우 들여쓰기 확인
            if skip_until_indent >= 0:
                if indent <= skip_until_indent:
                    skip_until_indent = -1  # 스킵 종료
                else:
                    current_line += 1
                    continue  # 계속 스킵
            
            result = yield from self.execute_script_line(env, stripped_line, entity, act_log, out_pipe_connectors, from_block_name)
            
            if isinstance(result, tuple) and result[0] == 'jump':
                # jump 명령어 처리
                target = result[1]
                try:
                    target_line = int(target) - 1  # 1-based to 0-based
                    if 0 <= target_line < len(lines):
                        current_line = target_line  # 점프
                        continue
                except ValueError:
                    logger.error(f"Invalid jump target: {target}")
                    
            elif result == 'break':
                # 블록 이동 등으로 인한 프로세스 종료
                break
            elif result == 'skip_block':
                # 조건이 거짓인 경우 해당 블록 스킵
                skip_until_indent = indent
                
            current_line += 1
        
        if iteration_count >= max_iterations:
            logger.error(f"Conditional branch script exceeded maximum iterations ({max_iterations}) for entity {entity.id}")
            act_log.append(f"{env.now:.2f}: Script execution stopped - maximum iterations exceeded")