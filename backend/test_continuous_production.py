import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
from app.entity import get_active_entity_states

async def test_continuous_production():
    """🔄 연속 생산 테스트"""
    
    print("🔄 CONTINUOUS PRODUCTION TEST")
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
    
    print(f"📋 목표: 두 번째 제품까지 연속 생산 확인")
    print()
    
    # 스텝별 실행 (첫 번째 제품 + 두 번째 제품 시작까지)
    max_steps = 20
    processed_entities = 0
    
    for i in range(1, max_steps + 1):
        print(f"🔸 === STEP {i} ===")
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            print(f"⏰ Time: {result.time:.1f}s")
            print(f"📊 Processed: {result.entities_processed_total} (이전: {processed_entities})")
            print(f"🔢 Active: {len(result.active_entities)}")
            print(f"🔍 Signals: {result.current_signals}")
            
            # 엔티티 위치 표시
            if result.active_entities:
                for entity in result.active_entities:
                    if hasattr(entity, 'id') and hasattr(entity, 'current_block_id'):
                        location = entity.current_block_id
                        if hasattr(entity, 'current_block_name'):
                            location = f"{location} ({entity.current_block_name})"
                        print(f"  📦 Entity {entity.id}: {location}")
            
            # 처리된 엔티티 수 변화 감지
            if result.entities_processed_total > processed_entities:
                print(f"  🎉 제품 {result.entities_processed_total}번 처리 완료!")
                processed_entities = result.entities_processed_total
                
                # 두 번째 제품까지 확인하면 성공
                if processed_entities >= 2:
                    print(f"\n🎉 연속 생산 성공! {processed_entities}개 제품 처리 완료")
                    break
            
            # 활성 엔티티 수 변화 감지
            if len(result.active_entities) > 1:
                print(f"  🚀 연속 생산 감지: {len(result.active_entities)}개 엔티티 활성화")
            
            print()
                
        except Exception as e:
            print(f"❌ 스텝 {i} 오류: {e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n📋 테스트 결과:")
    print(f"  최종 시간: {result.time:.1f}초")
    print(f"  처리된 제품: {processed_entities}개")
    print(f"  활성 엔티티: {len(result.active_entities)}개")
    
    if processed_entities >= 2:
        print(f"  ✅ 연속 생산 성공!")
    elif processed_entities == 1:
        print(f"  ⚠️ 첫 제품만 처리됨 - 연속 생산 실패")
    else:
        print(f"  ❌ 제품 처리 실패")

if __name__ == "__main__":
    asyncio.run(test_continuous_production())