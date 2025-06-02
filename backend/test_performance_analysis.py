import asyncio
import json
import time
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation, run_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

async def test_current_performance():
    """🔍 현재 성능 문제 분석"""
    
    print("🔍 CURRENT PERFORMANCE ANALYSIS")
    print("=" * 60)
    
    # base.json 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # ID 타입 변환
    blocks_data = []
    for block in data["blocks"]:
        block_copy = block.copy()
        block_copy["id"] = str(block_copy["id"])
        blocks_data.append(block_copy)
    
    connections_data = []
    for conn in data["connections"]:
        conn_copy = conn.copy()
        conn_copy["from_block_id"] = str(conn_copy["from_block_id"])
        conn_copy["to_block_id"] = str(conn_copy["to_block_id"])
        connections_data.append(conn_copy)
    
    setup = SimulationSetup(
        blocks=[ProcessBlockConfig(**block) for block in blocks_data],
        connections=[ConnectionConfig(**conn) for conn in connections_data],
        initial_entities=1,
        initial_signals={"공정1 load enable": True}
    )
    
    print("📊 테스트 1: 스텝별 실행 성능")
    print("-" * 40)
    
    # 스텝별 실행 성능 측정
    step_times = []
    total_steps = 20
    
    start_time = time.time()
    for i in range(1, total_steps + 1):
        step_start = time.time()
        result = await step_simulation(setup if i == 1 else None)
        step_end = time.time()
        step_time = step_end - step_start
        step_times.append(step_time)
        
        if i <= 5 or i % 5 == 0:
            print(f"Step {i:2d}: {step_time*1000:.1f}ms (Time: {result.time:.1f}s)")
        
        if result.entities_processed_total >= 2:
            print(f"🎯 2개 제품 완료: {i}번째 스텝")
            break
    
    total_time = time.time() - start_time
    avg_step_time = sum(step_times) / len(step_times)
    
    print(f"\n📈 스텝별 실행 결과:")
    print(f"  총 시간: {total_time:.3f}초")
    print(f"  실행 스텝: {len(step_times)}개")
    print(f"  평균 스텝 시간: {avg_step_time*1000:.1f}ms")
    print(f"  스텝/초: {1/avg_step_time:.1f}")
    
    # 가장 느린 스텝들 분석
    slow_steps = [(i+1, t) for i, t in enumerate(step_times) if t > avg_step_time * 2]
    if slow_steps:
        print(f"  🐌 느린 스텝들:")
        for step_num, step_time in slow_steps[:5]:
            print(f"    Step {step_num}: {step_time*1000:.1f}ms")
    
    print(f"\n📊 테스트 2: 전체 실행 성능 (Run Simulation)")
    print("-" * 40)
    
    # 전체 실행 성능 측정
    reset_simulation_state()
    
    setup_run = SimulationSetup(
        blocks=[ProcessBlockConfig(**block) for block in blocks_data],
        connections=[ConnectionConfig(**conn) for conn in connections_data],
        initial_entities=1,
        initial_signals={"공정1 load enable": True},
        stop_entities_processed=5,  # 5개 제품까지
        stop_time=100  # 100초 제한
    )
    
    start_time = time.time()
    result = await run_simulation(setup_run)
    end_time = time.time()
    
    run_time = end_time - start_time
    entities_per_sec = result.total_entities_processed / run_time if run_time > 0 else 0
    
    print(f"  실행 시간: {run_time:.3f}초")
    print(f"  처리된 제품: {result.total_entities_processed}개")
    print(f"  시뮬레이션 시간: {result.final_time:.1f}초")
    print(f"  제품/초 (실제): {entities_per_sec:.2f}")
    print(f"  제품/초 (시뮬): {result.total_entities_processed/result.final_time:.2f}")
    
    print(f"\n🔍 성능 분석:")
    print(f"  실제 시간 대비 시뮬레이션 시간 비율: {result.final_time/run_time:.1f}x")
    
    if run_time > result.final_time:
        slowdown = run_time / result.final_time
        print(f"  ⚠️ 실제 시간이 시뮬레이션 시간보다 {slowdown:.1f}배 느림!")
        print(f"  이는 SimPy 오버헤드가 심각하다는 의미입니다.")
    else:
        speedup = result.final_time / run_time
        print(f"  ✅ 시뮬레이션이 실제 시간보다 {speedup:.1f}배 빠름")
    
    print(f"\n💡 JavaScript 대안 성능 추정:")
    print(f"  간단한 이벤트 기반 시뮬레이션이라면")
    print(f"  JavaScript로 수십만 이벤트/초 처리 가능")
    print(f"  현재 SimPy: ~{1/avg_step_time:.0f} 스텝/초")
    print(f"  예상 JS 성능: ~100,000+ 이벤트/초")
    
    return {
        "avg_step_time_ms": avg_step_time * 1000,
        "steps_per_second": 1/avg_step_time,
        "run_time_seconds": run_time,
        "entities_processed": result.total_entities_processed,
        "simulation_time": result.final_time,
        "performance_ratio": result.final_time/run_time if run_time > 0 else 0
    }

