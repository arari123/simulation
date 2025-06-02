"""
테스트 관련 API 라우트
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
import os

# 테스트 러너 import를 위한 경로 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

router = APIRouter(prefix="/test", tags=["testing"])

@router.post("/run-full")
async def run_full_backend_test() -> Dict[str, Any]:
    """전체 백엔드 테스트 실행"""
    try:
        # 동적 import로 순환 import 방지
        from test_runner import run_full_backend_test
        
        results = await run_full_backend_test()
        return {
            "status": "completed",
            "results": results
        }
    except ImportError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"테스트 모듈을 찾을 수 없습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"테스트 실행 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def test_health_check() -> Dict[str, str]:
    """테스트 시스템 상태 확인"""
    return {
        "status": "healthy",
        "message": "테스트 시스템이 정상적으로 작동 중입니다."
    }