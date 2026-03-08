"""
Cache Manager
=============
In-memory caching with TTL support for API response caching.
Supports both memory and Redis backends for scalability.
"""

import time
import hashlib
import json
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict
from threading import Lock
from functools import wraps

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with TTL."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.created_at > self.ttl


class MemoryCache:
    """
    Thread-safe in-memory LRU cache with TTL support.
    Suitable for single-instance deployments.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a cache key from arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return entry.value
                else:
                    # Remove expired entry
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        with self._lock:
            ttl = ttl or self.default_ttl
            
            # Remove oldest entries if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = CacheEntry(value, ttl)
            self._cache.move_to_end(key)
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "default_ttl": self.default_ttl
            }


class CacheManager:
    """
    Cache manager that supports multiple backends.
    Provides a unified interface for caching operations.
    """
    
    def __init__(
        self,
        backend: str = "memory",
        max_size: int = 1000,
        default_ttl: int = 300,
        redis_url: Optional[str] = None
    ):
        self.backend_type = backend
        self.enabled = True
        
        if backend == "redis" and redis_url:
            try:
                import redis
                self._redis = redis.from_url(redis_url)
                self._cache = None
                logger.info(f"Using Redis cache backend: {redis_url}")
            except ImportError:
                logger.warning("Redis not installed, falling back to memory cache")
                self._redis = None
                self._cache = MemoryCache(max_size, default_ttl)
        else:
            self._redis = None
            self._cache = MemoryCache(max_size, default_ttl)
            logger.info("Using in-memory cache backend")
        
        self.default_ttl = default_ttl
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key with prefix."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        hash_key = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        if self._redis:
            try:
                value = self._redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
            return None
        
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if not self.enabled:
            return
        
        ttl = ttl or self.default_ttl
        
        if self._redis:
            try:
                self._redis.setex(key, ttl, json.dumps(value, default=str))
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
            return
        
        self._cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if self._redis:
            try:
                return bool(self._redis.delete(key))
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                return False
        
        return self._cache.delete(key)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        if self._redis:
            try:
                self._redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
            return
        
        self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._redis:
            try:
                info = self._redis.info("stats")
                return {
                    "backend": "redis",
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "connected": True
                }
            except Exception as e:
                return {"backend": "redis", "error": str(e), "connected": False}
        
        stats = self._cache.stats()
        stats["backend"] = "memory"
        return stats
    
    def disable(self) -> None:
        """Disable caching."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable caching."""
        self.enabled = True


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        from .settings import get_settings
        settings = get_settings()
        _cache_manager = CacheManager(
            backend=settings.cache_backend,
            max_size=settings.cache_max_size,
            default_ttl=settings.cache_ttl,
            redis_url=settings.redis_url
        )
        if not settings.cache_enabled:
            _cache_manager.disable()
    return _cache_manager


def cached(prefix: str, ttl: Optional[int] = None):
    """
    Decorator for caching function results.
    
    Usage:
        @cached("inventory_schema", ttl=300)
        async def get_inventory_schema(count: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            key = cache.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {prefix}")
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            logger.debug(f"Cache miss for {prefix}, cached result")
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache = get_cache_manager()
            key = cache.generate_key(prefix, *args, **kwargs)
            
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {prefix}")
                return cached_value
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            logger.debug(f"Cache miss for {prefix}, cached result")
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
