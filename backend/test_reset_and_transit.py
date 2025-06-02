#!/usr/bin/env python3
"""
리셋 후 초기화 및 Transit 엔티티 가시성 테스트
"""

import asyncio
import json
import sys
sys.path.append('/home/arari123/project/simulation/backend')

from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup

async def test_reset_and_transit():
    """리셋 후 초기화 및 Transit 엔티티 테스트"""
    print("🧪 RESET AND TRANSIT ENTITY TEST")
    print("=" * 50)
    
    # Load configuration
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Convert IDs to strings
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
    
    print("🔄 Testing reset functionality...")
    
    # First simulation run
    print("\n--- First Run ---")
    reset_simulation_state()
    from app import state_manager
    state_manager.sim_env = None  # Ensure clean state
    
    for i in range(1, 10):
        try:
            result = await step_simulation(setup if i == 1 else None)
            print(f"   Step {i:2d}: Time={result.time:4.1f} | Active={len(result.active_entities)} | Event='{result.event_description[:40]}...'")
            
            # Check for transit entities
            for entity in result.active_entities:
                if entity.current_block_id == "transit":
                    print(f"      🚚 TRANSIT Entity: {entity.id}")
            
        except Exception as e:
            print(f"   ❌ Step {i} failed: {e}")
            break
    
    print("\n🔄 Testing reset and restart...")
    
    # Reset using the route method
    from app.routes.simulation import reset_simulation_endpoint
    try:
        await reset_simulation_endpoint()
        print("   ✅ Reset completed successfully")
    except Exception as e:
        print(f"   ❌ Reset failed: {e}")
        return False
    
    # Second simulation run
    print("\n--- Second Run (After Reset) ---")
    
    transit_entities_found = []
    
    for i in range(1, 15):
        try:
            result = await step_simulation(setup if i == 1 else None)
            print(f"   Step {i:2d}: Time={result.time:4.1f} | Active={len(result.active_entities)} | Event='{result.event_description[:40]}...'")
            
            # Check for transit entities
            for entity in result.active_entities:
                if entity.current_block_id == "transit":
                    transit_entities_found.append({
                        "step": i,
                        "time": result.time,
                        "entity_id": entity.id,
                        "description": result.event_description
                    })
                    print(f"      🚚 TRANSIT Entity: {entity.id} at step {i}")
            
            # Look for routing events
            if "routed" in result.event_description.lower():
                print(f"      📤 Routing detected: {result.event_description}")
            
            if result.entities_processed_total > 0:
                print(f"      🎉 Entity processed!")
                break
                
        except Exception as e:
            print(f"   ❌ Step {i} failed: {e}")
            break
    
    # Analysis
    print(f"\n📊 Analysis:")
    print(f"   Transit entities detected: {len(transit_entities_found)}")
    print(f"   Reset functionality: {'✅ WORKING' if i > 1 else '❌ FAILED'}")
    
    if transit_entities_found:
        print(f"   🚚 Transit entities found at steps: {[t['step'] for t in transit_entities_found]}")
        for transit in transit_entities_found:
            print(f"      Step {transit['step']}: Entity {transit['entity_id']} at time {transit['time']:.1f}")
    
    # Overall result
    reset_working = i > 1
    transit_working = len(transit_entities_found) > 0
    
    if reset_working and transit_working:
        status = "🎉 ALL TESTS PASSED"
        print(f"\n{status}")
        print(f"✅ Reset functionality working")
        print(f"✅ Transit entity detection working")
    elif reset_working:
        status = "⚠️  RESET OK, TRANSIT NEEDS CHECK"
        print(f"\n{status}")
        print(f"✅ Reset functionality working")
        print(f"⚠️  Transit entities may need verification")
    elif transit_working:
        status = "⚠️  TRANSIT OK, RESET NEEDS FIX"
        print(f"\n{status}")
        print(f"⚠️  Reset functionality needs attention")
        print(f"✅ Transit entity detection working")
    else:
        status = "❌ BOTH SYSTEMS NEED ATTENTION"
        print(f"\n{status}")
        print(f"❌ Reset functionality failed")
        print(f"❌ Transit entity detection failed")
    
    return {
        "reset_working": reset_working,
        "transit_working": transit_working,
        "transit_entities": transit_entities_found,
        "status": status
    }

if __name__ == "__main__":
    asyncio.run(test_reset_and_transit())