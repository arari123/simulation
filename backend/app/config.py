"""
Configuration module for environment variables and application settings
"""
import os
from typing import List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application settings
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    port: int = Field(default=8080, env="PORT")
    
    # API settings
    api_title: str = Field(default="시뮬레이션 API", env="API_TITLE")
    api_description: str = Field(default="이산 사건 시뮬레이션 API", env="API_DESCRIPTION")
    api_version: str = Field(default="2.0.0", env="API_VERSION")
    
    # CORS settings
    allowed_origins: List[str] = Field(
        default=["*"], 
        env="ALLOWED_ORIGINS",
        description="Comma-separated list of allowed origins"
    )
    
    # Logging settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="standard", env="LOG_FORMAT")
    
    # Performance settings
    max_concurrent_simulations: int = Field(default=10, env="MAX_CONCURRENT_SIMULATIONS")
    request_timeout: int = Field(default=300, env="REQUEST_TIMEOUT")
    
    # Health check settings
    health_check_path: str = Field(default="/health", env="HEALTH_CHECK_PATH")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse comma-separated origins
        if isinstance(self.allowed_origins, str):
            self.allowed_origins = [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()