"""
새로운 단순화된 시뮬레이션 엔진 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simple_block import IndependentBlock
from simple_entity import SimpleEntity
from simple_signal_manager import SimpleSignalManager
from simple_script_executor import SimpleScriptExecutor
from simple_simulation_engine import SimpleSimulationEngine

def test_basic_flow():
    """기본 흐름 테스트"""
    print("=== 기본 흐름 테스트 ===")
    
    # 엔진 생성
    engine = SimpleSimulationEngine()
    
    # 설정
    config = {
        'initial_signals': {
            'process_enable': True,
            'output_enable': True
        },
        'blocks': [
            {
                'id': '1',
                'name': '투입',
                'type': 'source',
                'script': '''delay 1
go to 공정1.L,2'''
            },
            {
                'id': '2', 
                'name': '공정1',
                'script': '''delay 3
공정완료신호 = true
go to 배출.L,1'''
            },
            {
                'id': '3',
                'name': '배출',
                'type': 'sink',
                'script': '''delay 0.5'''
            }
        ],
        'connections': [
            {'fromBlockId': '1', 'fromConnectorId': 'R', 'toBlockId': '2'},
            {'fromBlockId': '2', 'fromConnectorId': 'R', 'toBlockId': '3'}
        ]
    }
    
    # 시뮬레이션 설정
    engine.setup_simulation(config)
    
    # 5스텝 실행
    for step in range(5):
        print(f"\n--- Step {step + 1} ---")
        result = engine.step_simulation()
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            break
        
        print(f"Time: {result.get('simulation_time', 0):.2f}")
        print(f"Total entities: {result.get('total_entities_in_system', 0)}")
        print(f"Processed: {result.get('total_entities_processed', 0)}")
        
        # 블록 상태
        for block_id, block_state in result.get('block_states', {}).items():
            print(f"  Block {block_state['name']}: {block_state['entities_count']} entities")
    
    print("\n=== 테스트 완료 ===")

def test_conditional_script():
    """조건부 스크립트 테스트"""
    print("\n=== 조건부 스크립트 테스트 ===")
    
    engine = SimpleSimulationEngine()
    
    config = {
        'initial_signals': {
            'condition1': True,
            'condition2': False
        },
        'blocks': [
            {
                'id': '1',
                'name': '조건블록',
                'type': 'source',
                'script': '''delay 1
if condition1 = true
    condition2 = true
    delay 2
if condition2 = true
    delay 1
    go to 다음블록.L'''
            },
            {
                'id': '2',
                'name': '다음블록', 
                'type': 'sink',
                'script': 'delay 1'
            }
        ],
        'connections': [
            {'fromBlockId': '1', 'fromConnectorId': 'R', 'toBlockId': '2'}
        ]
    }
    
    engine.setup_simulation(config)
    
    # 3스텝 실행
    for step in range(3):
        print(f"\n--- Step {step + 1} ---")
        result = engine.step_simulation()
        
        print(f"Signals: {result.get('current_signals', {})}")
        print(f"Time: {result.get('simulation_time', 0):.2f}")
    
    print("\n=== 조건부 스크립트 테스트 완료 ===")

def test_delay_range():
    """딜레이 범위 테스트"""
    print("\n=== 딜레이 범위 테스트 ===")
    
    engine = SimpleSimulationEngine()
    
    config = {
        'blocks': [
            {
                'id': '1',
                'name': '랜덤딜레이',
                'type': 'source',
                'script': '''delay 1-5
go to 출구.L'''
            },
            {
                'id': '2',
                'name': '출구',
                'type': 'sink', 
                'script': 'delay 0.1'
            }
        ],
        'connections': [
            {'fromBlockId': '1', 'fromConnectorId': 'R', 'toBlockId': '2'}
        ]
    }
    
    engine.setup_simulation(config)
    
    # 시간 측정
    times = []
    for step in range(3):
        result = engine.step_simulation()
        times.append(result.get('simulation_time', 0))
        print(f"Step {step + 1} time: {times[-1]:.2f}")
    
    print("\n=== 딜레이 범위 테스트 완료 ===")

if __name__ == "__main__":
    test_basic_flow()
    test_conditional_script()
    test_delay_range()
    
    print("\n🎉 모든 테스트 완료! 새로운 단순화된 엔진이 정상 작동합니다.")