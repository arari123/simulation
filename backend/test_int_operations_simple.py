"""
Simple test for integer variable operations
"""
import sys
sys.path.append('/home/arari123/project/simulation/backend')

from app.core.integer_variable_manager import IntegerVariableManager
from app.core.signal_types import SignalType


def test_integer_manager():
    print("Testing IntegerVariableManager directly...")
    
    manager = IntegerVariableManager()
    
    # Test initialization
    manager.set_variable("counter", 10)
    manager.set_variable("total", 0)
    
    assert manager.get_variable("counter") == 10
    assert manager.get_variable("total") == 0
    print("✓ Variable initialization works")
    
    # Test arithmetic operations
    result = manager.perform_operation("counter", "+=", 5)
    assert result == 15
    assert manager.get_variable("counter") == 15
    print("✓ Addition works")
    
    result = manager.perform_operation("counter", "-=", 3)
    assert result == 12
    assert manager.get_variable("counter") == 12
    print("✓ Subtraction works")
    
    result = manager.perform_operation("counter", "*=", 2)
    assert result == 24
    assert manager.get_variable("counter") == 24
    print("✓ Multiplication works")
    
    result = manager.perform_operation("counter", "/=", 4)
    assert result == 6
    assert manager.get_variable("counter") == 6
    print("✓ Division works")
    
    # Test assignment
    result = manager.perform_operation("total", "=", 100)
    assert result == 100
    assert manager.get_variable("total") == 100
    print("✓ Assignment works")
    
    # Test comparison
    assert manager.compare_value("total", ">", 50) == True
    assert manager.compare_value("total", "<", 200) == True
    assert manager.compare_value("total", "=", 100) == True
    assert manager.compare_value("total", "!=", 50) == True
    assert manager.compare_value("total", ">=", 100) == True
    assert manager.compare_value("total", "<=", 100) == True
    print("✓ Comparisons work")
    
    # Test variable list
    vars_list = manager.list_variables()
    assert len(vars_list) == 2
    print("✓ Variable listing works")


def test_script_executor():
    print("\nTesting script executor with integer operations...")
    
    from app.simple_script_executor import SimpleScriptExecutor
    from app.simple_signal_manager import SimpleSignalManager
    from app.core.unified_variable_accessor import UnifiedVariableAccessor
    import simpy
    
    signal_manager = SimpleSignalManager()
    integer_manager = IntegerVariableManager()
    variable_accessor = UnifiedVariableAccessor(signal_manager, integer_manager)
    
    # Initialize some variables
    integer_manager.set_variable("x", 10)
    integer_manager.set_variable("y", 5)
    
    executor = SimpleScriptExecutor(signal_manager, integer_manager, variable_accessor)
    
    # Test parsing
    cmd, params = executor.parse_script_line("int x += 15")
    assert cmd == "int_operation"
    assert params['var_name'] == "x"
    assert params['operator'] == "+="
    assert params['value'] == "15"
    print("✓ Script parsing works")
    
    # Test execution
    env = simpy.Environment()
    
    # Execute addition
    gen = executor.execute_int_operation(env, {
        'var_name': 'x',
        'operator': '+=',
        'value': '15'
    })
    # Run the generator
    try:
        next(gen)
    except StopIteration:
        pass
    
    assert integer_manager.get_variable("x") == 25
    print("✓ Script execution works")
    
    # Test variable reference
    gen = executor.execute_int_operation(env, {
        'var_name': 'x',
        'operator': '=',
        'value': 'y'
    })
    try:
        next(gen)
    except StopIteration:
        pass
    
    assert integer_manager.get_variable("x") == 5
    print("✓ Variable reference works")


if __name__ == "__main__":
    try:
        test_integer_manager()
        test_script_executor()
        print("\n✅ All tests passed!")
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