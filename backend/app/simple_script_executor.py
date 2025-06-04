"""
단순화된 스크립트 실행기
각 스크립트 명령어를 독립적인 함수로 처리합니다.
"""
import simpy
import re
import random
from typing import Generator, Dict, Any, Optional

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
        self.command_functions = {
            'delay': self.execute_delay,
            'signal_set': self.execute_signal_set,
            'signal_wait': self.execute_signal_wait,
            'go_to': self.execute_go_to,
            'if': self.execute_if,
            'jump': self.execute_jump,
            'wait': self.execute_wait
        }
    
    def execute_delay(self, env: simpy.Environment, delay_str: str) -> Generator:
        """delay 5 형태의 명령 실행"""
        delay_time = parse_delay_value(delay_str)
        yield env.timeout(delay_time)
    
    def execute_signal_set(self, env: simpy.Environment, signal_name: str, value: str) -> Generator:
        """신호명 = true 형태의 명령 실행"""
        bool_value = value.lower() == 'true'
        if self.signal_manager:
            self.signal_manager.set_signal(signal_name, bool_value)
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
    
    def execute_wait(self, env: simpy.Environment, condition: str) -> Generator:
        """wait 명령 실행 (wait 신호명 = true 형태, OR 조건 지원)"""
        # OR 조건 처리
        if ' or ' in condition:
            conditions = condition.split(' or ')
            while True:
                for cond in conditions:
                    cond = cond.strip()
                    if ' = ' in cond:
                        parts = cond.split(' = ', 1)
                        signal_name = parts[0].strip()
                        expected_value = parts[1].strip()
                        expected_bool = expected_value.lower() == 'true'
                        
                        if self.signal_manager:
                            current_value = self.signal_manager.get_signal(signal_name, False)
                            if current_value == expected_bool:
                                return  # 조건 중 하나라도 만족하면 종료
                
                yield env.timeout(0.01)  # 0.01초마다 체크
        # 단일 조건 처리
        elif ' = ' in condition:
            parts = condition.split(' = ', 1)
            signal_name = parts[0].strip()
            expected_value = parts[1].strip()
            yield from self.execute_signal_wait(env, signal_name, expected_value)
        else:
            yield env.timeout(0.1)
    
    def execute_go_to(self, env: simpy.Environment, target: str, entity: Any) -> Generator:
        """go to 블록명.커넥터명,딜레이 형태의 명령 실행"""
        # 딜레이 처리
        delay_time = 0
        if ',' in target:
            parts = target.split(',', 1)
            target = parts[0].strip()
            delay_str = parts[1].strip()
            delay_time = parse_delay_value(delay_str)
        
        # 딜레이 실행
        if delay_time > 0:
            yield env.timeout(delay_time)
        
        # 타겟 파싱
        if '.' in target:
            block_name, connector_name = target.split('.', 1)
            entity.target_block = block_name.strip()
            entity.target_connector = connector_name.strip()
        else:
            entity.target_block = target.strip()
            entity.target_connector = None
        
        # 이동 완료 신호
        entity.movement_requested = True
        yield env.timeout(0)
    
    def execute_if(self, env: simpy.Environment, condition: str) -> bool:
        """if 조건문 평가"""
        if ' = ' in condition:
            parts = condition.split(' = ', 1)
            signal_name = parts[0].strip()
            expected_value = parts[1].strip().lower() == 'true'
            
            if self.signal_manager:
                current_value = self.signal_manager.get_signal(signal_name, False)
                return current_value == expected_value
        
        return False
    
    def execute_jump(self, env: simpy.Environment, target_line: str) -> int:
        """jump to 1 형태의 명령 실행"""
        try:
            line_number = int(target_line.strip())
            return line_number - 1  # 0-based 인덱스로 변환
        except ValueError:
            return -1
    
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
        
        return None, None
    
    def execute_script_line(self, env: simpy.Environment, line: str, entity: Any) -> Generator:
        """단일 스크립트 라인 실행"""
        command, params = self.parse_script_line(line)
        
        if command == 'delay':
            yield from self.execute_delay(env, params)
        
        elif command == 'signal_set':
            yield from self.execute_signal_set(env, params['signal_name'], params['value'])
        
        elif command == 'wait':
            yield from self.execute_wait(env, params)
        
        elif command == 'go_to':
            yield from self.execute_go_to(env, params, entity)
            return 'movement'  # 이동 신호
        
        elif command == 'if':
            condition_result = self.execute_if(env, params)
            return ('if', condition_result)
        
        elif command == 'jump':
            target_line = self.execute_jump(env, params)
            return ('jump', target_line)
        
        return 'continue'