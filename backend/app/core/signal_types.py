"""
Signal and Variable Type System

This module defines the type system for signals and variables in the simulation.
It supports both boolean signals (existing) and integer variables (new).
"""

from enum import Enum
from typing import Union, Any


class SignalType(Enum):
    """Type enumeration for signals and variables"""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    
    @classmethod
    def from_value(cls, value: Any) -> 'SignalType':
        """Infer type from value"""
        if isinstance(value, bool):
            return cls.BOOLEAN
        elif isinstance(value, int) and not isinstance(value, bool):
            # In Python, bool is subclass of int, so we need to check bool first
            return cls.INTEGER
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")
    
    def validate_value(self, value: Any) -> bool:
        """Validate if value matches the signal type"""
        if self == SignalType.BOOLEAN:
            return isinstance(value, bool)
        elif self == SignalType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        return False
    
    def get_default_value(self) -> Union[bool, int]:
        """Get default value for the type"""
        if self == SignalType.BOOLEAN:
            return False
        elif self == SignalType.INTEGER:
            return 0
        raise ValueError(f"Unknown type: {self}")
    
    def parse_value(self, value_str: str) -> Union[bool, int]:
        """Parse string value to appropriate type"""
        if self == SignalType.BOOLEAN:
            if value_str.lower() == "true":
                return True
            elif value_str.lower() == "false":
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value_str}")
        elif self == SignalType.INTEGER:
            try:
                return int(value_str)
            except ValueError:
                raise ValueError(f"Invalid integer value: {value_str}")
        raise ValueError(f"Unknown type: {self}")


class TypedSignal:
    """Container for typed signal/variable with value"""
    def __init__(self, name: str, signal_type: SignalType, value: Union[bool, int] = None):
        self.name = name
        self.type = signal_type
        self._value = value if value is not None else signal_type.get_default_value()
        
        # Validate initial value
        if not self.type.validate_value(self._value):
            raise ValueError(f"Value {self._value} does not match type {self.type}")
    
    @property
    def value(self) -> Union[bool, int]:
        return self._value
    
    @value.setter
    def value(self, new_value: Union[bool, int]):
        if not self.type.validate_value(new_value):
            raise ValueError(f"Value {new_value} does not match type {self.type}")
        self._value = new_value
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TypedSignal':
        """Create from dictionary"""
        signal_type = SignalType(data.get("type", "boolean"))
        return cls(
            name=data["name"],
            signal_type=signal_type,
            value=data.get("value", signal_type.get_default_value())
        )