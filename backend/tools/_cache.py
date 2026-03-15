"""
Simple in-memory cache for tool results with TTL.
"""

import time
import hashlib
import asyncio
from typing import Any, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CacheEntry:
    data: Any
    expires_at: float
    created_at: float


class ToolCache:
    """Thread-safe in-memory cache for tool results."""

    def __init__(self):
        self._store: Dict[str, CacheEntry] = {}
        self._lock = None  # Use threading.Lock if we need thread safety
        self.default_ttl = 300  # 5 minutes

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        entry = self._store.get(key)
        if entry and entry.expires_at > time.time():
            return entry.data
        elif entry:
            # Expired, clean up
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set cache entry with TTL."""
        if ttl is None:
            ttl = self.default_ttl
        expires = time.time() + ttl
        self._store[key] = CacheEntry(data=value, expires_at=expires, created_at=time.time())

    def delete(self, key: str) -> None:
        """Remove from cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()

    def make_key(self, tool_name: str, args: dict) -> str:
        """Generate deterministic cache key from tool name and arguments."""
        # Sort args for consistent hashing
        sorted_items = sorted((k, v) for k, v in args.items() if v is not None)
        key_str = f"{tool_name}:" + ":".join(f"{k}={v}" for k, v in sorted_items)
        return hashlib.md5(key_str.encode()).hexdigest()


# Global cache instance
_global_cache = ToolCache()


def get_cache() -> ToolCache:
    """Get the global cache instance."""
    return _global_cache


def cached(tool_name: str, ttl: int = 300):
    """
    Decorator for caching tool results (sync and async functions).

    Args:
        tool_name: Name of the tool (used in cache key)
        ttl: Time-to-live in seconds (default 5 minutes)
    """
    def decorator(func):
        cache = get_cache()

        async def async_wrapper(*args, **kwargs):
            # Build cache key from function arguments
            # For async functions, args includes 'self' if method, skip it for bound methods
            if args and hasattr(args[0], '__class__'):
                call_args = dict(zip(func.__code__.co_varnames[1:len(args)], args[1:]))
            else:
                call_args = dict(zip(func.__code__.co_varnames[:len(args)], args))
            call_args.update(kwargs)
            key = cache.make_key(tool_name, call_args)

            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Call the actual async function
            result = await func(*args, **kwargs)

            # Cache successful results (only if not error)
            if isinstance(result, dict) and not result.get('error'):
                cache.set(key, result, ttl)

            return result

        def sync_wrapper(*args, **kwargs):
            call_args = dict(zip(func.__code__.co_varnames[:len(args)], args))
            call_args.update(kwargs)
            key = cache.make_key(tool_name, call_args)

            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)

            if isinstance(result, dict) and not result.get('error'):
                cache.set(key, result, ttl)

            return result

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator
