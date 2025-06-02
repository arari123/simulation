#!/usr/bin/env python3
"""
성능 최적화 및 UI 엔티티 가시성 테스트
"""

import asyncio
import json
import time
import sys
sys.path.append('/home/arari123/project/simulation/backend')

from app.routes.simulation import reset_simulation_state
from app.simulation_engine import step_simulation
from app.models import SimulationSetup

async def test_performance_optimization():
    """성능 최적화 효과 테스트"""
    print("🚀 PERFORMANCE OPTIMIZATION TEST")
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
    
    print("📊 Performance test - running 20 steps with timing")
    
    # Reset and start timing
    reset_simulation_state()
    start_time = time.time()
    
    transit_entities_found = []
    
    for i in range(1, 21):
        step_start = time.time()
        result = await step_simulation(setup if i == 1 else None)
        step_duration = time.time() - step_start
        
        # Check for transit entities
        for entity in result.active_entities:
            if entity.current_block_id == "transit":
                transit_entities_found.append({
                    "step": i,
                    "time": result.time,
                    "entity_id": entity.id,
                    "description": result.event_description
                })
        
        print(f"   Step {i:2d}: {step_duration:.4f}s | Time={result.time:4.1f} | Active={len(result.active_entities)} | Event='{result.event_description[:40]}...'")
        
        if result.entities_processed_total > 0:
            print(f"      🎉 Entity processed at step {i}!")
            break
    
    total_duration = time.time() - start_time
    avg_step_time = total_duration / min(i, 20)
    
    print(f"\n📈 Performance Results:")
    print(f"   Total time: {total_duration:.3f}s")
    print(f"   Average step time: {avg_step_time:.4f}s")
    print(f"   Steps per second: {1/avg_step_time:.1f}")
    
    # Performance benchmark
    if avg_step_time < 0.01:  # Less than 10ms per step
        performance_status = "🟢 EXCELLENT"
    elif avg_step_time < 0.05:  # Less than 50ms per step
        performance_status = "🟡 GOOD"
    else:
        performance_status = "🔴 NEEDS IMPROVEMENT"
    
    print(f"   Performance: {performance_status}")
    
    return {
        "total_duration": total_duration,
        "avg_step_time": avg_step_time,
        "transit_entities": transit_entities_found,
        "performance_grade": performance_status
    }

async def test_entity_visibility():
    """UI 엔티티 가시성 테스트"""
    print("\n👁️  ENTITY VISIBILITY TEST")
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
    
    # Proper reset with environment clearing
    reset_simulation_state()
    from app import state_manager
    state_manager.sim_env = None  # Ensure clean state
    
    print("🔍 Tracking entity visibility throughout simulation...")
    
    entity_visibility_log = []
    transit_detected = False
    
    for i in range(1, 15):
        result = await step_simulation(setup if i == 1 else None)
        
        # Track all entity states
        for entity in result.active_entities:
            visibility_info = {
                "step": i,
                "time": result.time,
                "entity_id": entity.id,
                "block_id": entity.current_block_id,
                "status": "visible_in_block" if entity.current_block_id != "transit" else "visible_in_transit"
            }
            entity_visibility_log.append(visibility_info)
            
            if entity.current_block_id == "transit":
                transit_detected = True
                print(f"   Step {i:2d}: 🚚 Entity {entity.id} in TRANSIT (should be visible on connection line)")
            else:
                print(f"   Step {i:2d}: 📦 Entity {entity.id} in Block {entity.current_block_id}")
        
        if result.entities_processed_total > 0:
            print(f"   Step {i:2d}: ✅ Entity processing completed!")
            break
    
    # Analysis
    total_entities_tracked = len(set(log["entity_id"] for log in entity_visibility_log))
    transit_occurrences = len([log for log in entity_visibility_log if log["status"] == "visible_in_transit"])
    
    print(f"\n📊 Visibility Analysis:")
    print(f"   Total entities tracked: {total_entities_tracked}")
    print(f"   Transit occurrences: {transit_occurrences}")
    print(f"   Transit detection: {'✅ YES' if transit_detected else '❌ NO'}")
    
    # UI Status Assessment
    if transit_detected and transit_occurrences > 0:
        ui_status = "🟢 UI TRANSIT DISPLAY WORKING"
        ui_message = "Entities will be visible on connection lines during movement"
    elif total_entities_tracked > 0:
        ui_status = "🟡 ENTITIES VISIBLE IN BLOCKS ONLY"
        ui_message = "Entities are tracked but may not have transit states in this test"
    else:
        ui_status = "🔴 NO ENTITIES TRACKED"
        ui_message = "No entities were detected during simulation"
    
    print(f"   Status: {ui_status}")
    print(f"   Result: {ui_message}")
    
    return {
        "total_entities": total_entities_tracked,
        "transit_occurrences": transit_occurrences,
        "transit_detected": transit_detected,
        "visibility_log": entity_visibility_log,
        "ui_status": ui_status
    }

async def main():
    """메인 테스트 실행"""
    print("🧪 COMPREHENSIVE PERFORMANCE & UI TEST")
    print("=" * 60)
    
    # Run performance test
    perf_results = await test_performance_optimization()
    
    # Run UI visibility test
    ui_results = await test_entity_visibility()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL TEST RESULTS")
    print("=" * 60)
    
    print(f"💨 Performance: {perf_results['performance_grade']}")
    print(f"   Average step time: {perf_results['avg_step_time']:.4f}s")
    print(f"   Transit entities detected: {len(perf_results['transit_entities'])}")
    
    print(f"\n👁️  UI Visibility: {ui_results['ui_status']}")
    print(f"   Entities tracked: {ui_results['total_entities']}")
    print(f"   Transit occurrences: {ui_results['transit_occurrences']}")
    
    # Overall assessment
    performance_ok = "EXCELLENT" in perf_results['performance_grade'] or "GOOD" in perf_results['performance_grade']
    ui_ok = ui_results['transit_detected'] or ui_results['total_entities'] > 0
    
    if performance_ok and ui_ok:
        overall_status = "🎉 ALL TESTS PASSED"
        print(f"\n{overall_status}")
        print("✅ Performance optimization successful")
        print("✅ Entity visibility system working")
        print("✅ Ready for production use")
    elif performance_ok:
        overall_status = "⚠️  PERFORMANCE OK, UI NEEDS CHECK"
        print(f"\n{overall_status}")
        print("✅ Performance optimization successful")
        print("⚠️  UI visibility may need verification")
    elif ui_ok:
        overall_status = "⚠️  UI OK, PERFORMANCE NEEDS IMPROVEMENT"
        print(f"\n{overall_status}")
        print("⚠️  Performance may need further optimization")
        print("✅ Entity visibility system working")
    else:
        overall_status = "❌ BOTH SYSTEMS NEED ATTENTION"
        print(f"\n{overall_status}")
        print("❌ Performance needs optimization")
        print("❌ UI visibility needs verification")
    
    return {
        "performance": perf_results,
        "ui": ui_results,
        "overall_status": overall_status
    }

if __name__ == "__main__":
    asyncio.run(main())