#!/usr/bin/env python3
"""
Test script to verify that connector actions execute in sequence
even when routing actions are in the middle of the sequence.

This test specifically checks that the 공정1.R connector executes all actions:
1. 공정1 unload enable = true
2. go to 배출.L,3  
3. 공정1 unload enable = false
4. 공정1 load enable = true
"""

import asyncio
import json
from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup
from app.state_manager import get_current_signals

async def test_connector_action_sequence():
    """Test that all connector actions execute even after routing"""
    
    print("🧪 Testing Connector Action Sequence")
    print("="*60)
    
    # 1. Load configuration
    with open("../base.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 2. Reset simulation
    reset_simulation_state()
    
    # 3. Convert IDs to strings (required by Pydantic models)
    for block in data["blocks"]:
        if isinstance(block["id"], int):
            block["id"] = str(block["id"])
    
    for conn in data["connections"]:
        for key in ["from_block_id", "to_block_id"]:
            if key in conn and isinstance(conn[key], (int, str)):
                conn[key] = str(conn[key])
    
    # 4. Prepare setup data
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
    
    print(f"📊 Initial signals: {setup.initial_signals}")
    print(f"📦 Expected sequence for 공정1.R:")
    print(f"   1. 공정1 unload enable = true")
    print(f"   2. go to 배출.L,3 (with 3s delay)")
    print(f"   3. 공정1 unload enable = false")
    print(f"   4. 공정1 load enable = true")
    print()
    
    # 5. Execute steps until we reach the connector actions
    max_steps = 20
    step_count = 0
    
    for i in range(1, max_steps + 1):
        print(f"=== Step {i} ===")
        
        try:
            # First step needs setup, subsequent ones don't
            result = await step_simulation(setup if i == 1 else None)
            step_count += 1
            
            print(f"Time: {result.time:.2f}")
            print(f"Event: {result.event_description}")
            
            # Check current signals
            current_signals = get_current_signals()
            print(f"Current signals: {current_signals}")
            
            # Check entities
            if result.active_entities:
                for entity in result.active_entities:
                    print(f"Entity {entity.id}: Block {entity.current_block_id}")
            
            # 🎯 Key test: Monitor signal changes during connector execution
            if "공정1 unload enable" in current_signals:
                unload_enable = current_signals["공정1 unload enable"]
                load_enable = current_signals.get("공정1 load enable", True)
                
                print(f"🔍 Signal Check:")
                print(f"   - 공정1 unload enable: {unload_enable}")
                print(f"   - 공정1 load enable: {load_enable}")
                
                # Check if we're in the middle of connector sequence
                if unload_enable and not load_enable:
                    print(f"⚠️  WARNING: Unload enabled but load disabled - this should be temporary!")
                elif not unload_enable and load_enable:
                    print(f"✅ GOOD: Final state - unload disabled, load enabled")
            
            # Check if entity moved to 배출
            if result.active_entities:
                for entity in result.active_entities:
                    if entity.current_block_id == 3:  # 배출 block
                        print(f"🎉 SUCCESS: Entity {entity.id} reached 배출 block!")
                        print(f"📊 Final signal states after routing:")
                        final_signals = get_current_signals()
                        for signal_name, signal_info in final_signals.items():
                            print(f"   - {signal_name}: {signal_info.get('value', 'Unknown')}")
                        
                        # Verify expected final state
                        expected_unload = False  # Should be False after sequence
                        expected_load = True     # Should be True after sequence
                        
                        actual_unload = final_signals.get("공정1 unload enable", {}).get("value", None)
                        actual_load = final_signals.get("공정1 load enable", {}).get("value", None)
                        
                        print(f"\n🎯 TEST RESULTS:")
                        print(f"Expected - unload enable: {expected_unload}, load enable: {expected_load}")
                        print(f"Actual   - unload enable: {actual_unload}, load enable: {actual_load}")
                        
                        if actual_unload == expected_unload and actual_load == expected_load:
                            print(f"✅ TEST PASSED: All connector actions executed correctly!")
                            print(f"✅ VERIFICATION: Routing action did NOT interrupt signal actions")
                        else:
                            print(f"❌ TEST FAILED: Signal states don't match expected values")
                            print(f"❌ ISSUE: Some connector actions were skipped after routing")
                        
                        return
            
            # Stop if entities are processed
            if result.entities_processed_total > 0:
                print(f"✅ Entities processed: {result.entities_processed_total}")
                break
                
        except Exception as e:
            print(f"❌ Error in step {i}: {e}")
            break
        
        print()
    
    print(f"\n📈 Test completed after {step_count} steps")
    
    # Final signal check
    final_signals = get_current_signals()
    print(f"📊 Final signals:")
    for signal_name, signal_info in final_signals.items():
        print(f"   - {signal_name}: {signal_info.get('value', 'Unknown')}")

if __name__ == "__main__":
    asyncio.run(test_connector_action_sequence())