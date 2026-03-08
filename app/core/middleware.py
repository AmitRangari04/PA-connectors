"""
Middleware Components
=====================
FastAPI middleware for rate limiting, request logging, and metrics collection.
"""

import time
import logging
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from .rate_limiter import get_rate_limiter
from .settings import get_settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.
    Returns 429 Too Many Requests when limit is exceeded.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Get client identifier (IP or API key)
        client_id = self._get_client_id(request)
        
        rate_limiter = get_rate_limiter()
        
        if not rate_limiter.is_allowed(client_id):
            wait_time = rate_limiter.get_wait_time(client_id)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Try again in {wait_time:.1f} seconds.",
                    "retry_after": int(wait_time) + 1
                },
                headers={
                    "Retry-After": str(int(wait_time) + 1),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + wait_time))
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(client_id)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Check for API key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api:{api_key[:8]}"
        
        # Check for client_key query parameter
        client_key = request.query_params.get("client_key")
        if client_key:
            return f"client:{client_key}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and response times.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        
        return response


class MetricsCollector:
    """
    Collects and stores application metrics.
    """
    
    def __init__(self):
        self.requests_total = 0
        self.requests_by_endpoint: dict = {}
        self.requests_by_status: dict = {}
        self.response_times: list = []
        self.errors: list = []
        self._max_response_times = 1000  # Keep last 1000 response times
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float
    ) -> None:
        """Record a request metric."""
        self.requests_total += 1
        
        # By endpoint
        key = f"{method}:{endpoint}"
        if key not in self.requests_by_endpoint:
            self.requests_by_endpoint[key] = 0
        self.requests_by_endpoint[key] += 1
        
        # By status
        status_group = f"{status_code // 100}xx"
        if status_group not in self.requests_by_status:
            self.requests_by_status[status_group] = 0
        self.requests_by_status[status_group] += 1
        
        # Response times
        self.response_times.append(duration_ms)
        if len(self.response_times) > self._max_response_times:
            self.response_times = self.response_times[-self._max_response_times:]
    
    def record_error(self, endpoint: str, error: str) -> None:
        """Record an error."""
        self.errors.append({
            "endpoint": endpoint,
            "error": error,
            "timestamp": time.time()
        })
        # Keep last 100 errors
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
    
    def get_stats(self) -> dict:
        """Get collected metrics."""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0
        )
        
        return {
            "requests_total": self.requests_total,
            "requests_by_endpoint": self.requests_by_endpoint,
            "requests_by_status": self.requests_by_status,
            "response_time_avg_ms": round(avg_response_time, 2),
            "response_time_min_ms": round(min(self.response_times), 2) if self.response_times else 0,
            "response_time_max_ms": round(max(self.response_times), 2) if self.response_times else 0,
            "recent_errors": len(self.errors)
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.requests_total = 0
        self.requests_by_endpoint.clear()
        self.requests_by_status.clear()
        self.response_times.clear()
        self.errors.clear()


# Global metrics collector
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        
        if not settings.metrics_enabled:
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            metrics = get_metrics_collector()
            metrics.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
            
            return response
            
        except Exception as e:
            metrics = get_metrics_collector()
            metrics.record_error(request.url.path, str(e))
            raise
