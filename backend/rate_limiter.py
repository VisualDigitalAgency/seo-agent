"""
Rate Limiter - Controls API call concurrency and respects rate limits

Provides:
- Global concurrency limits for different API providers
- Token bucket algorithm for rate limiting
- Retry-After header support
- Thread-safe implementation
"""

import time
import threading
from typing import Optional
from dataclasses import dataclass
from collections import deque


@dataclass
class RateLimitConfig:
    """Configuration for a rate limiter"""
    max_concurrent: int = 5          # Max concurrent requests
    requests_per_minute: int = 60    # Token bucket rate
    burst_capacity: int = 10         # Max tokens that can accumulate
    retry_after_scale: float = 1.0   # Multiply Retry-After by this factor


class TokenBucket:
    """Token bucket for rate limiting"""

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second (requests_per_minute / 60)
            capacity: Maximum tokens that can accumulate
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: int = 1) -> float:
        """
        Consume tokens from bucket. Returns wait time in seconds.
        If tokens available, returns 0.
        """
        with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            new_tokens = elapsed * self.rate
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            else:
                # Calculate wait time needed
                needed = tokens - self.tokens
                wait_time = needed / self.rate
                self.tokens = 0
                return wait_time


class RateLimiter:
    """
    Multi-provider rate limiter with concurrency control.
    Uses per-provider semaphores for concurrency + token bucket for rate limiting.
    """

    def __init__(self):
        self._configs: dict[str, RateLimitConfig] = {}
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._global_lock = threading.Lock()

    def register_provider(self, provider: str, config: RateLimitConfig):
        """Register a provider with rate limit configuration"""
        with self._global_lock:
            self._configs[provider] = config
            self._semaphores[provider] = threading.Semaphore(config.max_concurrent)
            # Convert requests_per_minute to tokens/sec
            rate = config.requests_per_minute / 60.0
            self._buckets[provider] = TokenBucket(rate, config.burst_capacity)

    def acquire(self, provider: str) -> tuple[float, float]:
        """
        Acquire permission to make an API call.
        Returns tuple of (concurrency_wait, rate_limit_wait) in seconds.
        """
        with self._global_lock:
            if provider not in self._configs:
                # Default: 10 concurrent, 120 req/min
                self.register_provider(provider, RateLimitConfig(
                    max_concurrent=10,
                    requests_per_minute=120
                ))

            config = self._configs[provider]
            semaphore = self._semaphores[provider]
            bucket = self._buckets[provider]

        # Check if semaphore can be acquired (non-blocking check)
        if semaphore.acquire(blocking=False):
            concurrency_wait = 0.0
        else:
            # Need to wait for concurrency slot
            # Estimate wait based on average request time? For now, just wait fixed
            concurrency_wait = 1.0  # Default wait
            # Actually block with timeout to avoid deadlock
            acquired = semaphore.acquire(timeout=30)
            if not acquired:
                raise TimeoutError(f"Timeout waiting for {provider} concurrency slot")

        # Check rate limit
        rate_wait = bucket.consume(1)

        return concurrency_wait, rate_wait

    def release(self, provider: str):
        """Release concurrency slot after request completes"""
        with self._global_lock:
            if provider in self._semaphores:
                self._semaphores[provider].release()

    def update_from_retry_after(self, provider: str, retry_after: Optional[float]):
        """
        Update rate limiter based on Retry-After header.
        If retry_after is provided, temporarily reduce capacity.
        """
        if retry_after is None:
            return

        with self._global_lock:
            if provider in self._configs:
                config = self._configs[provider]
                # Temporarily reduce token bucket to respect server's retry-after
                # This is a simplified approach - more sophisticated would add a penalty
                if provider in self._buckets:
                    bucket = self._buckets[provider]
                    bucket.tokens = 0  # Force wait
                    # The bucket will naturally refill over time


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter


def configure_rate_limits_from_env():
    """Configure rate limits from environment variables"""
    # OpenRouter: respect their rate limits
    # Free tier: 10-20 requests/min typically, but varies
    openrouter_rpm = int(__import__('os').environ.get("OPENROUTER_REQUESTS_PER_MINUTE", 60))
    openrouter_concurrent = int(__import__('os').environ.get("OPENROUTER_CONCURRENT", 10))

    _rate_limiter.register_provider("openrouter", RateLimitConfig(
        max_concurrent=openrouter_concurrent,
        requests_per_minute=openrouter_rpm,
        burst_capacity=openrouter_concurrent
    ))

    # Serper: typically 100 req/day free, paid higher
    serper_rpm = int(__import__('os').environ.get("SERPER_REQUESTS_PER_MINUTE", 60))
    serper_concurrent = int(__import__('os').environ.get("SERPER_CONCURRENT", 5))
    _rate_limiter.register_provider("serper", RateLimitConfig(
        max_concurrent=serper_concurrent,
        requests_per_minute=serper_rpm,
        burst_capacity=serper_concurrent
    ))

    # DataForSEO: varies by plan
    dfs_rpm = int(__import__('os').environ.get("DATAFORSEO_REQUESTS_PER_MINUTE", 100))
    dfs_concurrent = int(__import__('os').environ.get("DATAFORSEO_CONCURRENT", 10))
    _rate_limiter.register_provider("dataforseo", RateLimitConfig(
        max_concurrent=dfs_concurrent,
        requests_per_minute=dfs_rpm,
        burst_capacity=dfs_concurrent
    ))

    # Default for any other provider
    default_rpm = int(__import__('os').environ.get("DEFAULT_REQUESTS_PER_MINUTE", 60))
    default_concurrent = int(__import__('os').environ.get("DEFAULT_CONCURRENT", 5))


# Auto-configure on import
configure_rate_limits_from_env()