async def test_bottleneck_analysis():
    """🔍 병목 지점 상세 분석"""
    
    print(f"\n🔍 BOTTLENECK ANALYSIS")
    print("=" * 40)
    
    # 컴포넌트별 성능 측정을 위한 간단한 테스트들
    
    print("1. 시뮬레이션 초기화 시간:")
    start = time.time()
    reset_simulation_state()
    end = time.time()
    print(f"   {(end-start)*1000:.1f}ms")
    
    print("2. 설정 파싱 시간:")
    start = time.time()
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    blocks_data = [{"id": str(block["id"]), **{k: v for k, v in block.items() if k != "id"}} for block in data["blocks"]]
    connections_data = [{"from_block_id": str(conn["from_block_id"]), "to_block_id": str(conn["to_block_id"]), **{k: v for k, v in conn.items() if k not in ["from_block_id", "to_block_id"]}} for conn in data["connections"]]
    setup = SimulationSetup(
        blocks=[ProcessBlockConfig(**block) for block in blocks_data],
        connections=[ConnectionConfig(**conn) for conn in connections_data],
        initial_entities=1,
        initial_signals={"공정1 load enable": True}
    )
    end = time.time()
    print(f"   {(end-start)*1000:.1f}ms")
    
    print("3. 단일 스텝 실행 분석:")
    # 첫 번째 스텝 (초기화 포함)
    start = time.time()
    result1 = await step_simulation(setup)
    end = time.time()
    print(f"   첫 스텝 (초기화 포함): {(end-start)*1000:.1f}ms")
    
    # 두 번째 스텝 (초기화 없음)
    start = time.time()
    result2 = await step_simulation()
    end = time.time()
    print(f"   일반 스텝: {(end-start)*1000:.1f}ms")
    
    # 세 번째 스텝
    start = time.time()
    result3 = await step_simulation()
    end = time.time()
    print(f"   세 번째 스텝: {(end-start)*1000:.1f}ms")
    
    print("\n🎯 병목 지점 추정:")
    print("   - SimPy 이벤트 처리 오버헤드")
    print("   - Python 인터프리터 오버헤드") 
    print("   - 과도한 로깅 및 디버깅")
    print("   - Generator 기반 코루틴 오버헤드")
    print("   - 메모리 할당/해제 오버헤드")

async def main():
    """메인 성능 분석"""
    
    perf_results = await test_current_performance()
    await test_bottleneck_analysis()
    
    print(f"\n🏁 최종 성능 평가:")
    print(f"   현재 성능: {perf_results['steps_per_second']:.1f} 스텝/초")
    print(f"   평균 스텝 시간: {perf_results['avg_step_time_ms']:.1f}ms")
    
    if perf_results['steps_per_second'] < 100:
        print(f"   ❌ 성능 부족: JavaScript 대안 검토 필요")
        print(f"   💡 권장: 클라이언트 사이드 시뮬레이션 엔진 구현")
    elif perf_results['steps_per_second'] < 1000:
        print(f"   ⚠️ 성능 개선 필요: SimPy 최적화 가능")
    else:
        print(f"   ✅ 성능 양호")

if __name__ == "__main__":
    asyncio.run(main())