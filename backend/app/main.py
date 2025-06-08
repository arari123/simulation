from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes.simulation import router as simulation_router
from .routes.basic import router as basic_router
from .routes.testing import router as testing_router
from .routes.debug import router as debug_router
from .logger_config import setup_logging
from .config import settings

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(simulation_router)
app.include_router(basic_router)
app.include_router(testing_router)
app.include_router(debug_router)

# Health check endpoint
@app.get(settings.health_check_path)
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.api_version
    }

# 애플리케이션 시작 시 초기화
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    # Setup logging configuration
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 시뮬레이션 API 서버가 시작되었습니다.")
    logger.info(f"🌍 환경: {settings.environment}")
    logger.info(f"🔧 디버그 모드: {settings.debug}")
    logger.info(f"📚 API 문서: http://localhost:{settings.port}/docs")
    logger.info(f"❤️ 헬스체크: http://localhost:{settings.port}{settings.health_check_path}")
    
    print("🚀 시뮬레이션 API 서버가 시작되었습니다.")
    print(f"🌍 환경: {settings.environment}")
    print(f"📚 API 문서: http://localhost:{settings.port}/docs")

@app.on_event("shutdown") 
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    from .state_manager import reset_simulation_state
    logger = logging.getLogger(__name__)
    
    reset_simulation_state()
    logger.info("🛑 시뮬레이션 API 서버가 종료되었습니다.")
    print("🛑 시뮬레이션 API 서버가 종료되었습니다.") 