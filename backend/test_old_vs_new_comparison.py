import asyncio
import json
import time
import sys
import os

# main_old.py의 함수들을 import하기 위한 설정
sys.path.append('.')

async def test_main_old_performance():
    """main_old.py 성능 테스트"""
    
    print("🔍 main_old.py 성능 테스트")
    print("-" * 50)
    
    try:
        # main_old.py에서 필요한 함수들 import
        from main_old import (
            step_simulation as old_step_simulation,
            reset_simulation_state as old_reset_simulation_state,
            SimulationSetup as OldSimulationSetup,
            ProcessBlockConfig as OldProcessBlockConfig,
            ConnectionConfig as OldConnectionConfig
        )
        
        # base.json 로드
        with open("../base.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 이전 버전 초기화
        old_reset_simulation_state()
        
        # 설정 준비
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
        
        old_setup = OldSimulationSetup(
            blocks=[OldProcessBlockConfig(**block) for block in blocks_data],
            connections=[OldConnectionConfig(**conn) for conn in connections_data],
            initial_entities=1,
            initial_signals={"공정1 load enable": True}
        )
        
        # main_old.py 성능 측정
        old_step_times = []
        total_steps = 30
        
        print(f"📊 main_old.py 스텝별 성능 측정 ({total_steps}스텝)")
        
        for i in range(1, total_steps + 1):
            step_start = time.time()
            try:
                if i == 1:
                    result = await old_step_simulation(old_setup)
                else:
                    result = await old_step_simulation()
                
                step_time = time.time() - step_start
                old_step_times.append(step_time)
                
                if i <= 5 or i % 10 == 0:
                    print(f"  Old Step {i:2d}: {step_time*1000:6.2f}ms | Time: {result.time:5.1f}s")
                
                # 2개 제품 처리되면 중단
                if result.entities_processed_total >= 2:
                    print(f"  🎯 main_old.py: 2개 제품 완료: {i}번째 스텝")
                    break
                    
            except Exception as e:
                print(f"  ❌ Old Step {i} 오류: {e}")
                break
        
        if old_step_times:
            avg_old_time = sum(old_step_times) / len(old_step_times)
            old_steps_per_sec = 1 / avg_old_time if avg_old_time > 0 else 0
            
            print(f"\n📈 main_old.py 성능 요약:")
            print(f"  평균 스텝 시간: {avg_old_time*1000:.2f}ms")
            print(f"  최소/최대: {min(old_step_times)*1000:.2f}ms / {max(old_step_times)*1000:.2f}ms")
            print(f"  스텝/초: {old_steps_per_sec:.0f}")
            
            return {
                "avg_time": avg_old_time,
                "steps_per_sec": old_steps_per_sec,
                "total_steps": len(old_step_times),
                "min_time": min(old_step_times),
                "max_time": max(old_step_times)
            }
        else:
            print("❌ main_old.py 테스트 실패")
            return None
            
    except ImportError as e:
        print(f"❌ main_old.py import 실패: {e}")
        print("💡 main_old.py 파일이 존재하지 않거나 호환되지 않습니다.")
        return None
    except Exception as e:
        print(f"❌ main_old.py 테스트 중 오류: {e}")
        return None

async def test_new_performance():
    """현재 리팩토링된 코드 성능 테스트"""
    
    print("\n🔍 현재 리팩토링된 코드 성능 테스트")
    print("-" * 50)
    
    # 현재 버전 import
    from app.routes.simulation import reset_simulation_state
    from app.simulation_engine import step_simulation
    from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
    
    # base.json 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 현재 버전 초기화
    reset_simulation_state()
    
    # 설정 준비
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
    
    # 현재 코드 성능 측정
    new_step_times = []
    total_steps = 30
    
    print(f"📊 현재 코드 스텝별 성능 측정 ({total_steps}스텝)")
    
    for i in range(1, total_steps + 1):
        step_start = time.time()
        try:
            if i == 1:
                result = await step_simulation(setup)
            else:
                result = await step_simulation()
            
            step_time = time.time() - step_start
            new_step_times.append(step_time)
            
            if i <= 5 or i % 10 == 0:
                print(f"  New Step {i:2d}: {step_time*1000:6.2f}ms | Time: {result.time:5.1f}s")
            
            # 2개 제품 처리되면 중단
            if result.entities_processed_total >= 2:
                print(f"  🎯 현재 코드: 2개 제품 완료: {i}번째 스텝")
                break
                
        except Exception as e:
            print(f"  ❌ New Step {i} 오류: {e}")
            break
    
    if new_step_times:
        avg_new_time = sum(new_step_times) / len(new_step_times)
        new_steps_per_sec = 1 / avg_new_time if avg_new_time > 0 else 0
        
        print(f"\n📈 현재 코드 성능 요약:")
        print(f"  평균 스텝 시간: {avg_new_time*1000:.2f}ms")
        print(f"  최소/최대: {min(new_step_times)*1000:.2f}ms / {max(new_step_times)*1000:.2f}ms")
        print(f"  스텝/초: {new_steps_per_sec:.0f}")
        
        return {
            "avg_time": avg_new_time,
            "steps_per_sec": new_steps_per_sec,
            "total_steps": len(new_step_times),
            "min_time": min(new_step_times),
            "max_time": max(new_step_times)
        }
    else:
        print("❌ 현재 코드 테스트 실패")
        return None

async def analyze_performance_difference(old_perf, new_perf):
    """성능 차이 분석"""
    
    print("\n📊 성능 비교 분석")
    print("=" * 80)
    
    if not old_perf:
        print("❌ main_old.py 성능 데이터 없음 - 비교 불가")
        if new_perf:
            print(f"✅ 현재 코드만 측정됨: {new_perf['steps_per_sec']:.0f} 스텝/초")
        return
    
    if not new_perf:
        print("❌ 현재 코드 성능 데이터 없음 - 비교 불가")
        return
    
    # 성능 비교
    speed_ratio = new_perf['steps_per_sec'] / old_perf['steps_per_sec']
    time_ratio = old_perf['avg_time'] / new_perf['avg_time']
    
    print(f"📈 성능 비교 결과:")
    print(f"  {'항목':<20} {'main_old.py':<15} {'현재 코드':<15} {'비율':<10}")
    print(f"  {'-'*20} {'-'*15} {'-'*15} {'-'*10}")
    print(f"  {'평균 스텝 시간':<20} {old_perf['avg_time']*1000:<14.2f}ms {new_perf['avg_time']*1000:<14.2f}ms {time_ratio:<9.2f}x")
    print(f"  {'스텝/초':<20} {old_perf['steps_per_sec']:<14.0f} {new_perf['steps_per_sec']:<14.0f} {speed_ratio:<9.2f}x")
    print(f"  {'최소 스텝 시간':<20} {old_perf['min_time']*1000:<14.2f}ms {new_perf['min_time']*1000:<14.2f}ms")
    print(f"  {'최대 스텝 시간':<20} {old_perf['max_time']*1000:<14.2f}ms {new_perf['max_time']*1000:<14.2f}ms")
    
    print(f"\n🔍 분석 결과:")
    
    if speed_ratio >= 1.1:
        print(f"  🚀 성능 향상: 현재 코드가 {speed_ratio:.1f}배 빠름")
        print(f"     ✅ 리팩토링이 성능 개선에 성공!")
    elif speed_ratio >= 0.9:
        print(f"  ✅ 성능 유지: 차이가 {abs(1-speed_ratio)*100:.1f}% 이내로 유사함")
        print(f"     ✅ 리팩토링이 성능에 큰 영향을 주지 않음")
    else:
        print(f"  ⚠️ 성능 저하: 현재 코드가 {1/speed_ratio:.1f}배 느림")
        print(f"     🔧 성능 최적화 필요")
        
        # 성능 저하 원인 분석
        print(f"\n🔧 성능 저하 원인 분석:")
        
        if new_perf['max_time'] > old_perf['max_time'] * 2:
            print(f"  - 최대 스텝 시간이 과도하게 증가 ({new_perf['max_time']*1000:.2f}ms vs {old_perf['max_time']*1000:.2f}ms)")
        
        if new_perf['avg_time'] > 0.001:  # 1ms 이상
            print(f"  - 평균 스텝 시간이 임계값(1ms) 초과")
        
        print(f"\n💡 권장 개선 방안:")
        print(f"  1. 모듈 import 오버헤드 최소화")
        print(f"  2. 함수 호출 스택 단순화") 
        print(f"  3. 캐싱 시스템 강화")
        print(f"  4. 불필요한 로깅 제거")

async def test_concurrent_performance():
    """동시 실행 성능 테스트"""
    
    print(f"\n🔄 동시 실행 성능 테스트")
    print("-" * 50)
    
    from app.routes.simulation import reset_simulation_state
    from app.simulation_engine import step_simulation
    from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
    
    # base.json 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 여러 번의 동시 테스트
    concurrent_results = []
    
    for test_round in range(1, 4):  # 3라운드 테스트
        print(f"\n  라운드 {test_round}:")
        
        # 초기화
        reset_simulation_state()
        
        # 설정 준비
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
        
        # 10스텝 연속 실행
        round_start = time.time()
        step_times = []
        
        for i in range(1, 11):
            step_start = time.time()
            if i == 1:
                result = await step_simulation(setup)
            else:
                result = await step_simulation()
            step_time = time.time() - step_start
            step_times.append(step_time)
        
        round_time = time.time() - round_start
        avg_step_time = sum(step_times) / len(step_times)
        
        concurrent_results.append({
            "round": test_round,
            "total_time": round_time,
            "avg_step_time": avg_step_time,
            "steps_per_sec": len(step_times) / round_time
        })
        
        print(f"    총 시간: {round_time*1000:.2f}ms")
        print(f"    평균 스텝: {avg_step_time*1000:.2f}ms")
        print(f"    스텝/초: {len(step_times)/round_time:.0f}")
    
    # 결과 요약
    if concurrent_results:
        avg_total_time = sum(r['total_time'] for r in concurrent_results) / len(concurrent_results)
        avg_step_time = sum(r['avg_step_time'] for r in concurrent_results) / len(concurrent_results) 
        avg_steps_per_sec = sum(r['steps_per_sec'] for r in concurrent_results) / len(concurrent_results)
        
        print(f"\n  📊 동시 실행 성능 요약:")
        print(f"    평균 총 시간: {avg_total_time*1000:.2f}ms")
        print(f"    평균 스텝 시간: {avg_step_time*1000:.2f}ms")
        print(f"    평균 스텝/초: {avg_steps_per_sec:.0f}")
        
        # 일관성 체크
        time_variance = max(r['avg_step_time'] for r in concurrent_results) - min(r['avg_step_time'] for r in concurrent_results)
        if time_variance < avg_step_time * 0.1:  # 10% 이내 차이
            print(f"    ✅ 성능 일관성 양호 (편차: {time_variance*1000:.2f}ms)")
        else:
            print(f"    ⚠️ 성능 불일치 감지 (편차: {time_variance*1000:.2f}ms)")

async def main():
    """메인 비교 테스트 실행"""
    
    print("🔥 main_old.py vs 현재 코드 성능 비교")
    print("=" * 100)
    print("🎯 목표: 리팩토링 전후 성능 차이 정확한 측정")
    print()
    
    # 1. main_old.py 성능 테스트
    old_perf = await test_main_old_performance()
    
    # 2. 현재 코드 성능 테스트  
    new_perf = await test_new_performance()
    
    # 3. 성능 차이 분석
    await analyze_performance_difference(old_perf, new_perf)
    
    # 4. 동시 실행 성능 테스트
    await test_concurrent_performance()
    
    print(f"\n🏁 최종 결론")
    print("=" * 80)
    
    if old_perf and new_perf:
        speed_ratio = new_perf['steps_per_sec'] / old_perf['steps_per_sec']
        
        if speed_ratio >= 1.1:
            print(f"🎉 성공: 리팩토링 후 성능이 {speed_ratio:.1f}배 향상됨!")
            print(f"   현재 사용자 불만은 다른 원인(프론트엔드, 네트워크 등)일 가능성")
        elif speed_ratio >= 0.9:
            print(f"✅ 양호: 리팩토링이 성능에 큰 영향 없음 ({speed_ratio:.2f}x)")
            print(f"   사용자 불만은 다른 요인 분석 필요")
        else:
            print(f"⚠️ 문제: 리팩토링 후 성능이 {1/speed_ratio:.1f}배 저하됨")
            print(f"   백엔드 최적화 작업 필요")
    
    elif new_perf:
        print(f"✅ 현재 코드 성능: {new_perf['steps_per_sec']:.0f} 스텝/초")
        print(f"   main_old.py 비교 불가능하지만 현재 성능은 우수함")
    
    else:
        print(f"❌ 성능 측정 실패 - 추가 디버깅 필요")

if __name__ == "__main__":
    asyncio.run(main())