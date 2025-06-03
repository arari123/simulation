"""
시뮬레이션 엔진의 상수와 설정값들을 정의합니다.
"""

# Action Types
class ActionType:
    """액션 타입 상수"""
    DELAY = "delay"
    CUSTOM_SINK = "custom_sink"
    ROUTE_TO_CONNECTOR = "route_to_connector"
    CONDITIONAL_BRANCH = "conditional_branch"
    SIGNAL_WAIT = "signal_wait"
    SIGNAL_UPDATE = "signal_update"
    SET_SIGNAL = "signal_update"  # Alias for backward compatibility
    BLOCK_ENTRY = "block_entry"

# Entity States
class EntityState:
    """엔티티 상태 상수"""
    IN_BLOCK = "in_block"
    TRANSIT = "transit"
    PROCESSED = "processed"
    ERROR = "error"

# Timeout Values
class TimeoutConfig:
    """타임아웃 설정값"""
    NO_ENTITY_TIMEOUT = 0.1
    CAPACITY_RETRY_TIMEOUT = 0.5
    SIGNAL_ERROR_TIMEOUT = 0.1
    MINIMAL_DELAY = 0.00001
    IDLE_TIMEOUT = 1.0
    MONITORING_INTERVAL = 0.1

# Formatting
class FormatConfig:
    """포맷 설정"""
    ENTITY_ID_FORMAT = "{block_id}-e{count}"
    PIPE_ID_FORMAT = "{from_block}_{from_conn}_to_{to_block}_{to_conn}"
    TRANSIT_DISPLAY_FORMAT = "{from_block}→{to_block}"
    LOG_PREFIX_FORMAT = "BPROC [{name}({id})]"

# Limits
class LimitConfig:
    """제한 설정"""
    INFINITE_GENERATION = float('inf')
    
# Performance Settings
DEBUG_MODE = False  # Set to True for detailed debugging (impacts performance)
PERFORMANCE_MODE = True  # Set to False for detailed logging
MONITORING_MODE = True  # Set to True for comprehensive state monitoring