import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

async def test_step_by_step_flow():
    """🔍 스텝별 시뮬레이션 진행 상세 테스트"""
    
    print("🔍 STEP-BY-STEP SIMULATION FLOW TEST")
    print("=" * 50)
    
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
    
    print(f"📋 초기 신호 설정: {setup.initial_signals}")
    print()
    
    # 스텝별 실행
    max_steps = 15
    for i in range(1, max_steps + 1):
        print(f"🔸 === STEP {i} ===")
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            print(f"⏰ Time: {result.time:.1f}s")
            print(f"📝 Event: {result.event_description}")
            print(f"🔢 Active Entities: {len(result.active_entities)}")
            print(f"📊 Processed Total: {result.entities_processed_total}")
            print(f"🔍 Signals: {result.current_signals}")
            
            # 엔티티 상세 정보
            if result.active_entities:
                for j, entity in enumerate(result.active_entities):
                    if hasattr(entity, 'id') and hasattr(entity, 'current_block_id'):
                        location = entity.current_block_id
                        if hasattr(entity, 'current_block_name'):
                            location = f"{location} ({entity.current_block_name})"
                        print(f"  📦 Entity {entity.id}: {location}")
            else:
                print(f"  📦 No active entities")
            
            # 첫 제품 처리 완료 시 중단
            if result.entities_processed_total > 0:
                print(f"\n🎉 첫 제품 처리 완료! (Step {i})")
                break
                
            # 시간이 더 이상 진행되지 않으면 중단 (더 관대하게 5번으로 변경)
            if i > 1 and result.time == prev_time:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 5:
                    print(f"\n⚠️ 5번 연속 시간 진행 없음 - 중단 (Step {i})")
                    break
            else:
                consecutive_no_progress = 0
                
            prev_time = result.time
            print()
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n📋 테스트 완료:")
    print(f"  최종 시간: {result.time:.1f}초")
    print(f"  처리된 엔티티: {result.entities_processed_total}개")
    print(f"  활성 엔티티: {len(result.active_entities)}개")

if __name__ == "__main__":
    consecutive_no_progress = 0
    prev_time = 0
    asyncio.run(test_step_by_step_flow())