#!/usr/bin/env python3
"""
Simple test to verify connector action sequence fix.
This test confirms that routing actions don't interrupt subsequent actions.
"""

import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup
from app.state_manager import get_current_signals

async def test_simple_verification():
    """Simple test for connector action sequence"""
    
    print("🧪 CONNECTOR ACTION SEQUENCE VERIFICATION")
    print("="*60)
    
    # Load and prepare configuration
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    reset_simulation_state()
    
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
    
    print("📦 Testing sequence in 공정1.R connector:")
    print("   1. 공정1 unload enable = true")
    print("   2. go to 배출.L,3 (route with 3s delay)")
    print("   3. 공정1 unload enable = false")
    print("   4. 공정1 load enable = true")
    print()
    
    # Track key state changes
    found_unload_true = False
    found_both_signals_set = False
    entity_routed = False
    
    # Execute simulation steps
    for i in range(1, 25):
        try:
            result = await step_simulation(setup if i == 1 else None)
            
            # Get current signals (handle both dict and bool formats)
            current_signals = get_current_signals()
            unload_val = current_signals.get("공정1 unload enable", False)
            load_val = current_signals.get("공정1 load enable", True)
            
            # Extract actual boolean values
            if isinstance(unload_val, dict):
                unload_val = unload_val.get('value', False)
            if isinstance(load_val, dict):
                load_val = load_val.get('value', True)
            
            # Track progression
            if unload_val == True and not found_unload_true:
                found_unload_true = True
                print(f"✅ Step {i}: Found 'unload enable = true' signal")
            
            if unload_val == False and load_val == True and found_unload_true and not found_both_signals_set:
                found_both_signals_set = True
                print(f"✅ Step {i}: Both signals correctly set (unload=false, load=true)")
                print(f"   ⭐ SUCCESS: All connector actions executed even after routing!")
            
            # Check for entity routing
            if result.active_entities:
                for entity in result.active_entities:
                    if entity.current_block_id == 3 and not entity_routed:  # 배출 block
                        entity_routed = True
                        print(f"✅ Step {i}: Entity {entity.id} successfully routed to 배출 block")
            
            # Exit if entity processed
            if result.entities_processed_total > 0:
                print(f"✅ Step {i}: Entity processed - simulation complete")
                break
                
        except Exception as e:
            print(f"❌ Error in step {i}: {e}")
            break
    
    # Final verification
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   Unload signal set to true: {'✅' if found_unload_true else '❌'}")
    print(f"   Both signals properly restored: {'✅' if found_both_signals_set else '❌'}")
    print(f"   Entity successfully routed: {'✅' if entity_routed else '❌'}")
    
    if found_unload_true and found_both_signals_set and entity_routed:
        print(f"\n🎉 TEST PASSED: Connector actions execute correctly after routing!")
        print(f"🎉 FIX VERIFIED: Signal actions after 'go to 배출.L,3' are executed!")
    else:
        print(f"\n❌ TEST FAILED: Some connector actions were skipped")
    
    # Show final signal states
    final_signals = get_current_signals()
    print(f"\n📊 Final signal states:")
    for name, value in final_signals.items():
        if isinstance(value, dict):
            actual_value = value.get('value', 'Unknown')
        else:
            actual_value = value
        print(f"   {name}: {actual_value}")

if __name__ == "__main__":
    asyncio.run(test_simple_verification())