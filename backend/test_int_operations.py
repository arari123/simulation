"""
Test integer variable operations in scripts
"""
import sys
sys.path.append('/home/arari123/project/simulation/backend')

from app.simple_simulation_engine import SimpleSimulationEngine


def test_int_operations():
    print("Testing integer variable operations...")
    
    engine = SimpleSimulationEngine()
    
    # Test configuration with integer operations
    config = {
        "globalSignals": [
            {"name": "start", "type": "boolean", "value": True},
            {"name": "counter", "type": "integer", "value": 0},
            {"name": "limit", "type": "integer", "value": 5}
        ],
        "blocks": [{
            "id": "test_block",
            "name": "TestBlock",
            "type": "process",
            "capacity": 10,
            "script": """int counter += 1
delay 0.1
int counter *= 2
delay 0.1
int counter -= 3
int limit = counter"""
        }],
        "connections": []
    }
    
    engine.setup_simulation(config)
    
    # Initial values
    assert engine.integer_manager.get_variable("counter") == 0
    assert engine.integer_manager.get_variable("limit") == 5
    print("✓ Initial integer values correct")
    
    # Create an entity in the block to trigger script execution
    from app.simple_entity import SimpleEntity
    test_block = engine.blocks["test_block"]
    entity = SimpleEntity()
    test_block.add_entity(entity)
    
    # Run simulation for a short time
    result = engine.step_simulation()
    
    # After first operations: counter was 0, +1 = 1, *2 = 2, -3 = -1
    # And limit = counter = -1
    expected_counter = -1
    expected_limit = -1
    
    actual_counter = engine.integer_manager.get_variable("counter")
    actual_limit = engine.integer_manager.get_variable("limit")
    
    print(f"Counter: {actual_counter} (expected: {expected_counter})")
    print(f"Limit: {actual_limit} (expected: {expected_limit})")
    
    assert actual_counter == expected_counter
    assert actual_limit == expected_limit
    print("✓ Integer operations executed correctly")
    
    # Check status includes integer variables
    status = engine.get_simulation_status()
    global_signals = status['globalSignals']
    
    # Find integer variables in globalSignals
    counter_signal = next(s for s in global_signals if s['name'] == 'counter')
    limit_signal = next(s for s in global_signals if s['name'] == 'limit')
    
    assert counter_signal['type'] == 'integer'
    assert counter_signal['value'] == expected_counter
    assert limit_signal['type'] == 'integer'
    assert limit_signal['value'] == expected_limit
    print("✓ Status includes integer variables with correct values")


def test_variable_reference():
    print("\nTesting variable references in operations...")
    
    engine = SimpleSimulationEngine()
    
    config = {
        "globalSignals": [
            {"name": "a", "type": "integer", "value": 10},
            {"name": "b", "type": "integer", "value": 5},
            {"name": "result", "type": "integer", "value": 0}
        ],
        "blocks": [{
            "id": "calc_block",
            "name": "Calculator",
            "script": """int result = a
int result += b
delay 0.1"""
        }],
        "connections": []
    }
    
    engine.setup_simulation(config)
    
    # Add entity to trigger script
    from app.simple_entity import SimpleEntity
    calc_block = engine.blocks["calc_block"]
    entity = SimpleEntity()
    calc_block.add_entity(entity)
    
    # Run simulation
    engine.step_simulation()
    
    # result = a (10), then result += b (10 + 5 = 15)
    assert engine.integer_manager.get_variable("result") == 15
    print("✓ Variable references work correctly")


def test_division_and_negative():
    print("\nTesting division and negative numbers...")
    
    engine = SimpleSimulationEngine()
    
    config = {
        "globalSignals": [
            {"name": "x", "type": "integer", "value": 20},
            {"name": "y", "type": "integer", "value": -5}
        ],
        "blocks": [{
            "id": "div_block",
            "name": "Division",
            "script": """int x /= 3
int y += 10
int y *= -2"""
        }],
        "connections": []
    }
    
    engine.setup_simulation(config)
    
    # Add entity
    div_block = engine.blocks["div_block"]
    entity = SimpleEntity()
    div_block.add_entity(entity)
    
    # Run
    engine.step_simulation()
    
    # x = 20 / 3 = 6 (integer division)
    # y = -5 + 10 = 5, then 5 * -2 = -10
    assert engine.integer_manager.get_variable("x") == 6
    assert engine.integer_manager.get_variable("y") == -10
    print("✓ Division and negative numbers work correctly")


if __name__ == "__main__":
    try:
        test_int_operations()
        test_variable_reference()
        test_division_and_negative()
        print("\n✅ All integer operation tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)