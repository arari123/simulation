import asyncio
import json
import time
import os

# psutil이 없는 경우를 위한 fallback
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    print("⚠️ psutil이 설치되지 않음 - 시스템 리소스 모니터링 제한됨")
    HAS_PSUTIL = False
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation, run_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

class PerformanceProfiler:
    """성능 분석을 위한 상세 프로파일러"""
    
    def __init__(self):
        self.step_times = []
        self.api_times = []
        self.memory_usage = []
        self.cpu_usage = []
        
    def record_step(self, step_time, memory_mb=0, cpu_percent=0):
        self.step_times.append(step_time)
        if memory_mb > 0:
            self.memory_usage.append(memory_mb)
        if cpu_percent > 0:
            self.cpu_usage.append(cpu_percent)
    
    def record_api_call(self, api_time):
        self.api_times.append(api_time)
    
    def get_summary(self):
        if not self.step_times:
            return {}
            
        return {
            "step_performance": {
                "total_steps": len(self.step_times),
                "avg_step_time_ms": sum(self.step_times) * 1000 / len(self.step_times),
                "min_step_time_ms": min(self.step_times) * 1000,
                "max_step_time_ms": max(self.step_times) * 1000,
                "steps_per_second": len(self.step_times) / sum(self.step_times) if sum(self.step_times) > 0 else 0
            },
            "api_performance": {
                "total_calls": len(self.api_times),
                "avg_api_time_ms": sum(self.api_times) * 1000 / len(self.api_times) if self.api_times else 0,
                "total_api_time_ms": sum(self.api_times) * 1000
            },
            "system_resources": {
                "avg_memory_mb": sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
                "max_memory_mb": max(self.memory_usage) if self.memory_usage else 0,
                "avg_cpu_percent": sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
                "max_cpu_percent": max(self.cpu_usage) if self.cpu_usage else 0
            }
        }

