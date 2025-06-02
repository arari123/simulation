#!/usr/bin/env python3
"""
Test script to verify:
1. Reset → Step sequence works correctly
2. UI type display issue is fixed
"""

import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup
from app.state_manager import get_current_signals

async def test_reset_and_ui_fix():
    """Test reset functionality and UI type fix"""
    
    print("🧪 TESTING RESET + UI TYPE FIX")
    print("="*60)
    
    # Load configuration
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Check if UI fix is applied in base.json
    print("📋 Checking base.json for UI type fix:")
    for block in data["blocks"]:
        if block["name"] == "공정1":
            for cp in block.get("connectionPoints", []):
                if cp["name"] == "L":
                    for action in cp.get("actions", []):
                        print(f"   🔍 공정1.L action: {action['name']} (type: {action['type']})")
                        if action['type'] == 'block_entry':
                            print(f"   ✅ SUCCESS: UI type fixed to 'block_entry'")
                        elif action['type'] == 'conditional_branch':
                            print(f"   ❌ ISSUE: Still showing as 'conditional_branch'")
    
    # Reset simulation
    print(f"\n🔄 Testing Reset functionality:")
    reset_simulation_state()
    
    # Convert IDs to strings
    for block in data["blocks"]:
        if isinstance(block["id"], int):
            block["id"] = str(block["id"])
    
    for conn in data["connections"]:
        for key in ["from_block_id", "to_block_id"]:
            if key in conn and isinstance(conn[key], (int, str)):
                conn[key] = str(conn[key])
    
    # Prepare setup data
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
    
    print(f"✅ Setup prepared with {len(setup.blocks)} blocks")
    
    # Test first few steps after reset
    print(f"\n⚡ Testing Step execution after reset:")
    
    for i in range(1, 6):
        print(f"\n--- Step {i} ---")
        
        try:
            # First step needs setup
            result = await step_simulation(setup if i == 1 else None)
            
            print(f"Time: {result.time:.2f}")
            print(f"Event: {result.event_description}")
            
            # Check if we have active entities
            if result.active_entities:
                print(f"Active entities: {len(result.active_entities)}")
                for entity in result.active_entities:
                    print(f"  - Entity {entity.id}: Block {entity.current_block_id}")
            else:
                print(f"No active entities")
            
            # Check processed entities
            if result.entities_processed_total > 0:
                print(f"✅ Entities processed: {result.entities_processed_total}")
            
            # If time progresses, that's good
            if i > 1 and result.time > 0:
                print(f"✅ Time is progressing: {result.time}")
                break
            
        except Exception as e:
            print(f"❌ Error in step {i}: {e}")
            break
    
    print(f"\n🎯 FINAL RESULTS:")
    
    # Check if the issues are resolved
    ui_fix_applied = False
    reset_works = False
    
    # Check UI fix
    for block in data["blocks"]:
        if block["name"] == "공정1":
            for cp in block.get("connectionPoints", []):
                if cp["name"] == "L":
                    for action in cp.get("actions", []):
                        if action['type'] == 'block_entry':
                            ui_fix_applied = True
    
    # Check reset functionality (if we got past step 1 successfully)
    try:
        result = await step_simulation()
        reset_works = True
    except:
        reset_works = False
    
    print(f"   ✅ UI Type Fix Applied: {'YES' if ui_fix_applied else 'NO'}")
    print(f"   ✅ Reset → Step Works: {'YES' if reset_works else 'NO'}")
    
    if ui_fix_applied and reset_works:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"   - 공정1.L action now shows as 'block_entry' instead of 'conditional_branch'")
        print(f"   - Reset → Step sequence works without empty schedule error")
    else:
        print(f"\n❌ SOME TESTS FAILED - Additional fixes needed")

if __name__ == "__main__":
    asyncio.run(test_reset_and_ui_fix())