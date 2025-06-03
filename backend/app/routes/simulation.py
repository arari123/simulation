import os
import json
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, List, Any
import traceback
import asyncio
import simpy
import logging

from ..models import (
    SimulationSetup, SimulationRunResult, SimulationStepResult, 
    BatchStepRequest, BatchStepResult, EntityState
)
from ..state_manager import (
    sim_env, sim_log, processed_entities_count,
    reset_simulation_state, get_current_signals
)
from ..entity import get_active_entity_states
from ..utils import check_entity_movement, get_latest_movement_description
# 리팩토링된 엔진 사용
from ..simulation_engine_v2 import run_simulation, step_simulation, batch_step_simulation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])

def convert_global_signals_to_initial_signals(config_data: dict) -> dict:
    """글로벌 신호를 initial_signals 형태로 변환"""
    # 이미 initial_signals가 있다면 그대로 사용
    if "initial_signals" in config_data and isinstance(config_data["initial_signals"], dict):
        return config_data["initial_signals"]
    
    # globalSignals 배열에서 변환
    initial_signals = {}
    for signal in config_data.get("globalSignals", []):
        signal_name = signal.get("name")
        signal_value = signal.get("value", False)
        if signal_name:
            initial_signals[signal_name] = signal_value
    return initial_signals

def convert_config_ids_to_strings(config_data: dict) -> dict:
    """설정의 모든 ID를 문자열로 변환"""
    # 딥 카피로 원본 데이터 보호
    import copy
    config = copy.deepcopy(config_data)
    
    # 블록 ID 변환
    for block in config.get("blocks", []):
        if "id" in block and isinstance(block["id"], int):
            block["id"] = str(block["id"])
    
    # 연결 ID 변환
    for conn in config.get("connections", []):
        if "id" in conn and isinstance(conn["id"], int):
            conn["id"] = str(conn["id"])
        if "from_block_id" in conn and isinstance(conn["from_block_id"], int):
            conn["from_block_id"] = str(conn["from_block_id"])
        if "to_block_id" in conn and isinstance(conn["to_block_id"], int):
            conn["to_block_id"] = str(conn["to_block_id"])
    
    return config

@router.post("/run", response_model=SimulationRunResult)
async def run_simulation_endpoint(raw_setup: dict):
    """전체 시뮬레이션을 실행합니다."""
    try:
        # ID 변환 및 신호 처리 적용
        converted_config = convert_config_ids_to_strings(raw_setup)
        initial_signals = convert_global_signals_to_initial_signals(converted_config)
        
        # SimulationSetup 객체 생성
        setup_data = {
            "blocks": converted_config.get("blocks", []),
            "connections": converted_config.get("connections", []),
            "initial_signals": initial_signals
        }
        
        # 기타 필드들도 포함
        for key in ["initial_entities", "stop_time", "stop_entities_processed"]:
            if key in converted_config:
                setup_data[key] = converted_config[key]
        
        setup = SimulationSetup(**setup_data)
        result = await run_simulation(setup)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")