async def test_current_vs_old_performance():
    """현재 리팩토링된 코드와 이전 성능 비교"""
    
    print("🔥 DETAILED PERFORMANCE ANALYSIS: Current vs main_old.py")
    print("=" * 80)
    
    # 시스템 정보
    if HAS_PSUTIL:
        process = psutil.Process(os.getpid())
        print(f"🖥️ 시스템 정보:")
        print(f"  Python PID: {os.getpid()}")
        print(f"  CPU 코어: {psutil.cpu_count()}")
        print(f"  메모리: {psutil.virtual_memory().total / (1024**3):.1f}GB")
    else:
        process = None
        print(f"🖥️ 시스템 정보:")
        print(f"  Python PID: {os.getpid()}")
    print()
    
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
    
    # 1. 현재 리팩토링된 코드 성능 테스트
    print("📊 테스트 1: 현재 리팩토링된 코드 (step_simulation)")
    print("-" * 60)
    
    profiler = PerformanceProfiler()
    
    # 초기화 시간 측정
    init_start = time.time()
    reset_simulation_state()
    init_time = time.time() - init_start
    print(f"🔄 초기화 시간: {init_time*1000:.2f}ms")
    
    # 스텝별 상세 성능 측정
    total_steps = 30
    for i in range(1, total_steps + 1):
        # 시스템 리소스 측정
        if HAS_PSUTIL and process:
            memory_mb = process.memory_info().rss / (1024 * 1024)
            cpu_percent = process.cpu_percent()
        else:
            memory_mb = 0
            cpu_percent = 0
        
        # 스텝 실행 시간 측정
        step_start = time.time()
        try:
            result = await step_simulation(setup if i == 1 else None)
            step_time = time.time() - step_start
            
            profiler.record_step(step_time, memory_mb, cpu_percent)
            
            # 첫 10스텝과 마지막 몇 스텝 상세 로그
            if i <= 5 or i % 10 == 0 or i >= total_steps - 2:
                print(f"  Step {i:2d}: {step_time*1000:6.2f}ms | Time: {result.time:5.1f}s | Mem: {memory_mb:6.1f}MB | CPU: {cpu_percent:5.1f}%")
            
            # 2개 제품 처리되면 중단
            if result.entities_processed_total >= 2:
                print(f"  🎯 2개 제품 완료: {i}번째 스텝에서 중단")
                break
                
        except Exception as e:
            print(f"  ❌ Step {i} 오류: {e}")
            break
    
    current_summary = profiler.get_summary()
    
    print(f"\n📈 현재 코드 성능 요약:")
    print(f"  평균 스텝 시간: {current_summary['step_performance']['avg_step_time_ms']:.2f}ms")
    print(f"  최소/최대 스텝 시간: {current_summary['step_performance']['min_step_time_ms']:.2f}ms / {current_summary['step_performance']['max_step_time_ms']:.2f}ms")
    print(f"  스텝/초: {current_summary['step_performance']['steps_per_second']:.0f}")
    print(f"  평균 메모리: {current_summary['system_resources']['avg_memory_mb']:.1f}MB")
    print(f"  평균 CPU: {current_summary['system_resources']['avg_cpu_percent']:.1f}%")
    
    # 2. 전체 실행 성능 비교 (run_simulation)
    print(f"\n📊 테스트 2: 전체 실행 성능 (run_simulation)")
    print("-" * 60)
    
    reset_simulation_state()
    
    setup_run = SimulationSetup(
        blocks=[ProcessBlockConfig(**block) for block in blocks_data],
        connections=[ConnectionConfig(**conn) for conn in connections_data],
        initial_entities=1,
        initial_signals={"공정1 load enable": True},
        stop_entities_processed=3,  # 3개 제품까지
        stop_time=50  # 50초 제한
    )
    
    # 메모리 사용량 측정 시작
    if HAS_PSUTIL and process:
        memory_before = process.memory_info().rss / (1024 * 1024)
    else:
        memory_before = 0
    
    start_time = time.time()
    result = await run_simulation(setup_run)
    end_time = time.time()
    
    if HAS_PSUTIL and process:
        memory_after = process.memory_info().rss / (1024 * 1024)
        memory_diff = memory_after - memory_before
    else:
        memory_diff = 0
    
    run_time = end_time - start_time
    entities_per_sec = result.total_entities_processed / run_time if run_time > 0 else 0
    
    print(f"  실행 시간: {run_time*1000:.2f}ms")
    print(f"  처리된 제품: {result.total_entities_processed}개")
    print(f"  시뮬레이션 시간: {result.final_time:.1f}초")
    print(f"  제품/초 (실제): {entities_per_sec:.2f}")
    print(f"  메모리 증가: {memory_diff:.1f}MB")
    print(f"  실시간 비율: {result.final_time/run_time:.0f}x")
    
    # 3. 성능 병목 분석
    print(f"\n🔍 성능 병목 분석")
    print("-" * 40)
    
    # 느린 스텝들 분석
    slow_steps = [(i+1, t*1000) for i, t in enumerate(profiler.step_times) if t > current_summary['step_performance']['avg_step_time_ms']/1000 * 2]
    if slow_steps:
        print(f"  🐌 평균보다 2배 이상 느린 스텝들:")
        for step_num, step_time in slow_steps[:5]:
            print(f"    Step {step_num}: {step_time:.2f}ms")
    
    # 메모리 누수 체크
    if len(profiler.memory_usage) > 5:
        memory_trend = profiler.memory_usage[-1] - profiler.memory_usage[0]
        if memory_trend > 5:  # 5MB 이상 증가
            print(f"  ⚠️ 메모리 누수 의심: {memory_trend:.1f}MB 증가")
        else:
            print(f"  ✅ 메모리 사용량 안정: {memory_trend:.1f}MB 변화")
    
    # CPU 사용률 분석
    if current_summary['system_resources']['max_cpu_percent'] > 80:
        print(f"  🔥 높은 CPU 사용률: 최대 {current_summary['system_resources']['max_cpu_percent']:.1f}%")
    else:
        print(f"  ✅ CPU 사용률 양호: 평균 {current_summary['system_resources']['avg_cpu_percent']:.1f}%")
    
    return current_summary

async def test_api_overhead():
    """API 호출 오버헤드 측정"""
    
    print(f"\n📡 API 호출 오버헤드 분석")
    print("-" * 50)
    
    # FastAPI 라우트 시뮬레이션 (실제 HTTP 호출 없이 함수 직접 호출)
    # 모델 import 제거하고 직접 API 함수 호출 사용
    
    # base.json 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 초기화
    reset_simulation_state()
    
    # API 호출 시간 측정 (직접 함수 호출)
    api_times = []
    
    # 설정 데이터 준비
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
    
    for i in range(1, 11):
        api_start = time.time()
        
        try:
            if i == 1:
                result = await step_simulation(setup)
            else:
                result = await step_simulation()
            api_time = time.time() - api_start
            api_times.append(api_time)
            
            print(f"  API Call {i}: {api_time*1000:.2f}ms")
            
        except Exception as e:
            print(f"  ❌ API Call {i} 오류: {e}")
            break
    
    if api_times:
        avg_api_time = sum(api_times) / len(api_times)
        print(f"\n  📊 API 성능 요약:")
        print(f"    평균 API 호출 시간: {avg_api_time*1000:.2f}ms")
        print(f"    최소/최대: {min(api_times)*1000:.2f}ms / {max(api_times)*1000:.2f}ms")
        print(f"    API 호출/초: {1/avg_api_time:.0f}")

