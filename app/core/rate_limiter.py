"""
Rate Limiter
============
Token bucket rate limiting for API endpoints.
Supports per-client and global rate limiting for scalability.
"""

import time
import logging
from typing import Dict, Optional
from threading import Lock
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: float = field(default_factory=time.time)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens. Returns True if successful.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed, False if rate limited
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait before tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            float: Seconds to wait (0 if tokens available now)
        """
        self._refill()
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        return needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter supporting per-client and global limits.
    Uses token bucket algorithm for smooth rate limiting.
    """
    
    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        burst: int = 20
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_window: Max requests per time window
            window_seconds: Time window in seconds
            burst: Additional burst capacity
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.burst = burst
        self.enabled = True
        
        # Calculate token bucket parameters
        self.capacity = requests_per_window + burst
        self.refill_rate = requests_per_window / window_seconds
        
        # Per-client buckets
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = Lock()
        
        # Global bucket
        self._global_bucket = TokenBucket(
            capacity=self.capacity * 10,  # 10x for global
            refill_rate=self.refill_rate * 10
        )
        
        # Statistics
        self._total_requests = 0
        self._limited_requests = 0
    
    def _get_bucket(self, client_id: str) -> TokenBucket:
        """Get or create a token bucket for a client."""
        with self._lock:
            if client_id not in self._buckets:
                self._buckets[client_id] = TokenBucket(
                    capacity=self.capacity,
                    refill_rate=self.refill_rate
                )
            return self._buckets[client_id]
    
    def is_allowed(self, client_id: str = "default") -> bool:
        """
        Check if a request is allowed for the given client.
        
        Args:
            client_id: Client identifier for per-client limiting
            
        Returns:
            bool: True if request is allowed
        """
        if not self.enabled:
            return True
        
        self._total_requests += 1
        
        # Check global limit first
        if not self._global_bucket.consume():
            self._limited_requests += 1
            logger.warning(f"Global rate limit exceeded")
            return False
        
        # Check per-client limit
        bucket = self._get_bucket(client_id)
        if not bucket.consume():
            self._limited_requests += 1
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        return True
    
    def get_wait_time(self, client_id: str = "default") -> float:
        """
        Get time to wait before next request is allowed.
        
        Args:
            client_id: Client identifier
            
        Returns:
            float: Seconds to wait
        """
        if not self.enabled:
            return 0
        
        global_wait = self._global_bucket.get_wait_time()
        client_wait = self._get_bucket(client_id).get_wait_time()
        return max(global_wait, client_wait)
    
    def get_remaining(self, client_id: str = "default") -> int:
        """
        Get remaining requests for a client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            int: Remaining requests
        """
        if not self.enabled:
            return self.capacity
        
        bucket = self._get_bucket(client_id)
        bucket._refill()
        return int(bucket.tokens)
    
    def stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            "enabled": self.enabled,
            "requests_per_window": self.requests_per_window,
            "window_seconds": self.window_seconds,
            "burst": self.burst,
            "total_requests": self._total_requests,
            "limited_requests": self._limited_requests,
            "limit_rate": f"{(self._limited_requests / self._total_requests * 100) if self._total_requests > 0 else 0:.2f}%",
            "active_clients": len(self._buckets)
        }
    
    def reset(self, client_id: Optional[str] = None) -> None:
        """
        Reset rate limits.
        
        Args:
            client_id: If provided, reset only this client. Otherwise reset all.
        """
        with self._lock:
            if client_id:
                if client_id in self._buckets:
                    del self._buckets[client_id]
            else:
                self._buckets.clear()
                self._global_bucket = TokenBucket(
                    capacity=self.capacity * 10,
                    refill_rate=self.refill_rate * 10
                )
    
    def disable(self) -> None:
        """Disable rate limiting."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable rate limiting."""
        self.enabled = True


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        from .settings import get_settings
        settings = get_settings()
        _rate_limiter = RateLimiter(
            requests_per_window=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window,
            burst=settings.rate_limit_burst
        )
        if not settings.rate_limit_enabled:
            _rate_limiter.disable()
    return _rate_limiter
