"""
Step Mode Wrapper
기존 process_entity를 감싸서 스크립트 실행 상태를 추적합니다.
"""
import simpy
import logging
from typing import Generator, Optional
from .script_state_manager import script_state_manager
from .simple_entity import SimpleEntity

logger = logging.getLogger(__name__)

class StepModeWrapper:
    """스텝 모드에서 스크립트 실행 상태를 관리하는 래퍼"""
    
    @staticmethod
    def process_entity_with_state(env: simpy.Environment, block, entity: Optional[SimpleEntity]) -> Generator:
        """상태를 추적하면서 엔티티를 처리합니다."""
        block_id = block.id
        state = script_state_manager.get_state(block_id)
        
        # 이미 실행 중인 경우, 이전 상태에서 계속
        if state.is_executing:
            logger.info(f"Block {block.name} resuming from line {state.current_line}")
            # 이전에 생성된 엔티티가 있으면 사용
            if state.entity_ref and not entity:
                entity = state.entity_ref
                logger.info(f"Using previously created entity {entity.id}")
        else:
            # 새로운 실행 시작
            script_state_manager.start_execution(block_id, 
                                               entity.id if entity else None, 
                                               entity)
            state.current_line = 0
        
        # force execution 처리
        start_line = 0
        if block.has_force_execution() and state.current_line == 0:
            # force execution 라인은 건너뛰기
            start_line = 1
            state.current_line = 1
        else:
            start_line = state.current_line
        
        # 스크립트 실행
        current_line = start_line
        max_iterations = 1000
        iteration_count = 0
        
        while current_line < len(block.script_lines) and iteration_count < max_iterations:
            iteration_count += 1
            line = block.script_lines[current_line].strip()
            
            # 빈 줄이나 주석은 건너뛰기
            if not line or line.startswith('//'):
                current_line += 1
                continue
            
            # 현재 라인 업데이트
            script_state_manager.set_current_line(block_id, current_line)
            
            # 스크립트 라인 실행
            # Executing line
            result = yield from block.script_executor.execute_script_line(env, line, entity, block.name, block)
            # Result processed
            
            # 결과 처리
            if isinstance(result, tuple) and result[0] == 'created_entity':
                # create entity 명령으로 엔티티가 생성된 경우
                entity = result[1]
                # 상태에 엔티티 저장
                script_state_manager.update_state(block_id, 
                                                entity_id=entity.id,
                                                entity_ref=entity)
                logger.info(f"[{block.name}] Entity created and saved in state: {entity.id}")
                current_line += 1
                
            elif result == 'movement':
                # 이동 요청 후에도 스크립트 계속 실행
                logger.info(f"[{block.name}] Movement requested, continuing script execution")
                current_line += 1
                # 계속 실행하지 않고 리턴 (기존 동작 유지)
                return entity
                
            elif isinstance(result, tuple) and result[0] == 'jump':
                # jump 명령 처리
                target_line = result[1]
                if 0 <= target_line < len(block.script_lines):
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
                    while current_line < len(block.script_lines):
                        line = block.script_lines[current_line]
                        # 들여쓰기가 없으면 if 블록 종료
                        if not line.startswith('\t') and not line.startswith('    '):
                            break
                        
                        stripped_line = line.strip()
                        if not stripped_line or stripped_line.startswith('//'):
                            current_line += 1
                            continue
                        
                        # 현재 라인 업데이트
                        script_state_manager.set_current_line(block_id, current_line)
                        
                        sub_result = yield from block.script_executor.execute_script_line(env, stripped_line, entity, block.name, block)
                        
                        if sub_result == 'movement':
                            logger.info(f"[{block.name}] Movement in if block, keeping state for next step")
                            # script_state_manager.end_execution(block_id)  # 종료하지 않음
                            return entity
                        elif isinstance(sub_result, tuple) and sub_result[0] == 'created_entity':
                            entity = sub_result[1]
                            script_state_manager.update_state(block_id, 
                                                            entity_id=entity.id,
                                                            entity_ref=entity)
                            logger.info(f"[{block.name}] Entity created in if block: {entity.id}")
                        
                        current_line += 1
                else:
                    # 조건이 거짓이면 들여쓰기된 블록 스킵
                    current_line = StepModeWrapper._skip_indented_block(block, current_line)
            else:
                current_line += 1
        
        # 스크립트 실행 완료
        logger.info(f"[{block.name}] Script execution completed")
        script_state_manager.end_execution(block_id)
        return entity
    
    @staticmethod
    def _skip_indented_block(block, if_line_index: int) -> int:
        """if 조건이 거짓일 때 들여쓰기된 블록을 스킵"""
        current_line = if_line_index + 1
        
        while current_line < len(block.script_lines):
            line = block.script_lines[current_line]
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