import asyncio
import json
import time
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

async def test_performance_improvement():
    """🚀 엔티티 이동 기반 스텝 실행 성능 테스트"""
    
    print("🚀 PERFORMANCE TEST: Entity Movement-Based Step Execution")
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
        initial_entities=3,
        initial_signals={"공정1 load enable": True}  # 명시적으로 신호 설정
    )
    
    # 성능 테스트
    performance_steps = 50
    start_time = time.time()
    
    transit_detections = []
    route_detections = []
    
    for i in range(1, performance_steps + 1):
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            # Transit 엔티티 감지
            for entity in result.active_entities:
                if hasattr(entity, 'current_block_id') and entity.current_block_id == "transit":
                    transit_detections.append(f"Step {i}: Entity {entity.id}")
                    print(f"🟣 [TRANSIT] Step {i}: Entity {entity.id} in transit")
            
            # 공정1.R → 배출.L 이동 감지
            if ("공정1" in result.event_description and "배출" in result.event_description) or \
               ("routed" in result.event_description.lower() and "entity" in result.event_description.lower()):
                route_detections.append(f"Step {i}: {result.event_description}")
                print(f"⭐ [ROUTING] Step {i}: {result.event_description}")
            
            # 로그는 5 스텝마다만 출력
            if i % 5 == 0:
                print(f"Step {i:2d}: Time={result.time:.1f}, Active={len(result.active_entities)}, Processed={result.entities_processed_total}")
            
            # 첫 제품이 처리되면 완료
            if result.entities_processed_total > 0:
                print(f"🎉 첫 제품 처리 완료: {i}번째 스텝")
                break
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            break
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n📊 RESULTS:")
    print(f"🚀 Performance: {i} steps in {total_time:.4f}s = {i/total_time:.0f} steps/sec")
    print(f"👁️ Transit detections: {len(transit_detections)}")
    print(f"🔄 Routing detections: {len(route_detections)}")
    
    # 성능 평가
    steps_per_sec = i/total_time
    if steps_per_sec > 10000:
        print("🟢 Performance: EXCELLENT (>10k steps/sec)")
    elif steps_per_sec > 1000:
        print("🟡 Performance: GOOD (>1k steps/sec)")
    else:
        print("🔴 Performance: SLOW (<1k steps/sec)")
    
    # Transit 감지 평가
    if len(transit_detections) > 0:
        print("✅ Transit entity detection: WORKING")
        for detection in transit_detections[:5]:  # 처음 5개만 표시
            print(f"  - {detection}")
    else:
        print("❌ Transit entity detection: NO DETECTIONS")
    
    # Routing 감지 평가
    if len(route_detections) > 0:
        print("✅ Entity routing detection: WORKING")
        for detection in route_detections[:3]:  # 처음 3개만 표시
            print(f"  - {detection}")
    else:
        print("❌ Entity routing detection: NO DETECTIONS")
    
    return {
        "steps_per_second": steps_per_sec,
        "transit_detections": len(transit_detections),
        "routing_detections": len(route_detections),
        "entities_processed": result.entities_processed_total if 'result' in locals() else 0
    }

async def test_signal_system():
    """🔍 신호 시스템 테스트 (기존 문제 검증)"""
    
    print(f"\n🔍 SIGNAL SYSTEM TEST")
    print("=" * 40)
    
    # 새로운 시뮬레이션 시작
    reset_simulation_state()
    
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
        initial_signals=data.get("initial_signals", {"공정1 load enable": True})  # 신호를 명시적으로 True로 설정
    )
    
    print(f"📋 초기 신호 상태: {setup.initial_signals}")
    
    # 첫 몇 스텝 실행
    for i in range(1, 10):
        try:
            result = await step_simulation(setup if i == 1 else None)
            print(f"Step {i}: Time={result.time:.1f}, Signals={result.current_signals}, Event: {result.event_description[:60]}...")
            
            # 시간이 진행되면 성공
            if result.time > 0:
                print(f"✅ 시간 진행 확인: {result.time}초")
                break
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            break
    
    return result.time > 0 if 'result' in locals() else False

async def main():
    """메인 테스트 실행"""
    
    print("🧪 MAIN_OLD.PY PATTERN IMPLEMENTATION TEST")
    print("=" * 70)
    
    # 1. 성능 및 엔티티 가시성 테스트
    perf_results = await test_performance_improvement()
    
    # 2. 신호 시스템 테스트
    signal_working = await test_signal_system()
    
    print(f"\n🏁 FINAL SUMMARY:")
    print(f"🚀 Performance: {perf_results['steps_per_second']:.0f} steps/sec")
    print(f"👁️ Transit detections: {perf_results['transit_detections']}")
    print(f"🔄 Routing detections: {perf_results['routing_detections']}")
    print(f"🔍 Signal system: {'✅ WORKING' if signal_working else '❌ STUCK'}")
    print(f"🎯 Entities processed: {perf_results['entities_processed']}")
    
    # 종합 평가
    if (perf_results['steps_per_second'] > 10000 and 
        perf_results['transit_detections'] > 0 and 
        signal_working):
        print("\n🎉 ALL IMPROVEMENTS SUCCESSFUL!")
    else:
        print("\n⚠️ Some issues remain to be resolved")

if __name__ == "__main__":
    asyncio.run(main())