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
# 새로운 단순 엔진 어댑터 사용
from ..simple_engine_adapter import engine_adapter

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
        for field in ["fromBlockId", "toBlockId"]:
            if field in conn and isinstance(conn[field], int):
                conn[field] = str(conn[field])
    
    return config

@router.post("/setup")
async def setup_simulation_endpoint(config_data: dict):
    """시뮬레이션 설정 엔드포인트"""
    try:
        logger.info("🚀 새로운 단순 엔진으로 시뮬레이션 설정 시작")
        
        # ID를 문자열로 변환
        config_data = convert_config_ids_to_strings(config_data)
        
        # 글로벌 신호 변환
        initial_signals = convert_global_signals_to_initial_signals(config_data)
        config_data["initial_signals"] = initial_signals
        
        # Pydantic 모델로 검증
        setup = SimulationSetup(**config_data)
        
        # 새 엔진으로 설정
        await engine_adapter.setup_simulation(setup)
        
        logger.info("✅ 새로운 단순 엔진 설정 완료")
        return {
            "message": "새로운 단순 엔진으로 시뮬레이션이 설정되었습니다",
            "engine_type": "simple_engine_v3",
            "blocks_count": len(setup.blocks),
            "connections_count": len(setup.connections),
            "initial_signals": initial_signals
        }
        
    except Exception as e:
        logger.error(f"❌ 시뮬레이션 설정 오류: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=f"설정 오류: {str(e)}")

@router.post("/step", response_model=SimulationStepResult)
async def step_simulation_endpoint(config_data: Optional[dict] = None):
    """단일 시뮬레이션 스텝 실행"""
    try:
        # 설정 데이터가 있으면 먼저 시뮬레이션 설정
        if config_data:
            logger.info("🚀 스텝 실행 전 시뮬레이션 설정")
            
            # 블록 정보 로깅
            for block in config_data.get('blocks', []):
                block_name = block.get('name', 'Unknown')
                if 'script' in block:
                    logger.info(f"📝 설정 중 블록 '{block_name}' 스크립트 필드 존재")
                else:
                    logger.info(f"📝 설정 중 블록 '{block_name}' 스크립트 필드 없음")
            
            # ID를 문자열로 변환
            config_data = convert_config_ids_to_strings(config_data)
            
            # 글로벌 신호 변환
            initial_signals = convert_global_signals_to_initial_signals(config_data)
            config_data["initial_signals"] = initial_signals
            
            # Pydantic 모델로 검증
            setup = SimulationSetup(**config_data)
            
            # 새 엔진으로 설정
            await engine_adapter.setup_simulation(setup)
            logger.info("✅ 시뮬레이션 설정 완료")
        
        logger.info("⚡ 새로운 단순 엔진 스텝 실행")
        result = engine_adapter.step_simulation()
        
        logger.info(f"✅ 스텝 완료 - 시간: {result.time:.2f}, 엔티티: {len(result.active_entities)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ 스텝 실행 오류: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"스텝 실행 오류: {str(e)}")

@router.post("/batch-step", response_model=BatchStepResult)
def batch_step_simulation_endpoint(request: BatchStepRequest):
    """배치 시뮬레이션 스텝 실행"""
    try:
        logger.info(f"⚡ 새로운 단순 엔진 배치 스텝 실행 ({request.steps}스텝)")
        result = engine_adapter.batch_step_simulation(request.steps)
        
        logger.info(f"✅ 배치 스텝 완료 - {result.steps_executed}스텝 실행")
        return result
        
    except Exception as e:
        logger.error(f"❌ 배치 스텝 실행 오류: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"배치 스텝 실행 오류: {str(e)}")

@router.post("/run", response_model=SimulationRunResult)
def run_simulation_endpoint(max_steps: int = 100):
    """시뮬레이션 연속 실행"""
    try:
        logger.info(f"🏃 새로운 단순 엔진 연속 실행 시작 (최대 {max_steps}스텝)")
        result = engine_adapter.run_simulation(max_steps)
        
        logger.info(f"✅ 연속 실행 완료 - 총 {result.total_entities_processed}개 엔티티 처리")
        return result
        
    except Exception as e:
        logger.error(f"❌ 연속 실행 오류: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"연속 실행 오류: {str(e)}")

@router.post("/reset")
def reset_simulation_endpoint():
    """시뮬레이션 리셋"""
    try:
        logger.info("🔄 새로운 단순 엔진 리셋")
        engine_adapter.reset_simulation()
        
        logger.info("✅ 새로운 단순 엔진 리셋 완료")
        return {
            "message": "새로운 단순 엔진이 리셋되었습니다",
            "engine_type": "simple_engine_v3"
        }
        
    except Exception as e:
        logger.error(f"❌ 리셋 오류: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"리셋 오류: {str(e)}")

@router.get("/status")
def get_simulation_status():
    """현재 시뮬레이션 상태 조회"""
    try:
        status = engine_adapter.get_simulation_status()
        status["engine_type"] = "simple_engine_v3"
        return status
        
    except Exception as e:
        logger.error(f"❌ 상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"상태 조회 오류: {str(e)}")

@router.get("/load-base-config")
def load_base_config():
    """기본 설정 로드"""
    try:
        base_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "base.json")
        
        if os.path.exists(base_config_path):
            with open(base_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info("✅ 기본 설정 로드 완료")
            return {
                "message": "기본 설정이 로드되었습니다",
                "config": config,
                "engine_type": "simple_engine_v3"
            }
        else:
            logger.warning("⚠️ 기본 설정 파일을 찾을 수 없습니다")
            raise HTTPException(status_code=404, detail="기본 설정 파일을 찾을 수 없습니다")
            
    except Exception as e:
        logger.error(f"❌ 기본 설정 로드 오류: {e}")
        raise HTTPException(status_code=500, detail=f"기본 설정 로드 오류: {str(e)}")

@router.post("/load-config")
def load_config_file(file_path: str):
    """지정된 설정 파일 로드"""
    try:
        logger.info(f"📁 설정 파일 로드 시작: {file_path}")
        
        # 상대 경로를 절대 경로로 변환
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        full_path = os.path.join(project_root, file_path)
        
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 블록별 스크립트 정보 로깅
            for block in config.get('blocks', []):
                block_name = block.get('name', 'Unknown')
                if 'script' in block:
                    script_lines = block['script'].split('\n')
                    logger.info(f"📝 블록 '{block_name}' 스크립트: {len(script_lines)} 라인")
                    if script_lines:
                        logger.info(f"   첫 번째 라인: {script_lines[0]}")
                else:
                    logger.info(f"📝 블록 '{block_name}' 스크립트: 없음")
            
            logger.info(f"✅ 설정 파일 로드 완료: {file_path}")
            return {
                "message": f"설정 파일 {file_path}이(가) 로드되었습니다",
                "config": config,
                "engine_type": "simple_engine_v3"
            }
        else:
            logger.error(f"❌ 파일을 찾을 수 없습니다: {full_path}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 파싱 오류: {e}")
        raise HTTPException(status_code=400, detail=f"JSON 파싱 오류: {str(e)}")
    except Exception as e:
        logger.error(f"❌ 설정 파일 로드 오류: {e}")
        raise HTTPException(status_code=500, detail=f"설정 파일 로드 오류: {str(e)}")