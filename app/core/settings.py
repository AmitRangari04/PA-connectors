"""
Application Settings
====================
Centralized configuration using pydantic-settings for environment variable management.
Supports scalability features like caching, rate limiting, and worker configuration.
"""

import os
from typing import Optional, List
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Supports .env file loading and validation.
    """
    
    # ==========================================================================
    # APPLICATION SETTINGS
    # ==========================================================================
    app_name: str = Field(default="PAConnector API", description="Application name")
    app_version: str = Field(default="2.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # ==========================================================================
    # SERVER SETTINGS
    # ==========================================================================
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=4, description="Number of worker processes for production")
    reload: bool = Field(default=True, description="Enable auto-reload in development")
    
    # ==========================================================================
    # CORS SETTINGS
    # ==========================================================================
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins. Use specific origins in production."
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")
    
    # ==========================================================================
    # LOGGING SETTINGS
    # ==========================================================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        description="Log format string"
    )
    log_json: bool = Field(default=False, description="Enable JSON logging for production")
    
    # ==========================================================================
    # CACHE SETTINGS
    # ==========================================================================
    cache_enabled: bool = Field(default=True, description="Enable response caching")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds (default 5 minutes)")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_backend: str = Field(
        default="memory",
        description="Cache backend: memory, redis"
    )
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis URL for distributed caching (e.g., redis://localhost:6379)"
    )
    
    # ==========================================================================
    # RATE LIMITING SETTINGS
    # ==========================================================================
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    rate_limit_burst: int = Field(default=20, description="Burst allowance above limit")
    
    # ==========================================================================
    # ASYNC PROCESSING SETTINGS
    # ==========================================================================
    batch_size: int = Field(default=100, description="Default batch size for processing")
    max_concurrent_requests: int = Field(default=10, description="Max concurrent API requests")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Delay between retries in seconds")
    
    # ==========================================================================
    # CONNECTION POOL SETTINGS
    # ==========================================================================
    pool_size: int = Field(default=10, description="Connection pool size")
    pool_max_overflow: int = Field(default=20, description="Max overflow connections")
    pool_timeout: int = Field(default=30, description="Pool connection timeout")
    pool_recycle: int = Field(default=3600, description="Connection recycle time in seconds")
    
    # ==========================================================================
    # CROWDSTRIKE API SETTINGS
    # ==========================================================================
    crowdstrike_client_id: Optional[str] = Field(default=None, description="CrowdStrike Client ID")
    crowdstrike_client_secret: Optional[str] = Field(default=None, description="CrowdStrike Client Secret")
    crowdstrike_base_url: str = Field(
        default="https://api.crowdstrike.com",
        description="CrowdStrike API base URL"
    )
    
    # ==========================================================================
    # HEALTH CHECK SETTINGS
    # ==========================================================================
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    health_check_timeout: int = Field(default=5, description="Health check timeout in seconds")
    
    # ==========================================================================
    # METRICS SETTINGS
    # ==========================================================================
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_prefix: str = Field(default="paconnector", description="Metrics prefix")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    def get_uvicorn_config(self) -> dict:
        """Get uvicorn configuration based on environment."""
        config = {
            "host": self.host,
            "port": self.port,
        }
        
        if self.is_production():
            config["workers"] = self.workers
            config["reload"] = False
            config["access_log"] = True
        else:
            config["reload"] = self.reload
            config["workers"] = 1
        
        return config


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache for singleton pattern.
    """
    return Settings()
