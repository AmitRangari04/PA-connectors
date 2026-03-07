"""
Core Module
===========
Core utilities for scalability: settings, caching, rate limiting, and async processing.
"""

from .settings import Settings, get_settings
from .cache import CacheManager, get_cache_manager, cached
from .rate_limiter import RateLimiter, get_rate_limiter
from .async_processor import AsyncBatchProcessor, ConnectionPool
from .middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    MetricsMiddleware,
    MetricsCollector,
    get_metrics_collector
)

__all__ = [
    "Settings",
    "get_settings",
    "CacheManager",
    "get_cache_manager",
    "cached",
    "RateLimiter",
    "get_rate_limiter",
    "AsyncBatchProcessor",
    "ConnectionPool",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "MetricsMiddleware",
    "MetricsCollector",
    "get_metrics_collector"
]
