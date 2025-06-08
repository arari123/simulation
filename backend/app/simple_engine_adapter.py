"""
새로운 단순 엔진을 기존 API 형식에 맞추는 어댑터
"""
from typing import Dict, List, Any, Optional
from .models import (
    SimulationSetup, SimulationStepResult, SimulationRunResult, 
    BatchStepResult, EntityState, ProcessBlockConfig, ConnectionConfig
)
from .simple_simulation_engine import SimpleSimulationEngine
from .simple_entity import SimpleEntity
from .core.debug_manager import DebugManager
import logging

logger = logging.getLogger(__name__)

class SimpleEngineAdapter:
    """새로운 단순 엔진을 기존 API와 호환되게 만드는 어댑터"""
    
    def __init__(self):
        self.engine = SimpleSimulationEngine()
        self.step_counter = 0
        # 글로벌 디버그 매니저 생성
        self.global_debug_manager = DebugManager()
        # 실행 모드 관련 속성
        self.execution_mode = "default"
        self.mode_config = {}
    
    def has_engine(self) -> bool:
        """엔진이 초기화되었는지 확인"""
        return self.engine is not None and self.engine.env is not None
        
    def convert_setup_to_simple_format(self, setup: SimulationSetup) -> Dict[str, Any]:
        """기존 SimulationSetup을 새 엔진 형식으로 변환"""
        simple_config = {
            'initial_signals': setup.initial_signals or {},
            'blocks': [],
            'connections': []
        }
        
        # globalSignals가 있으면 추가 (타입 정보 포함)
        if hasattr(setup, 'globalSignals'):
            simple_config['globalSignals'] = setup.globalSignals
        
        # 블록 변환
        for block in setup.blocks:
            simple_block = {
                'id': str(block.id),
                'name': block.name,
                'maxCapacity': getattr(block, 'capacity', 100) or 100,
                'actions': block.actions,  # 기존 액션을 그대로 사용 (convert_actions_to_script에서 변환)
                'script': getattr(block, 'script', ''),  # script 필드 추가
                'connectionPoints': getattr(block, 'connectionPoints', [])  # connectionPoints 필드 추가
            }
            
            # 블록 타입 결정
            has_input_connections = any(
                conn.to_block_id == str(block.id) 
                for conn in setup.connections
            )
            has_custom_sink = any(
                action.type == 'custom_sink' 
                for action in block.actions
            )
            
            if not has_input_connections and not has_custom_sink:
                simple_block['type'] = 'source'
            elif has_custom_sink or block.name in ['배출', 'Sink']:
                simple_block['type'] = 'sink'
                
            simple_config['blocks'].append(simple_block)
        
        # 연결 변환
        for conn in setup.connections:
            simple_config['connections'].append({
                'fromBlockId': str(conn.from_block_id),
                'fromConnectorId': conn.from_connector_id,
                'toBlockId': str(conn.to_block_id),
                'toConnectorId': conn.to_connector_id
            })
        
        return simple_config
    
    def convert_simple_result_to_api_format(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """새 엔진 결과를 기존 API 형식으로 변환"""
        # 활성 엔티티 변환 (새로운 속성 포함)
        active_entities = []
        for block_id, block_state in result.get('block_states', {}).items():
            for entity_info in block_state.get('entities', []):
                # EntityState는 dict로 전달 (frontend에서 직접 사용)
                entity_dict = {
                    'id': entity_info['id'],
                    'current_block_id': block_id,
                    'current_block_name': block_state['name'],
                    'state': entity_info.get('state', 'normal'),
                    'color': entity_info.get('color'),
                    'custom_attributes': entity_info.get('custom_attributes', [])
                }
                active_entities.append(entity_dict)
        
        # 시간을 반올림하여 부동소수점 오차 제거 (소수점 1자리)
        simulation_time = round(result.get('simulation_time', 0), 1)
        
        # block_states와 script_logs를 포함하여 반환
        return {
            'time': simulation_time,
            'event_description': f"Simulation step {result.get('step_count', 0)} completed",
            'entities_processed_total': result.get('total_entities_processed', 0),
            'active_entities': active_entities,
            'current_signals': result.get('current_signals', {}),
            'globalSignals': result.get('globalSignals', []),  # 통합된 신호/변수 정보
            'block_states': result.get('block_states', {}),  # 블록 상태 정보 추가
            'script_logs': result.get('script_logs', []),  # 스크립트 로그 추가
            'debug_info': result.get('debug_info', {}),  # 디버그 정보 추가
            'log': [{
                'time': simulation_time,
                'event': f"Step {result.get('step_count', 0)}: {result.get('total_entities_in_system', 0)} entities in system"
            }]
        }
    
    async def setup_simulation(self, setup: SimulationSetup):
        """시뮬레이션 설정"""
        simple_config = self.convert_setup_to_simple_format(setup)
        self.engine.setup_simulation(simple_config)
        
        # 디버그 매니저를 엔진에 연결
        self.engine.set_debug_manager(self.global_debug_manager)
        # Debug manager connected to engine
        
        self.step_counter = 0
    
    def step_simulation(self) -> SimulationStepResult:
        """단일 스텝 실행"""
        result = self.engine.step_simulation()
        self.step_counter += 1
        
        if 'error' in result:
            return SimulationStepResult(
                time=0,
                event_description=f"Error: {result['error']}",
                entities_processed_total=0,
                active_entities=[],
                current_signals={}
            )
        
        converted = self.convert_simple_result_to_api_format(result)
        return SimulationStepResult(**converted)
    
    def batch_step_simulation(self, steps: int) -> BatchStepResult:
        """배치 스텝 실행"""
        logs = []
        final_result = None
        
        for i in range(steps):
            result = self.engine.step_simulation()
            if 'error' in result:
                break
                
            final_result = result
            logs.append({
                'time': round(result.get('simulation_time', 0), 1),
                'event': f"Batch step {i+1}: {result.get('total_entities_in_system', 0)} entities"
            })
        
        if not final_result:
            return BatchStepResult(
                message="Batch execution failed",
                steps_executed=0,
                final_event_description="Error occurred",
                log=[],
                current_time=0,
                active_entities=[],
                total_entities_processed=0
            )
        
        converted = self.convert_simple_result_to_api_format(final_result)
        
        return BatchStepResult(
            message=f"Executed {len(logs)} steps successfully",
            steps_executed=len(logs),
            final_event_description=converted['event_description'],
            log=logs,
            current_time=converted['time'],
            active_entities=converted['active_entities'],
            total_entities_processed=converted['entities_processed_total']
        )
    
    def run_simulation(self, max_steps: int = 100) -> SimulationRunResult:
        """시뮬레이션 연속 실행"""
        logs = []
        final_result = None
        
        for i in range(max_steps):
            result = self.engine.step_simulation()
            if 'error' in result:
                break
                
            final_result = result
            logs.append({
                'time': round(result.get('simulation_time', 0), 1),
                'event': f"Step {i+1}: {result.get('total_entities_in_system', 0)} entities in system"
            })
            
            # 종료 조건 체크 (엔티티가 없고 충분한 시간이 지났을 때)
            if (result.get('total_entities_in_system', 0) == 0 and 
                result.get('simulation_time', 0) > 10):
                break
        
        if not final_result:
            return SimulationRunResult(
                message="Simulation failed",
                log=[],
                total_entities_processed=0,
                final_time=0,
                active_entities=[]
            )
        
        converted = self.convert_simple_result_to_api_format(final_result)
        
        return SimulationRunResult(
            message=f"Simulation completed after {len(logs)} steps",
            log=logs,
            total_entities_processed=converted['entities_processed_total'],
            final_time=converted['time'],
            active_entities=converted['active_entities']
        )
    
    def reset_simulation(self):
        """시뮬레이션 리셋"""
        # 스크립트 상태 초기화
        from .script_state_manager import script_state_manager
        script_state_manager.reset_all()
        
        # 디버그 매니저 초기화 (브레이크포인트는 유지)
        self.global_debug_manager.reset()
        
        self.engine.reset()
        self.step_counter = 0
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """시뮬레이션 상태 조회"""
        return self.engine.get_simulation_status()
    
    def set_execution_mode(self, mode: str, config: dict = None):
        """실행 모드 설정"""
        self.execution_mode = mode
        self.mode_config = config or {}
        
        # 엔진이 있으면 모드 설정 적용
        if self.has_engine():
            # 향후 엔진에 모드 적용 로직 추가
            pass
    
    def get_execution_mode(self) -> str:
        """현재 실행 모드 반환"""
        return self.execution_mode
    
    def get_mode_config(self) -> dict:
        """현재 모드 설정 반환"""
        return self.mode_config

# 전역 어댑터 인스턴스
engine_adapter = SimpleEngineAdapter()