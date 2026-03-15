"""
Utility functions for error handling, timeouts, and circuit breaker patterns
for external API calls.
"""

import asyncio
import logging
import threading
import time
import random
from typing import Any, Dict, Optional, TypeVar, Callable
from dataclasses import dataclass

logger = logging.getLogger("seo-backend")


T = TypeVar("T")


@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking."""
    failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    threshold: int = 5
    timeout: float = 60.0  # seconds to stay open


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, name: str, threshold: int = 5, timeout: float = 60.0):
        self.name = name
        self.state = CircuitBreakerState(
            threshold=threshold,
            timeout=timeout
        )
        self._lock = threading.Lock()

    def can_call(self) -> bool:
        """Check if calls are allowed (circuit not OPEN)."""
        now = time.time()
        with self._lock:
            if self.state.state == "OPEN":
                # Check if timeout expired to allow test call
                if (now - self.state.last_failure_time) >= self.state.timeout:
                    # Transition to HALF_OPEN
                    self.state.state = "HALF_OPEN"
                    self.state.failures = 0
                    logger.info(f"Circuit breaker for {self.name} transitioning to HALF_OPEN")
                    return True
                return False
            return True

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call a function with circuit breaker protection."""
        if not self.can_call():
            logger.warning(f"Circuit breaker for {self.name} is OPEN - skipping call")
            raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def record_success(self):
        """Record a successful call."""
        with self._lock:
            now = time.time()
            if self.state.state == "HALF_OPEN":
                logger.info(f"Circuit breaker for {self.name} succeeded - closing")
                self.state.state = "CLOSED"
                self.state.failures = 0
            elif self.state.state == "OPEN":
                self.state.state = "CLOSED"
                self.state.failures = 0
            self.state.last_success_time = now

    def record_failure(self):
        """Record a failed call."""
        with self._lock:
            now = time.time()
            self.state.failures += 1
            self.state.last_failure_time = now

            if self.state.failures >= self.state.threshold:
                self.state.state = "OPEN"
                logger.error(f"Circuit breaker for {self.name} OPENED after {self.state.failures} failures")


async def exponential_backoff_retry(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    **kwargs
) -> T:
    """Retry a function with exponential backoff and jitter."""

    for attempt in range(max_retries):
        try:
            # Add jitter for first attempt too
            delay = base_delay * (2 ** attempt)
            if jitter:
                delay *= random.uniform(0.5, 1.5)

            if attempt > 0:
                # Wait before retrying
                await asyncio.sleep(min(delay, max_delay))

            result = await func(**kwargs)

            # Only log retries if not the first attempt
            if attempt > 0:
                logger.info(f"Retry succeeded for {func.__name__} after {attempt} attempts")

            return result

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}")

            # Last attempt - raise the exception
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed for {func.__name__}")
                raise


async def call_with_timeout(
    func: Callable[..., T],
    timeout: float = 30.0,
    **kwargs
) -> T:
    """Call a function with timeout."""
    try:
        return await asyncio.wait_for(func(**kwargs), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Timeout of {timeout}s exceeded for {func.__name__}")
        raise


async def safe_call(
    func: Callable[..., T],
    error_message: str = "Operation failed",
    default_value: Optional[T] = None,
    log_error: bool = True,
    **kwargs
) -> Optional[T]:
    """Call a function safely and return default value on error."""
    try:
        return await func(**kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"{error_message}: {str(e)}", exc_info=True)
        return default_value


def format_error_response(
    error: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500
) -> Dict[str, Any]:
    """Format a structured error response."""
    return {
        "error": error,
        "status_code": status_code,
        "timestamp": time.time(),
        "details": details or {}
    }


async def log_and_reraise(
    error: Exception,
    context: str = "",
    log_full_trace: bool = True
):
    """Log an error and re-raise it."""
    if log_full_trace:
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    else:
        logger.error(f"Error in {context}: {str(error)}")
    raise error