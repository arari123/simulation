import re
import random
from .utils import parse_delay_value
from .state_manager import signals, set_signal, wait_for_signal, block_pipes

def execute_script_line(env, line, entity, act_log, out_pipe_connectors=None):
    """
    단일 스크립트 라인을 실행합니다.
    
    Args:
        env: SimPy 환경
        line: 실행할 스크립트 라인
        entity: 현재 엔티티
        act_log: 액션 로그 리스트
        out_pipe_connectors: 출력 파이프 커넥터 딕셔너리
    
    Returns:
        실행 결과에 따른 제어 정보 (continue, break, jump 등)
    """
    line = line.strip()
    
    # 빈 줄이나 주석은 건너뛰기
    if not line or line.startswith('//'):
        return 'continue'
    
    # delay 명령어 처리
    if line.startswith('delay '):
        delay_str = line[6:].strip()  # 'delay ' 제거
        try:
            delay_time = parse_delay_value(delay_str)
            yield env.timeout(delay_time)
            act_log.append(f"{env.now:.2f}: Delayed for {delay_time:.2f} seconds")
            print(f"{env.now:.2f}: Entity {entity.id} delayed for {delay_time:.2f} seconds")
        except ValueError as e:
            print(f"{env.now:.2f}: Error in delay command: {e}")
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
                set_signal(signal_name, value, env)
                act_log.append(f"{env.now:.2f}: Set signal '{signal_name}' to {value}")
                print(f"{env.now:.2f}: Entity {entity.id} set signal '{signal_name}' to {value}")
            else:
                print(f"{env.now:.2f}: Invalid signal value: {value_str}")
                act_log.append(f"{env.now:.2f}: Invalid signal value: {value_str}")
        return 'continue'
    
    # 신호 대기 명령어 처리 (wait signal_name = value)
    if line.startswith('wait '):
        wait_part = line[5:].strip()  # 'wait ' 제거
        if ' = ' in wait_part:
            parts = wait_part.split(' = ', 1)
            if len(parts) == 2:
                signal_name = parts[0].strip()
                value_str = parts[1].strip()
                
                if value_str.lower() in ['true', 'false']:
                    expected_value = value_str.lower() == 'true'
                    
                    print(f"{env.now:.2f}: Entity {entity.id} waiting for signal '{signal_name}' = {expected_value}")
                    act_log.append(f"{env.now:.2f}: Waiting for signal '{signal_name}' = {expected_value}")
                    
                    # 신호 대기
                    yield wait_for_signal(signal_name, expected_value, env)
                    
                    print(f"{env.now:.2f}: Entity {entity.id} signal wait completed for '{signal_name}' = {expected_value}")
                    act_log.append(f"{env.now:.2f}: Signal wait completed for '{signal_name}' = {expected_value}")
                else:
                    print(f"{env.now:.2f}: Invalid signal value in wait: {value_str}")
                    act_log.append(f"{env.now:.2f}: Invalid signal value in wait: {value_str}")
        return 'continue'
    
    # go to 명령어 처리
    if line.startswith('go to '):
        target = line[6:].strip()  # 'go to ' 제거
        
        # 딜레이가 포함된 경우 처리
        delay_time = 0
        if ',' in target:
            parts = target.split(',', 1)
            target = parts[0].strip()
            delay_str = parts[1].strip()
            try:
                delay_time = parse_delay_value(delay_str)
            except ValueError as e:
                print(f"{env.now:.2f}: Error parsing delay in go to: {e}")
                act_log.append(f"{env.now:.2f}: Error parsing delay in go to: {e}")
        
        # self.블록명 또는 self.블록ID 처리
        if target.startswith('self.'):
            target_name = target[5:].strip()  # 'self.' 제거
            
            # 딜레이 실행
            if delay_time > 0:
                yield env.timeout(delay_time)
                act_log.append(f"{env.now:.2f}: Delayed for {delay_time:.2f} seconds before moving")
                print(f"{env.now:.2f}: Entity {entity.id} delayed for {delay_time:.2f} seconds before moving")
            
            # 커넥터에서 같은 블록 내부로 이동 - 블록 프로세스로 전달
            act_log.append(f"{env.now:.2f}: Moving to same block's main process: {target_name}")
            print(f"{env.now:.2f}: Entity {entity.id} moving to same block's main process: {target_name}")
            return 'continue'  # 커넥터 액션 완료, 블록 액션으로 진행
        
        # 다른 블록.커넥터 형식 처리
        if '.' in target:
            block_name, connector_name = target.split('.', 1)
            block_name = block_name.strip()
            connector_name = connector_name.strip()
            
            # 딜레이 실행
            if delay_time > 0:
                yield env.timeout(delay_time)
                act_log.append(f"{env.now:.2f}: Delayed for {delay_time:.2f} seconds before moving")
                print(f"{env.now:.2f}: Entity {entity.id} delayed for {delay_time:.2f} seconds before moving")
            
            # 해당 블록의 특정 커넥터로 이동
            if out_pipe_connectors:
                moved = False
                for connector_id, block_info in out_pipe_connectors.items():
                    if isinstance(block_info, dict):
                        if (block_info.get('block_name') == block_name and 
                            block_info.get('connector_name') == connector_name):
                            
                            if connector_id in block_pipes:
                                pipe = block_pipes[connector_id]
                                yield pipe.put(entity)
                                act_log.append(f"{env.now:.2f}: Moved to {block_name}.{connector_name}")
                                print(f"{env.now:.2f}: Entity {entity.id} moved to {block_name}.{connector_name}")
                                moved = True
                                break
                
                if not moved:
                    print(f"{env.now:.2f}: No route found to {block_name}.{connector_name}")
                    act_log.append(f"{env.now:.2f}: No route found to {block_name}.{connector_name}")
            
            return 'break'  # 블록 이동 시 현재 프로세스 종료
        
        return 'continue'
    
    # jump to 명령어 처리
    if line.startswith('jump to '):
        target = line[8:].strip()  # 'jump to ' 제거
        act_log.append(f"{env.now:.2f}: Jump to {target}")
        print(f"{env.now:.2f}: Entity {entity.id} jumping to {target}")
        return ('jump', target)
    
    # if 조건문 처리 (기본적인 구현)
    if line.startswith('if '):
        condition = line[3:].strip()  # 'if ' 제거
        
        if ' = ' in condition:
            parts = condition.split(' = ', 1)
            if len(parts) == 2:
                signal_name = parts[0].strip()
                value_str = parts[1].strip()
                
                if value_str.lower() in ['true', 'false']:
                    expected_value = value_str.lower() == 'true'
                    
                    if signal_name in signals:
                        current_value = signals[signal_name].get('value', False)
                        if current_value == expected_value:
                            act_log.append(f"{env.now:.2f}: Condition '{condition}' is true")
                            print(f"{env.now:.2f}: Entity {entity.id} condition '{condition}' is true")
                            return 'continue'  # 조건이 참이면 계속 실행
                        else:
                            act_log.append(f"{env.now:.2f}: Condition '{condition}' is false")
                            print(f"{env.now:.2f}: Entity {entity.id} condition '{condition}' is false")
                            return 'skip_block'  # 조건이 거짓이면 블록 스킵
                    else:
                        print(f"{env.now:.2f}: Signal '{signal_name}' not found")
                        act_log.append(f"{env.now:.2f}: Signal '{signal_name}' not found")
                        return 'skip_block'
        
        return 'continue'
    
    # 인식되지 않는 명령어
    print(f"{env.now:.2f}: Unknown command: {line}")
    act_log.append(f"{env.now:.2f}: Unknown command: {line}")
    return 'continue'

def execute_conditional_branch_script(env, script, entity, act_log, out_pipe_connectors=None):
    """
    조건부 분기 스크립트를 실행합니다.
    
    Args:
        env: SimPy 환경
        script: 실행할 스크립트 전체
        entity: 현재 엔티티
        act_log: 액션 로그 리스트
        out_pipe_connectors: 출력 파이프 커넥터 딕셔너리
    """
    lines = script.split('\n')
    
    for line in lines:
        result = yield from execute_script_line(env, line, entity, act_log, out_pipe_connectors)
        
        if isinstance(result, tuple) and result[0] == 'jump':
            # jump 명령어 처리
            target = result[1]
            # 여기서는 단순히 로그만 남기고 실제 점프는 구현하지 않음
            act_log.append(f"{env.now:.2f}: Jump command to {target} (not implemented)")
            continue
        elif result == 'break':
            # 블록 이동 등으로 인한 프로세스 종료
            break
        elif result == 'skip_block':
            # 조건이 거짓인 경우 나머지 스킵
            break 