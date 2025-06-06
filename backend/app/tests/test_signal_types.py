"""
Unit tests for signal type system
"""

import pytest
from app.core.signal_types import SignalType, TypedSignal


class TestSignalType:
    """Test SignalType enum functionality"""
    
    def test_enum_values(self):
        """Test enum value definitions"""
        assert SignalType.BOOLEAN.value == "boolean"
        assert SignalType.INTEGER.value == "integer"
    
    def test_from_value(self):
        """Test type inference from values"""
        assert SignalType.from_value(True) == SignalType.BOOLEAN
        assert SignalType.from_value(False) == SignalType.BOOLEAN
        assert SignalType.from_value(0) == SignalType.INTEGER
        assert SignalType.from_value(42) == SignalType.INTEGER
        assert SignalType.from_value(-10) == SignalType.INTEGER
        
        with pytest.raises(ValueError):
            SignalType.from_value("string")
        with pytest.raises(ValueError):
            SignalType.from_value(3.14)
    
    def test_validate_value(self):
        """Test value validation"""
        assert SignalType.BOOLEAN.validate_value(True) == True
        assert SignalType.BOOLEAN.validate_value(False) == True
        assert SignalType.BOOLEAN.validate_value(0) == False
        assert SignalType.BOOLEAN.validate_value("true") == False
        
        assert SignalType.INTEGER.validate_value(0) == True
        assert SignalType.INTEGER.validate_value(42) == True
        assert SignalType.INTEGER.validate_value(-10) == True
        assert SignalType.INTEGER.validate_value(True) == False  # bool is not int
        assert SignalType.INTEGER.validate_value(3.14) == False
        assert SignalType.INTEGER.validate_value("42") == False
    
    def test_get_default_value(self):
        """Test default values"""
        assert SignalType.BOOLEAN.get_default_value() == False
        assert SignalType.INTEGER.get_default_value() == 0
    
    def test_parse_value(self):
        """Test string parsing"""
        # Boolean parsing
        assert SignalType.BOOLEAN.parse_value("true") == True
        assert SignalType.BOOLEAN.parse_value("True") == True
        assert SignalType.BOOLEAN.parse_value("TRUE") == True
        assert SignalType.BOOLEAN.parse_value("false") == False
        assert SignalType.BOOLEAN.parse_value("False") == False
        assert SignalType.BOOLEAN.parse_value("FALSE") == False
        
        with pytest.raises(ValueError):
            SignalType.BOOLEAN.parse_value("yes")
        with pytest.raises(ValueError):
            SignalType.BOOLEAN.parse_value("1")
        
        # Integer parsing
        assert SignalType.INTEGER.parse_value("0") == 0
        assert SignalType.INTEGER.parse_value("42") == 42
        assert SignalType.INTEGER.parse_value("-10") == -10
        assert SignalType.INTEGER.parse_value("  100  ") == 100
        
        with pytest.raises(ValueError):
            SignalType.INTEGER.parse_value("abc")
        with pytest.raises(ValueError):
            SignalType.INTEGER.parse_value("3.14")
        with pytest.raises(ValueError):
            SignalType.INTEGER.parse_value("")


class TestTypedSignal:
    """Test TypedSignal container"""
    
    def test_initialization(self):
        """Test signal creation"""
        # Boolean signal
        sig1 = TypedSignal("flag", SignalType.BOOLEAN)
        assert sig1.name == "flag"
        assert sig1.type == SignalType.BOOLEAN
        assert sig1.value == False  # default
        
        sig2 = TypedSignal("enabled", SignalType.BOOLEAN, True)
        assert sig2.value == True
        
        # Integer signal
        sig3 = TypedSignal("count", SignalType.INTEGER)
        assert sig3.name == "count"
        assert sig3.type == SignalType.INTEGER
        assert sig3.value == 0  # default
        
        sig4 = TypedSignal("total", SignalType.INTEGER, 42)
        assert sig4.value == 42
    
    def test_value_validation(self):
        """Test value type validation"""
        sig_bool = TypedSignal("flag", SignalType.BOOLEAN)
        sig_int = TypedSignal("count", SignalType.INTEGER)
        
        # Valid assignments
        sig_bool.value = True
        assert sig_bool.value == True
        
        sig_int.value = 100
        assert sig_int.value == 100
        
        # Invalid assignments
        with pytest.raises(ValueError):
            sig_bool.value = 1
        
        with pytest.raises(ValueError):
            sig_int.value = True
        
        with pytest.raises(ValueError):
            sig_int.value = 3.14
        
        # Invalid initialization
        with pytest.raises(ValueError):
            TypedSignal("bad", SignalType.BOOLEAN, 123)
        
        with pytest.raises(ValueError):
            TypedSignal("bad", SignalType.INTEGER, "hello")
    
    def test_serialization(self):
        """Test to_dict and from_dict"""
        sig1 = TypedSignal("flag", SignalType.BOOLEAN, True)
        data1 = sig1.to_dict()
        assert data1 == {
            "name": "flag",
            "type": "boolean",
            "value": True
        }
        
        sig2 = TypedSignal("count", SignalType.INTEGER, 42)
        data2 = sig2.to_dict()
        assert data2 == {
            "name": "count", 
            "type": "integer",
            "value": 42
        }
        
        # Test deserialization
        sig3 = TypedSignal.from_dict(data1)
        assert sig3.name == "flag"
        assert sig3.type == SignalType.BOOLEAN
        assert sig3.value == True
        
        sig4 = TypedSignal.from_dict(data2)
        assert sig4.name == "count"
        assert sig4.type == SignalType.INTEGER
        assert sig4.value == 42
        
        # Test with missing value (should use default)
        sig5 = TypedSignal.from_dict({"name": "test", "type": "boolean"})
        assert sig5.value == False
        
        sig6 = TypedSignal.from_dict({"name": "test", "type": "integer"})
        assert sig6.value == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])