#!/usr/bin/env python3
"""
백엔드 시뮬레이션 성능 테스트
HTTP 오버헤드 없이 순수 엔진 성능 측정
"""
import json
import time
import cProfile
import pstats
import io
import sys
import os

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.simple_simulation_engine import SimpleSimulationEngine
from app.simple_signal_manager import SimpleSignalManager
from app.core.integer_variable_manager import IntegerVariableManager
from app.core.unified_variable_accessor import UnifiedVariableAccessor

def load_config(file_path):
    """시뮬레이션 설정 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def setup_engine(config_data):
    """엔진 직접 설정"""
    engine = SimpleSimulationEngine()
    engine.setup_simulation(config_data)
    return engine

def test_default_mode(engine, target_entities=10):
    """Default mode (엔티티 이동 기반) 테스트"""
    print("\n=== Default Mode Performance Test ===")
    
    # 실행 모드 설정
    engine.set_execution_mode("default")
    
    start_time = time.time()
    step_count = 0
    total_entities = 0
    
    # 목표 엔티티 수만큼 처리될 때까지 실행
    while total_entities < target_entities:
        result = engine.step_simulation()
        step_count += 1
        
        if 'total_entities_processed' in result:
            total_entities = result['total_entities_processed']
        
        # 에러 체크
        if 'error' in result:
            print(f"Error: {result['error']}")
            break
        
        # 진행 상황 출력
        if step_count % 10 == 0:
            print(f"Steps: {step_count}, Entities: {total_entities}, Time: {result.get('simulation_time', 0)}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\nResults:")
    print(f"- Total steps: {step_count}")
    print(f"- Total entities processed: {total_entities}")
    print(f"- Real time elapsed: {elapsed_time:.2f} seconds")
    print(f"- Average time per step: {(elapsed_time/step_count)*1000:.2f} ms")
    print(f"- Average time per entity: {(elapsed_time/total_entities)*1000:.2f} ms")
    
    return elapsed_time, step_count

def test_time_step_mode(engine, duration=60):
    """Time step mode 테스트"""
    print(f"\n=== Time Step Mode Performance Test ({duration}s) ===")
    
    # 실행 모드 설정 (1초 단위)
    engine.set_execution_mode("time_step")
    engine.time_step_duration = 1.0
    
    start_time = time.time()
    step_count = 0
    total_entities = 0
    sim_time = 0
    
    # 목표 시간만큼 시뮬레이션
    while sim_time < duration:
        result = engine.step_simulation()
        step_count += 1
        
        if 'simulation_time' in result:
            sim_time = result['simulation_time']
        
        if 'total_entities_processed' in result:
            total_entities = result['total_entities_processed']
        
        # 에러 체크
        if 'error' in result:
            print(f"Error: {result['error']}")
            break
        
        # 진행 상황 출력
        if step_count % 10 == 0:
            print(f"Steps: {step_count}, Sim time: {sim_time}s, Entities: {total_entities}")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\nResults:")
    print(f"- Total steps: {step_count}")
    print(f"- Simulation time: {sim_time} seconds")
    print(f"- Real time elapsed: {elapsed_time:.2f} seconds")
    print(f"- Time ratio: {sim_time/elapsed_time:.2f}x")
    print(f"- Total entities processed: {total_entities}")
    
    return elapsed_time, step_count

def profile_simulation(engine):
    """프로파일링으로 병목 지점 찾기"""
    print("\n=== Profiling Default Mode ===")
    
    engine.set_execution_mode("default")
    
    # 프로파일러 시작
    pr = cProfile.Profile()
    pr.enable()
    
    # 10 스텝 실행
    for _ in range(10):
        engine.step_simulation()
    
    pr.disable()
    
    # 결과 분석
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # 상위 20개 함수
    
    print("\nTop 20 time-consuming functions:")
    print(s.getvalue())

def main():
    # 설정 파일 경로
    config_path = "../simulation-config (1).json"
    
    print("Loading configuration...")
    config_data = load_config(config_path)
    
    # 엔진 직접 생성 및 초기화
    engine = setup_engine(config_data)
    
    # 로깅 레벨 조정 (성능 테스트 중 로그 최소화)
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    
    # 테스트 실행
    print("\n" + "="*60)
    print("Starting performance tests...")
    print("="*60)
    
    # Default mode 테스트
    default_time, default_steps = test_default_mode(engine, target_entities=10)
    
    # 리셋 및 재초기화
    engine = setup_engine(config_data)
    
    # Time step mode 테스트
    time_step_time, time_step_steps = test_time_step_mode(engine, duration=60)
    
    # 프로파일링 자동 실행
    print("\n" + "="*60)
    print("Running profiling...")
    engine = setup_engine(config_data)
    profile_simulation(engine)
    
    print("\n" + "="*60)
    print("Performance test completed!")
    print("="*60)

if __name__ == "__main__":
    main()