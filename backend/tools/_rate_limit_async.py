"""
Async Rate Limiter for tool functions
Provides rate limiting for async HTTP calls using asyncio.Semaphore
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class AsyncRateLimitConfig:
    """Configuration for async rate limiter"""
    max_concurrent: int = 5
    requests_per_minute: int = 60


class AsyncRateLimiter:
    """
    Async rate limiter using semaphore for concurrency control
    and simple token bucket for rate limiting.
    """

    def __init__(self, config: AsyncRateLimitConfig):
        self.config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
        self._last_reset = time.time()
        self._request_count = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request"""
        await self._semaphore.acquire()

        # Also enforce rate limit (requests per minute)
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_reset
            if elapsed >= 60:
                # Reset counter every minute
                self._request_count = 0
                self._last_reset = now
            elif self._request_count >= self.config.requests_per_minute:
                # Need to wait until next minute
                wait_time = 60 - elapsed
                self._semaphore.release()
                await asyncio.sleep(wait_time)
                async with self._lock:
                    self._request_count = 0
                    self._last_reset = time.time()
                    # Re-acquire after waiting
                    await self._semaphore.acquire()
            self._request_count += 1

    def release(self):
        """Release concurrency slot"""
        self._semaphore.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.release()


# Global registry of async rate limiters
_async_limiters: dict[str, AsyncRateLimiter] = {}


def get_async_rate_limiter(provider: str) -> AsyncRateLimiter:
    """Get or create an async rate limiter for the given provider"""
    import os

    if provider not in _async_limiters:
        # Default config from environment or built-in defaults
        if provider == "serper":
            rpm = int(os.environ.get("SERPER_REQUESTS_PER_MINUTE", 60))
            concurrent = int(os.environ.get("SERPER_CONCURRENT", 5))
        elif provider == "dataforseo":
            rpm = int(os.environ.get("DATAFORSEO_REQUESTS_PER_MINUTE", 100))
            concurrent = int(os.environ.get("DATAFORSEO_CONCURRENT", 10))
        elif provider == "gsc":
            rpm = int(os.environ.get("GSC_REQUESTS_PER_MINUTE", 100))
            concurrent = int(os.environ.get("GSC_CONCURRENT", 5))
        elif provider == "ga4":
            rpm = int(os.environ.get("GA4_REQUESTS_PER_MINUTE", 100))
            concurrent = int(os.environ.get("GA4_CONCURRENT", 5))
        else:
            rpm = int(os.environ.get("DEFAULT_REQUESTS_PER_MINUTE", 60))
            concurrent = int(os.environ.get("DEFAULT_CONCURRENT", 5))

        _async_limiters[provider] = AsyncRateLimiter(AsyncRateLimitConfig(
            max_concurrent=concurrent,
            requests_per_minute=rpm
        ))

    return _async_limiters[provider]
