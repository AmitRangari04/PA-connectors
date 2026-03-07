"""
Monitoring Routes
=================
Health check, metrics, and system status endpoints for monitoring and observability.
"""

import platform
import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from .settings import get_settings
from .cache import get_cache_manager
from .rate_limiter import get_rate_limiter
from .middleware import get_metrics_collector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

# Track application start time
_start_time = time.time()


def get_uptime() -> str:
    """Get application uptime as human-readable string."""
    uptime_seconds = time.time() - _start_time
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)


@router.get(
    "/health",
    summary="Health check endpoint",
    description="Returns the health status of the application and its dependencies."
)
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Returns:
        Health status of all components
    """
    settings = get_settings()
    
    # Check cache health
    cache_healthy = True
    try:
        cache = get_cache_manager()
        cache_stats = cache.stats()
        if cache_stats.get("backend") == "redis" and not cache_stats.get("connected", True):
            cache_healthy = False
    except Exception as e:
        cache_healthy = False
        logger.warning(f"Cache health check failed: {e}")
    
    # Overall health
    is_healthy = cache_healthy
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime": get_uptime(),
        "version": settings.app_version,
        "environment": settings.environment,
        "components": {
            "cache": "healthy" if cache_healthy else "unhealthy",
            "rate_limiter": "enabled" if settings.rate_limit_enabled else "disabled",
            "metrics": "enabled" if settings.metrics_enabled else "disabled"
        }
    }


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness check for Kubernetes/container orchestration."
)
async def liveness_probe() -> Dict[str, str]:
    """
    Simple liveness probe for container orchestration.
    
    Returns:
        Simple status response
    """
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Readiness check for Kubernetes/container orchestration."
)
async def readiness_probe() -> Dict[str, Any]:
    """
    Readiness probe for container orchestration.
    
    Returns:
        Readiness status
    """
    # Check if application is ready to receive traffic
    try:
        cache = get_cache_manager()
        cache.stats()  # Simple operation to verify cache is working
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "reason": str(e)}
        )


@router.get(
    "/metrics",
    summary="Application metrics",
    description="Returns application metrics for monitoring."
)
async def get_metrics() -> Dict[str, Any]:
    """
    Get application metrics.
    
    Returns:
        Collected metrics
    """
    settings = get_settings()
    
    if not settings.metrics_enabled:
        return {"enabled": False, "message": "Metrics collection is disabled"}
    
    metrics = get_metrics_collector()
    cache = get_cache_manager()
    rate_limiter = get_rate_limiter()
    
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": time.time() - _start_time,
        "requests": metrics.get_stats(),
        "cache": cache.stats(),
        "rate_limiter": rate_limiter.stats()
    }


@router.get(
    "/system",
    summary="System information",
    description="Returns system and runtime information."
)
async def system_info() -> Dict[str, Any]:
    """
    Get system information.
    
    Returns:
        System and runtime details
    """
    settings = get_settings()
    
    return {
        "application": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "debug": settings.debug
        },
        "runtime": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "pid": os.getpid()
        },
        "configuration": {
            "workers": settings.workers,
            "cache_enabled": settings.cache_enabled,
            "cache_backend": settings.cache_backend,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "rate_limit_requests": settings.rate_limit_requests,
            "rate_limit_window": settings.rate_limit_window,
            "batch_size": settings.batch_size,
            "max_concurrent_requests": settings.max_concurrent_requests
        }
    }


@router.get(
    "/cache/stats",
    summary="Cache statistics",
    description="Returns detailed cache statistics."
)
async def cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache statistics
    """
    cache = get_cache_manager()
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stats": cache.stats()
    }


@router.post(
    "/cache/clear",
    summary="Clear cache",
    description="Clears all cached data. Use with caution."
)
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cached data.
    
    Returns:
        Confirmation message
    """
    cache = get_cache_manager()
    cache.clear()
    logger.info("Cache cleared via API")
    return {"status": "success", "message": "Cache cleared"}


@router.get(
    "/rate-limit/stats",
    summary="Rate limiter statistics",
    description="Returns rate limiter statistics."
)
async def rate_limit_stats() -> Dict[str, Any]:
    """
    Get rate limiter statistics.
    
    Returns:
        Rate limiter statistics
    """
    rate_limiter = get_rate_limiter()
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stats": rate_limiter.stats()
    }


@router.post(
    "/rate-limit/reset",
    summary="Reset rate limits",
    description="Resets rate limits for all clients or a specific client."
)
async def reset_rate_limits(client_id: str = None) -> Dict[str, str]:
    """
    Reset rate limits.
    
    Args:
        client_id: Optional client ID to reset. Resets all if not provided.
        
    Returns:
        Confirmation message
    """
    rate_limiter = get_rate_limiter()
    rate_limiter.reset(client_id)
    
    if client_id:
        logger.info(f"Rate limits reset for client: {client_id}")
        return {"status": "success", "message": f"Rate limits reset for {client_id}"}
    else:
        logger.info("All rate limits reset via API")
        return {"status": "success", "message": "All rate limits reset"}
