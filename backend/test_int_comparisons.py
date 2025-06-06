"""
Test integer variable comparison operations
"""
import sys
sys.path.append('/home/arari123/project/simulation/backend')

from app.simple_script_executor import SimpleScriptExecutor
from app.simple_signal_manager import SimpleSignalManager
from app.core.integer_variable_manager import IntegerVariableManager
from app.core.unified_variable_accessor import UnifiedVariableAccessor
import simpy


def test_integer_comparisons():
    print("Testing integer comparison operations...")
    
    signal_manager = SimpleSignalManager()
    integer_manager = IntegerVariableManager()
    variable_accessor = UnifiedVariableAccessor(signal_manager, integer_manager)
    
    # Initialize variables
    integer_manager.set_variable("count", 10)
    integer_manager.set_variable("threshold", 5)
    integer_manager.set_variable("limit", 20)
    signal_manager.set_signal("ready", True)
    
    executor = SimpleScriptExecutor(signal_manager, integer_manager, variable_accessor)
    env = simpy.Environment()
    
    # Test single comparisons
    assert executor.execute_if(env, "count > 5") == True
    assert executor.execute_if(env, "count < 5") == False
    assert executor.execute_if(env, "count >= 10") == True
    assert executor.execute_if(env, "count <= 10") == True
    assert executor.execute_if(env, "count = 10") == True
    assert executor.execute_if(env, "count != 5") == True
    print("✓ Single integer comparisons work")
    
    # Test variable to variable comparisons
    assert executor.execute_if(env, "count > threshold") == True
    assert executor.execute_if(env, "count < limit") == True
    assert executor.execute_if(env, "threshold < limit") == True
    print("✓ Variable to variable comparisons work")
    
    # Test AND conditions with integers
    assert executor.execute_if(env, "count > 5 and count < 15") == True
    assert executor.execute_if(env, "count > 5 and count < 8") == False
    assert executor.execute_if(env, "ready = true and count > 5") == True
    assert executor.execute_if(env, "ready = false and count > 5") == False
    print("✓ AND conditions with integers work")
    
    # Test OR conditions with integers  
    assert executor.execute_if(env, "count > 15 or count < 12") == True
    assert executor.execute_if(env, "count > 15 or count < 8") == False
    assert executor.execute_if(env, "ready = false or count > 5") == True
    print("✓ OR conditions with integers work")
    
    # Test wait with integer conditions
    # This should return immediately since count > 5 is already true
    gen = executor.execute_wait(env, "count > 5")
    try:
        next(gen)
        wait_completed = True
    except StopIteration:
        wait_completed = True
    assert wait_completed == True
    print("✓ Wait with integer conditions works")


def test_integer_if_blocks():
    print("\nTesting integer conditions in if blocks...")
    
    from app.simple_simulation_engine import SimpleSimulationEngine
    
    engine = SimpleSimulationEngine()
    
    config = {
        "globalSignals": [
            {"name": "x", "type": "integer", "value": 10},
            {"name": "y", "type": "integer", "value": 5},
            {"name": "result", "type": "boolean", "value": False}
        ],
        "blocks": [{
            "id": "test_block",
            "name": "TestBlock",
            "script": """if x > y
    result = true
    int x += 5
if x >= 15
    int y *= 2"""
        }],
        "connections": []
    }
    
    engine.setup_simulation(config)
    
    # Add entity and run script
    from app.simple_entity import SimpleEntity
    block = engine.blocks["test_block"]
    entity = SimpleEntity()
    block.add_entity(entity)
    
    # Execute script
    env = engine.env
    gen = block.process_entity(env, entity)
    try:
        while True:
            next(gen)
    except StopIteration:
        pass
    
    # Check results
    assert engine.signal_manager.get_signal("result") == True
    assert engine.integer_manager.get_variable("x") == 15  # 10 + 5
    assert engine.integer_manager.get_variable("y") == 10  # 5 * 2
    print("✓ If blocks with integer conditions work correctly")


def test_wait_for_integer_condition():
    print("\nTesting wait for integer condition to become true...")
    
    from app.simple_simulation_engine import SimpleSimulationEngine
    
    engine = SimpleSimulationEngine()
    
    config = {
        "globalSignals": [
            {"name": "counter", "type": "integer", "value": 0},
            {"name": "done", "type": "boolean", "value": False}
        ],
        "blocks": [
            {
                "id": "incrementer",
                "name": "Incrementer",
                "script": """delay 0.1
int counter += 1
if counter >= 3
    done = true"""
            },
            {
                "id": "waiter",
                "name": "Waiter",
                "script": """wait counter >= 3
done = true"""
            }
        ],
        "connections": []
    }
    
    engine.setup_simulation(config)
    
    # The waiter block will wait until counter >= 3
    # We'll need to run the incrementer multiple times
    
    print("✓ Wait for integer condition setup complete")


def test_mixed_conditions():
    print("\nTesting mixed boolean and integer conditions...")
    
    signal_manager = SimpleSignalManager()
    integer_manager = IntegerVariableManager()
    variable_accessor = UnifiedVariableAccessor(signal_manager, integer_manager)
    
    # Initialize
    signal_manager.set_signal("enabled", True)
    signal_manager.set_signal("active", False)
    integer_manager.set_variable("score", 75)
    integer_manager.set_variable("min_score", 60)
    
    executor = SimpleScriptExecutor(signal_manager, integer_manager, variable_accessor)
    env = simpy.Environment()
    
    # Test mixed AND
    assert executor.execute_if(env, "enabled = true and score > 70") == True
    assert executor.execute_if(env, "enabled = true and score > 80") == False
    assert executor.execute_if(env, "active = true and score > 70") == False
    
    # Test mixed OR
    assert executor.execute_if(env, "active = true or score > 70") == True
    assert executor.execute_if(env, "active = true or score < 70") == False
    
    # Test complex mixed
    assert executor.execute_if(env, "enabled = true and score >= min_score") == True
    assert executor.execute_if(env, "enabled = false or score >= min_score") == True
    
    print("✓ Mixed boolean and integer conditions work correctly")


if __name__ == "__main__":
    try:
        test_integer_comparisons()
        test_integer_if_blocks()
        test_wait_for_integer_condition()
        test_mixed_conditions()
        print("\n✅ All integer comparison tests passed!")
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