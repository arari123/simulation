import asyncio
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup, ProcessBlockConfig, ConnectionConfig
import json

async def test_capacity_limit_issue():
    """투입 블록의 최대 수량 제한 문제를 테스트"""
    
    print("=== 투입 블록 최대 수량 제한 문제 테스트 ===")
    
    # 1. base.json 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    reset_simulation_state()
    
    # 2. 시뮬레이션 설정
    blocks = []
    for block_data in data["blocks"]:
        block_config = ProcessBlockConfig(
            id=str(block_data["id"]),
            name=block_data["name"],
            actions=block_data["actions"],
            maxCapacity=block_data.get("maxCapacity", 1),  # 중요: maxCapacity 필드
            connectionPoints=block_data.get("connectionPoints", [])
        )
        blocks.append(block_config)
        print(f"블록 {block_config.name}({block_config.id}) - maxCapacity: {block_config.maxCapacity}")
    
    connections = []
    for conn_data in data["connections"]:
        conn_config = ConnectionConfig(
            from_block_id=str(conn_data["from_block_id"]),
            from_connector_id=conn_data["from_connector_id"],
            to_block_id=str(conn_data["to_block_id"]),
            to_connector_id=conn_data["to_connector_id"]
        )
        connections.append(conn_config)
    
    setup = SimulationSetup(
        blocks=blocks,
        connections=connections,
        initial_entities=5,  # 5개 제품만 생성
        initial_signals=data.get("globalSignals", {})
    )
    
    print(f"\n=== 시뮬레이션 시작 (초기 엔티티: {setup.initial_entities}개) ===")
    
    # 3. 시뮬레이션 실행 - 20스텝 실행하여 문제 확인
    for i in range(1, 21):
        print(f"\n=== {i}번째 스텝 ===")
        try:
            result = await step_simulation(setup if i == 1 else None)
            print(f"시간: {result.time}")
            print(f"이벤트: {result.event_description}")
            print(f"처리된 총 엔티티 수: {result.entities_processed_total}")
            print(f"활성 엔티티 수: {len(result.active_entities)}")
            
            # 활성 엔티티 상세 정보
            if result.active_entities:
                print("활성 엔티티 위치:")
                for entity in result.active_entities:
                    print(f"  - {entity.entity_id}: 블록 {entity.current_block_id} ({entity.current_block_name})")
            
            # 블록별 엔티티 수 계산
            block_entity_counts = {}
            for entity in result.active_entities:
                block_id = entity.current_block_id
                if block_id not in block_entity_counts:
                    block_entity_counts[block_id] = 0
                block_entity_counts[block_id] += 1
            
            # 용량 초과 체크
            for block in blocks:
                entity_count = block_entity_counts.get(block.id, 0)
                if entity_count > block.maxCapacity:
                    print(f"🚨 용량 초과 발견! 블록 {block.name}({block.id}): {entity_count}/{block.maxCapacity}")
                elif entity_count > 0:
                    print(f"📦 블록 {block.name}({block.id}): {entity_count}/{block.maxCapacity}")
            
            # 배출된 제품 확인
            if result.entities_processed_total > 0:
                print(f"✅ 배출된 제품: {result.entities_processed_total}개")
            
        except Exception as e:
            print(f"❌ 오류: {e}")
            break
    
    print(f"\n=== 테스트 완료 ===")
    print("문제점:")
    print("1. 투입 블록(maxCapacity=1)에 여러 제품이 동시에 있을 수 있음")
    print("2. maxCapacity 체크 로직이 백엔드에 구현되지 않음")
    print("3. 소스 블록에서 용량 제한 없이 계속 제품 생성")

if __name__ == "__main__":
    asyncio.run(test_capacity_limit_issue()) 