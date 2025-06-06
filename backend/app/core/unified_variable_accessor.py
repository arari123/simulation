"""
Unified Variable Accessor

This module provides a unified interface to access both boolean signals 
and integer variables through a single API.
"""
from typing import Dict, Union, Any, Optional, Tuple
from app.simple_signal_manager import SimpleSignalManager
from app.core.integer_variable_manager import IntegerVariableManager
from app.core.signal_types import SignalType, TypedSignal


class UnifiedVariableAccessor:
    """Unified interface for accessing all types of variables"""
    
    def __init__(self, signal_manager: SimpleSignalManager, integer_manager: IntegerVariableManager):
        self.signal_manager = signal_manager
        self.integer_manager = integer_manager
    
    def get_value(self, name: str) -> Union[bool, int, None]:
        """Get value of any variable by name"""
        # Check integer variables first (they can be auto-created)
        if self.integer_manager.has_variable(name):
            return self.integer_manager.get_variable(name)
        
        # Check boolean signals
        if name in self.signal_manager.signals:
            return self.signal_manager.get_signal(name)
        
        return None
    
    def set_value(self, name: str, value: Union[bool, int], signal_type: Optional[SignalType] = None):
        """Set value of any variable"""
        if signal_type is None:
            # Infer type from value
            signal_type = SignalType.from_value(value)
        
        if signal_type == SignalType.BOOLEAN:
            self.signal_manager.set_signal(name, value)
        elif signal_type == SignalType.INTEGER:
            self.integer_manager.set_variable(name, value)
        else:
            raise ValueError(f"Unknown signal type: {signal_type}")
    
    def get_type(self, name: str) -> Optional[SignalType]:
        """Get type of a variable"""
        if self.integer_manager.has_variable(name):
            return SignalType.INTEGER
        elif name in self.signal_manager.signals:
            return SignalType.BOOLEAN
        return None
    
    def has_variable(self, name: str) -> bool:
        """Check if variable exists"""
        return (name in self.signal_manager.signals or 
                self.integer_manager.has_variable(name))
    
    def get_all_variables(self) -> Dict[str, TypedSignal]:
        """Get all variables as TypedSignal objects"""
        result = {}
        
        # Add boolean signals
        for name, value in self.signal_manager.get_all_signals().items():
            result[name] = TypedSignal(name, SignalType.BOOLEAN, value)
        
        # Add integer variables
        result.update(self.integer_manager.to_typed_signals())
        
        return result
    
    def initialize_from_config(self, config_data: list):
        """Initialize from frontend config format"""
        boolean_signals = {}
        integer_variables = {}
        
        for item in config_data:
            name = item.get("name")
            signal_type = item.get("type", "boolean")  # Default to boolean for backward compatibility
            
            if signal_type == "boolean":
                # Handle boolean value
                value = item.get("value", False)
                if isinstance(value, str):
                    value = value.lower() == "true"
                boolean_signals[name] = bool(value)
                
            elif signal_type == "integer":
                # Handle integer value
                value = item.get("value", 0)
                if isinstance(value, str):
                    value = int(value)
                integer_variables[name] = int(value)
        
        # Initialize managers
        self.signal_manager.initialize_signals(boolean_signals)
        self.integer_manager.initialize_variables(integer_variables)
    
    def to_config_format(self) -> list:
        """Convert to frontend config format"""
        result = []
        
        # Add boolean signals
        for name, value in self.signal_manager.get_all_signals().items():
            result.append({
                "id": f"signal_{name}",
                "name": name,
                "type": "boolean",
                "value": value,
                "initialValue": self.signal_manager.initial_signals.get(name, False)
            })
        
        # Add integer variables
        for name, value in self.integer_manager.get_all_variables().items():
            result.append({
                "id": f"int_{name}",
                "name": name,
                "type": "integer",
                "value": value,
                "initialValue": self.integer_manager.initial_variables.get(name, 0)
            })
        
        return result
    
    def reset(self):
        """Reset all variables to initial values"""
        self.signal_manager.reset()
        self.integer_manager.reset()
    
    def parse_variable_reference(self, reference: str) -> Tuple[Optional[str], Optional[SignalType]]:
        """Parse variable reference from script (e.g., 'int count' or 'signal_name')"""
        parts = reference.strip().split(maxsplit=1)
        
        if len(parts) == 2 and parts[0] == "int":
            # Integer variable reference
            return parts[1], SignalType.INTEGER
        elif len(parts) == 1:
            # Check if it exists
            var_type = self.get_type(parts[0])
            return parts[0], var_type
        
        return None, None