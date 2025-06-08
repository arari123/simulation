"""
디버그 관련 API 엔드포인트
브레이크포인트 관리 및 디버그 제어
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from ..simple_engine_adapter import engine_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulation/debug", tags=["debug"])

# Request/Response 모델 정의
class BreakpointRequest(BaseModel):
    """브레이크포인트 설정/해제 요청"""
    action: str  # "set", "clear", "clear_all"
    block_id: Optional[str] = None
    line_number: Optional[int] = None

class DebugControlRequest(BaseModel):
    """디버그 제어 요청"""
    action: str  # "continue", "step", "stop_debug", "start_debug"

class DebugStatusResponse(BaseModel):
    """디버그 상태 응답"""
    is_debugging: bool
    is_paused: bool
    current_break: Optional[Dict[str, Any]] = None
    breakpoints: Dict[str, List[int]]
    execution_context: List[Dict[str, Any]]

class BreakpointData(BaseModel):
    """브레이크포인트 설정/해제 데이터 (프론트엔드 호환)"""
    block_id: str
    line_number: int
    enabled: bool

@router.post("/breakpoints/manage")
async def manage_breakpoints(request: BreakpointRequest):
    """브레이크포인트 설정/해제 (관리 API)"""
    try:
        # 시뮬레이션이 초기화되었으면 엔진의 디버그 매니저 사용, 아니면 글로벌 디버그 매니저 사용
        if engine_adapter.has_engine():
            debug_manager = engine_adapter.engine.debug_manager
        else:
            debug_manager = engine_adapter.global_debug_manager
        
        if request.action == "set":
            if not request.block_id or request.line_number is None:
                raise HTTPException(status_code=400, detail="block_id and line_number required for set action")
            
            debug_manager.set_breakpoint(request.block_id, request.line_number)
            # Breakpoint set
            
        elif request.action == "clear":
            if not request.block_id or request.line_number is None:
                raise HTTPException(status_code=400, detail="block_id and line_number required for clear action")
            
            debug_manager.clear_breakpoint(request.block_id, request.line_number)
            # Breakpoint cleared
            
        elif request.action == "clear_all":
            debug_manager.clear_all_breakpoints(request.block_id)
            # All breakpoints cleared
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return {
            "success": True,
            "breakpoints": debug_manager.get_breakpoints()
        }
        
    except Exception as e:
        logger.error(f"Error managing breakpoints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/control")
async def debug_control(request: DebugControlRequest):
    """디버그 제어 (계속/스텝/중지)"""
    try:
        if not engine_adapter.has_engine():
            raise HTTPException(status_code=400, detail="Simulation not initialized")
        
        debug_manager = engine_adapter.engine.debug_manager
        
        if request.action == "start_debug":
            debug_manager.start_debugging()
            # Debug mode started
            
        elif request.action == "stop_debug":
            debug_manager.stop_debugging()
            # Debug mode stopped
            
        elif request.action == "continue":
            success = debug_manager.continue_execution()
            if not success:
                raise HTTPException(status_code=400, detail="Not in paused state")
            # Execution continued
            
        elif request.action == "step":
            success = debug_manager.step_execution()
            if not success:
                raise HTTPException(status_code=400, detail="Not in paused state")
            # Step execution
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return {
            "success": True,
            "debug_info": debug_manager.get_debug_info()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in debug control: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=DebugStatusResponse)
async def get_debug_status():
    """현재 디버그 상태 조회"""
    try:
        # 글로벌 디버그 매니저 사용
        debug_info = engine_adapter.global_debug_manager.get_debug_info()
        
        return DebugStatusResponse(**debug_info)
        
    except Exception as e:
        logger.error(f"Error getting debug status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set_breakpoints_batch")
async def set_breakpoints_batch(breakpoints: Dict[str, List[int]]):
    """여러 브레이크포인트 한번에 설정"""
    try:
        if not engine_adapter.has_engine():
            raise HTTPException(status_code=400, detail="Simulation not initialized")
        
        debug_manager = engine_adapter.engine.debug_manager
        
        # 모든 브레이크포인트 초기화
        debug_manager.clear_all_breakpoints()
        
        # 새 브레이크포인트 설정
        for block_id, line_numbers in breakpoints.items():
            for line_number in line_numbers:
                debug_manager.set_breakpoint(block_id, line_number)
        
        # Batch breakpoints set
        
        return {
            "success": True,
            "breakpoints": debug_manager.get_breakpoints()
        }
        
    except Exception as e:
        logger.error(f"Error setting batch breakpoints: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 프론트엔드 호환 엔드포인트 (이미 manage_breakpoints가 있지만 다른 형식)
@router.post("/breakpoints", name="set_breakpoint_frontend")
async def set_breakpoint_frontend(data: BreakpointData):
    """브레이크포인트 설정/해제 (프론트엔드 호환)"""
    
    try:
        # 시뮬레이션이 초기화되었으면 엔진의 디버그 매니저 사용, 아니면 글로벌 디버그 매니저 사용
        if engine_adapter.has_engine():
            debug_manager = engine_adapter.engine.debug_manager
        else:
            debug_manager = engine_adapter.global_debug_manager
        
        if data.enabled:
            debug_manager.set_breakpoint(data.block_id, data.line_number)
            # Breakpoint set
        else:
            debug_manager.clear_breakpoint(data.block_id, data.line_number)
            # Breakpoint cleared
        
        # 현재 브레이크포인트 상태 로그
        all_breakpoints = debug_manager.get_breakpoints()
        
        return {
            "status": "success",
            "breakpoints": all_breakpoints
        }
        
    except Exception as e:
        logger.error(f"Error managing breakpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))