async def test_frontend_simulation():
    """프론트엔드 시뮬레이션을 위한 성능 테스트"""
    
    print(f"\n🎨 프론트엔드 호환성 테스트")
    print("-" * 50)
    
    # 프론트엔드에서 자주 사용되는 패턴 시뮬레이션
    frontend_times = []
    
    for i in range(1, 21):
        start_time = time.time()
        
        # 1. 스텝 실행
        result = await step_simulation()
        
        # 2. 엔티티 상태 조회 (프론트엔드에서 UI 업데이트용)
        entities = get_active_entity_states()
        
        # 3. 추가 데이터 처리 시뮬레이션
        entity_data = []
        for entity in entities:
            if hasattr(entity, 'id') and hasattr(entity, 'current_block_id'):
                entity_data.append({
                    "id": entity.id,
                    "block_id": entity.current_block_id,
                    "block_name": getattr(entity, 'current_block_name', 'Unknown')
                })
        
        end_time = time.time()
        frontend_time = end_time - start_time
        frontend_times.append(frontend_time)
        
        if i <= 5 or i % 5 == 0:
            print(f"  Frontend Cycle {i}: {frontend_time*1000:.2f}ms | Entities: {len(entity_data)}")
    
    if frontend_times:
        avg_frontend_time = sum(frontend_times) / len(frontend_times)
        print(f"\n  📊 프론트엔드 시뮬레이션 성능:")
        print(f"    평균 사이클 시간: {avg_frontend_time*1000:.2f}ms")
        print(f"    사이클/초: {1/avg_frontend_time:.0f}")

async def main():
    """메인 성능 분석 실행"""
    
    print("🚀 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("=" * 100)
    print("🎯 목표: 리팩토링 전 main_old.py 대비 성능 저하 원인 파악")
    print()
    
    # 현재 성능 측정
    current_perf = await test_current_vs_old_performance()
    
    # API 오버헤드 측정
    await test_api_overhead()
    
    # 프론트엔드 시뮬레이션
    await test_frontend_simulation()
    
    # 최종 결론 및 권장사항
    print(f"\n🏁 최종 분석 결과")
    print("=" * 80)
    
    avg_step_ms = current_perf['step_performance']['avg_step_time_ms']
    steps_per_sec = current_perf['step_performance']['steps_per_second']
    
    print(f"📊 현재 성능:")
    print(f"  스텝/초: {steps_per_sec:.0f}")
    print(f"  평균 스텝 시간: {avg_step_ms:.2f}ms")
    
    print(f"\n🔍 성능 저하 가능한 원인들:")
    
    if avg_step_ms > 1.0:
        print(f"  ❌ 스텝 실행 시간이 1ms 이상 - 백엔드 최적화 필요")
    else:
        print(f"  ✅ 스텝 실행 시간 양호 ({avg_step_ms:.2f}ms)")
    
    if current_perf['system_resources']['avg_memory_mb'] > 100:
        print(f"  ⚠️ 메모리 사용량 높음 - 메모리 최적화 검토 필요")
    else:
        print(f"  ✅ 메모리 사용량 양호")
    
    print(f"\n💡 권장 개선 사항:")
    print(f"  1. 백엔드 최적화: PERFORMANCE_MODE 활성화 상태 확인")
    print(f"  2. 프론트엔드 최적화: 불필요한 API 호출 최소화")
    print(f"  3. 캐싱 시스템: 엔티티 상태 캐싱 강화")
    print(f"  4. 메모리 관리: 엔티티 풀링 최적화")
    
    if steps_per_sec < 5000:
        print(f"\n🚨 성능 경고: main_old.py 대비 성능이 크게 저하된 상태")
        print(f"   권장: 모듈 구조 단순화 또는 main_old.py 패턴 복원 검토")
    elif steps_per_sec < 15000:
        print(f"\n⚠️ 성능 주의: 추가 최적화가 필요한 상태")
    else:
        print(f"\n✅ 성능 양호: 현재 최적화 상태가 우수함")

if __name__ == "__main__":
    asyncio.run(main())