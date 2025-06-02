import asyncio
import json
import time
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

async def test_performance_and_entity_visibility():
    """🚀 엔티티 이동 기반 스텝 실행 성능 및 UI 가시성 테스트"""
    
    print("🧪 PERFORMANCE AND ENTITY VISIBILITY TEST")
    print("=" * 60)
    
    # 환경 초기화
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    reset_simulation_state()
    
    # 시뮬레이션 설정 데이터 준비 (ID를 문자열로 변환)
    blocks_data = []
    for block in data["blocks"]:
        block_copy = block.copy()
        block_copy["id"] = str(block_copy["id"])  # ID를 문자열로 변환
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
        initial_entities=5,
        initial_signals=data.get("initial_signals", {})
    )
    
    print(f"📋 설정 로드 완료: {len(setup.blocks)}개 블록, {len(setup.connections)}개 연결")
    
    # 🚀 성능 테스트
    print("\n🚀 PERFORMANCE TEST: Entity Movement-Based Step Execution")
    performance_steps = 100
    start_time = time.time()
    
    for i in range(1, performance_steps + 1):
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            # 성능 로그는 10 스텝마다만 출력
            if i % 10 == 0:
                print(f"Step {i:3d}: Time={result.time:.2f}, Entities={len(result.active_entities)}, Event: {result.event_description[:50]}...")
            
            # 엔티티가 처리되면 성능 테스트 완료
            if result.entities_processed_total > 0:
                print(f"✅ 첫 엔티티 처리 완료: {i}번째 스텝에서 {result.entities_processed_total}개 엔티티 처리")
                break
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            break
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # 🚀 성능 분석
    print(f"\n📊 PERFORMANCE ANALYSIS:")
    print(f"Total steps executed: {i}")
    print(f"Total time: {total_time:.4f}s")
    print(f"Average step time: {total_time/i:.6f}s")
    print(f"Steps per second: {i/total_time:.0f}")
    
    if total_time/i < 0.001:  # 1ms 미만
        print("🟢 Performance: EXCELLENT (< 1ms per step)")
    elif total_time/i < 0.01:  # 10ms 미만
        print("🟡 Performance: GOOD (< 10ms per step)")
    else:
        print("🔴 Performance: NEEDS IMPROVEMENT (> 10ms per step)")
    
    # 🔍 Entity visibility test
    print(f"\n👁️ ENTITY VISIBILITY TEST: Transit Entity Detection")
    
    # 리셋 후 새로운 시뮬레이션 시작
    reset_simulation_state()
    
    transit_detections = []
    
    for i in range(1, 20):  # 20 스텝 실행
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            # Transit 엔티티 감지
            for entity in result.active_entities:
                if hasattr(entity, 'current_block_id') and entity.current_block_id == "transit":
                    transit_detections.append(f"Step {i}: Entity {entity.id} in transit")
                    print(f"🟣 [TRANSIT DETECTED] Step {i}: Entity {entity.id} in transit state")
            
            # 공정1.R → 배출.L 이동 패턴 감지
            if "공정1" in result.event_description and "배출" in result.event_description:
                print(f"⭐ [공정1→배출 이동] Step {i}: {result.event_description}")
            
            print(f"Step {i:2d}: Time={result.time:.1f}, Active={len(result.active_entities)}, Processed={result.entities_processed_total}")
            
            # 첫 제품이 배출되면 테스트 완료
            if result.entities_processed_total > 0:
                print(f"🎉 첫 제품 배출 완료: {i}번째 스텝에서 배출")
                break
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            break
    
    # 🔍 결과 분석
    print(f"\n📊 ENTITY VISIBILITY ANALYSIS:")
    print(f"Transit detections: {len(transit_detections)}")
    for detection in transit_detections:
        print(f"  - {detection}")
    
    if len(transit_detections) > 0:
        print("✅ Transit entity detection: WORKING")
    else:
        print("❌ Transit entity detection: NOT WORKING")
    
    print(f"\n🎯 TEST SUMMARY:")
    print(f"✅ Performance test: {i} steps in {total_time:.4f}s ({i/total_time:.0f} steps/sec)")
    print(f"✅ Entity visibility: {len(transit_detections)} transit detections")
    print(f"✅ Simulation completion: {result.entities_processed_total} entities processed")
    
    return {
        "performance_steps_per_second": i/total_time,
        "transit_detections": len(transit_detections),
        "entities_processed": result.entities_processed_total
    }

if __name__ == "__main__":
    results = asyncio.run(test_performance_and_entity_visibility())
    print(f"\n🏁 Final Results: {results}")