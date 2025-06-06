"""
Integer Variable Manager

This module manages integer variables separately from boolean signals.
It provides similar interface to SimpleSignalManager for consistency.
"""
from typing import Dict, Optional, List, Any
from app.core.signal_types import SignalType, TypedSignal


class IntegerVariableManager:
    """Manager for integer type variables"""
    
    def __init__(self):
        self.variables: Dict[str, int] = {}
        self.initial_variables: Dict[str, int] = {}
    
    def initialize_variables(self, variables: Dict[str, int]):
        """Initialize integer variables"""
        self.initial_variables = variables.copy()
        self.variables = variables.copy()
    
    def set_variable(self, variable_name: str, value: int):
        """Set integer variable value"""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Value must be an integer, not {type(value)}")
        self.variables[variable_name] = value
    
    def get_variable(self, variable_name: str, default: int = 0) -> int:
        """Get integer variable value"""
        return self.variables.get(variable_name, default)
    
    def get_all_variables(self) -> Dict[str, int]:
        """Get all integer variables"""
        return self.variables.copy()
    
    def reset(self):
        """Reset variables to initial values"""
        self.variables = self.initial_variables.copy()
    
    def add_variable(self, variable_name: str, initial_value: int = 0):
        """Add new integer variable"""
        if not isinstance(initial_value, int) or isinstance(initial_value, bool):
            raise ValueError(f"Initial value must be an integer, not {type(initial_value)}")
        if variable_name not in self.variables:
            self.variables[variable_name] = initial_value
            self.initial_variables[variable_name] = initial_value
    
    def has_variable(self, variable_name: str) -> bool:
        """Check if variable exists"""
        return variable_name in self.variables
    
    def perform_operation(self, variable_name: str, operation: str, operand: int) -> int:
        """Perform arithmetic operation on variable"""
        if variable_name not in self.variables:
            # Auto-create variable if it doesn't exist
            self.add_variable(variable_name, 0)
        
        current_value = self.variables[variable_name]
        
        if operation == "+=":
            new_value = current_value + operand
        elif operation == "-=":
            new_value = current_value - operand
        elif operation == "*=":
            new_value = current_value * operand
        elif operation == "/=":
            if operand == 0:
                raise ValueError("Division by zero")
            new_value = current_value // operand  # Integer division
        elif operation == "=":
            new_value = operand
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        self.set_variable(variable_name, new_value)
        return new_value
    
    def compare(self, variable_name: str, operator: str, operand: int) -> bool:
        """Compare variable with operand"""
        if variable_name not in self.variables:
            # Auto-create with default value if doesn't exist
            self.add_variable(variable_name, 0)
        
        value = self.variables[variable_name]
        
        if operator == ">":
            return value > operand
        elif operator == ">=":
            return value >= operand
        elif operator == "<":
            return value < operand
        elif operator == "<=":
            return value <= operand
        elif operator == "=":
            return value == operand
        elif operator == "!=":
            return value != operand
        else:
            raise ValueError(f"Unknown comparison operator: {operator}")
    
    def to_typed_signals(self) -> Dict[str, TypedSignal]:
        """Convert all variables to TypedSignal objects"""
        result = {}
        for name, value in self.variables.items():
            result[name] = TypedSignal(name, SignalType.INTEGER, value)
        return result
    
    def compare_value(self, variable_name: str, operator: str, comparison_value: int) -> bool:
        """Alias for compare method - for compatibility"""
        return self.compare(variable_name, operator, comparison_value)
    
    def list_variables(self) -> list:
        """Get list of all integer variables with their values"""
        return [
            {'name': name, 'type': 'integer', 'value': value}
            for name, value in self.variables.items()
        ]