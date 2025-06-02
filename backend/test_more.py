#!/usr/bin/env python3
"""
더 상세한 디버깅 - 엔티티 처리 문제 파악
"""

import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup
from app.state_manager import get_current_signals

async def debug_entity_processing():
    """엔티티 처리 문제 디버깅"""
    
    print("🔍 ENTITY PROCESSING DEBUG")
    print("="*50)
    
    # 설정 로드
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # ID 변환
    for block in data["blocks"]:
        if isinstance(block["id"], int):
            block["id"] = str(block["id"])
    
    for conn in data["connections"]:
        for key in ["from_block_id", "to_block_id"]:
            if key in conn and isinstance(conn[key], (int, str)):
                conn[key] = str(conn[key])
    
    setup_data = {
        "blocks": data["blocks"],
        "connections": data["connections"],
        "initial_signals": {
            "공정1 load enable": True,
            "공정1 unload enable": False
        },
        "initial_entities": 1,
        "stop_time": 50
    }
    
    setup = SimulationSetup(**setup_data)
    
    # 리셋
    reset_simulation_state()
    
    print("📋 Debugging 20 steps to find entity processing issue...")
    
    for i in range(1, 21):
        result = await step_simulation(setup if i == 1 else None)
        
        print(f"\nStep {i:2d}:")
        print(f"   Time: {result.time:.1f}")
        print(f"   Active entities: {len(result.active_entities)}")
        
        for entity in result.active_entities:
            print(f"      Entity {entity.id}: Block {entity.current_block_id}")
        
        print(f"   Processed total: {result.entities_processed_total}")
        print(f"   Event: {result.event_description[:60]}...")
        
        # 엔티티가 배출 블록에 도달했는지 확인
        for entity in result.active_entities:
            if entity.current_block_id == 3:  # 배출 블록
                print(f"   🎯 Entity {entity.id} reached sink block (ID: 3)")
                
                # 다음 몇 스텝에서 처리되는지 확인
                for j in range(3):
                    next_result = await step_simulation()
                    print(f"      Step {i+j+1}: Processed={next_result.entities_processed_total}, Active={len(next_result.active_entities)}")
                    
                    if next_result.entities_processed_total > result.entities_processed_total:
                        print(f"      🎉 Entity processed at step {i+j+1}!")
                        return
                
                print(f"      ⚠️  Entity not processed after 3 additional steps")
                return
    
    print("\n❌ Entity never reached sink block in 20 steps")

if __name__ == "__main__":
    asyncio.run(debug_entity_processing())