@router.post("/step", response_model=SimulationStepResult)
async def step_simulation_endpoint(raw_setup: Optional[dict] = None):
    """시뮬레이션을 한 스텝씩 실행합니다."""
    global processed_entities_count
    
    try:
        # 🔥 간소화된 디버깅 로그 (성능 최적화)
        from .. import simulation_engine_v2
        engine = simulation_engine_v2._simulation_engine
        has_env = engine.sim_env is not None
        has_setup = raw_setup is not None
        
        # 모니터링 모드가 아닐 때만 간단한 로그 출력
        if not getattr(engine, 'monitoring_mode', False):
            if has_env:
                current_time = engine.sim_env.now
                queue_size = len(engine.sim_env._queue)
                logger.info(f"[STEP] 환경 상태: 시간={current_time:.1f}, 큐={queue_size}, setup={has_setup}")
            else:
                logger.info(f"[STEP] 환경 없음, setup 제공: {has_setup}")
        
        setup = None
        if engine.sim_env is None:
            # 🔥 시뮬레이션 환경이 없으면 setup이 필요함
            if raw_setup is None:
                # 기본 설정 자동 로드
                logger.info(f"[STEP] 환경 없음 - 기본 설정 자동 로드")
                try:
                    with open('/home/arari123/project/simulation/base.json', 'r', encoding='utf-8') as f:
                        import json
                        raw_setup = json.load(f)
                        logger.info(f"[STEP] 기본 설정 로드 성공")
                except Exception as e:
                    logger.error(f"[STEP-ERROR] 기본 설정 로드 실패: {e}")
                    raise HTTPException(
                        status_code=400, 
                        detail="No active simulation and failed to load default setup. Please provide simulation setup."
                    )
            if not getattr(engine, 'monitoring_mode', False):
                logger.info(f"[STEP] 첫 번째 스텝 - 새로운 설정으로 시뮬레이션 시작")
            
            # ID 변환 및 신호 처리 적용
            converted_config = convert_config_ids_to_strings(raw_setup)
            initial_signals = convert_global_signals_to_initial_signals(converted_config)
            
            if not getattr(engine, 'monitoring_mode', False):
                logger.info(f"[STEP] 초기 신호 설정: {initial_signals}")
            
            # SimulationSetup 객체 생성
            setup_data = {
                "blocks": converted_config.get("blocks", []),
                "connections": converted_config.get("connections", []),
                "initial_signals": initial_signals
            }
            
            # 기타 필드들도 포함
            for key in ["initial_entities", "stop_time", "stop_entities_processed"]:
                if key in converted_config:
                    setup_data[key] = converted_config[key]
            
            setup = SimulationSetup(**setup_data)
        elif raw_setup is not None and engine.sim_env is not None:
            # 🔥 이미 시뮬레이션이 진행 중인 경우
            if not getattr(engine, 'monitoring_mode', False):
                logger.info(f"[STEP] 기존 환경에서 계속 진행")
            # setup을 전달하여 엔진이 변경사항을 확인할 수 있도록 함
            converted_config = convert_config_ids_to_strings(raw_setup)
            initial_signals = convert_global_signals_to_initial_signals(converted_config)
            
            setup_data = {
                "blocks": converted_config.get("blocks", []),
                "connections": converted_config.get("connections", []),
                "initial_signals": initial_signals
            }
            
            for key in ["initial_entities", "stop_time", "stop_entities_processed"]:
                if key in converted_config:
                    setup_data[key] = converted_config[key]
            
            setup = SimulationSetup(**setup_data)
        else:
            # 🔥 환경 존재하지만 setup 없음 - 계속 진행
            if not getattr(engine, 'monitoring_mode', False):
                logger.info(f"[STEP] 기존 환경에서 계속 진행")
            setup = None
        
        # 초기 상태 저장 (엔티티 움직임 감지용)
        initial_entity_states = {}
        for entity_state in get_active_entity_states():
            initial_entity_states[entity_state.id] = entity_state.current_block_id
        initial_processed_count = processed_entities_count
        
        result = await step_simulation(setup)
        
        # 엔티티 움직임 확인
        has_movement = check_entity_movement(initial_entity_states, initial_processed_count)
        
        if not has_movement:
            # 움직임이 없으면 최근 이벤트 설명 사용
            result.event_description = get_latest_movement_description()
        
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Step simulation error: {str(e)}")

@router.post("/batch-step", response_model=BatchStepResult)
async def batch_step_simulation_endpoint(request: BatchStepRequest):
    """시뮬레이션을 여러 스텝 실행합니다."""
    try:
        result = await batch_step_simulation(request.steps)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch step simulation error: {str(e)}")

@router.post("/reset")
async def reset_simulation_endpoint():
    """시뮬레이션을 초기화합니다."""
    try:
        # 🔥 SimPy 환경을 완전히 새로 생성하여 이전 프로세스들을 정리
        from .. import simulation_engine_v2
        engine = simulation_engine_v2._simulation_engine
        
        if engine.sim_env:
            logger.info(f"[RESET] 이전 SimPy 환경 정리 (시간: {engine.sim_env.now})")
        
        # 기존 state_manager도 리셋
        reset_simulation_state()
        
        # 새로운 엔진 리셋
        engine.reset()
        
        # 🚀 Performance optimization cache reset
        try:
            from .. import simulation_engine_v2
            simulation_engine_v2._simulation_engine.reset()
        except Exception as e:
            logger.warning(f"[RESET] Cache reset warning: {e}")
            # Continue with reset even if cache reset fails
        
        logger.info(f"[RESET] SimPy 환경 및 캐시 초기화됨 - 다음 스텝에서 새로 생성됨")
        
        # Reset log file
        from ..logger_config import reset_log_file
        reset_log_file()
        
        return {"message": "Simulation reset successfully"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Reset error: {str(e)}")

@router.post("/update-settings")
async def update_settings_endpoint(settings: Dict[str, Any]):
    """시뮬레이션 설정을 업데이트합니다."""
    try:
        # 설정 검증 및 저장
        valid_keys = ['boxSize', 'fontSize', 'deadlockTimeout', 'showEntityNames', 'showSignalNames', 'showSignalValues']
        validated_settings = {}
        
        for key, value in settings.items():
            if key in valid_keys:
                validated_settings[key] = value
            else:
                logger.warning(f"[SimulationRoutes] Warning: Unknown setting key '{key}' ignored")
        
        logger.info(f"[SimulationRoutes] Settings updated: {validated_settings}")
        
        return {
            "message": "Settings updated successfully",
            "updated_settings": validated_settings
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Settings update error: {str(e)}") 