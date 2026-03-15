"""
FastAPI Rate Limiting Middleware
Implements per-endpoint rate limiting for public API endpoints using slowapi.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Global rate limiter instance
# Default limits: 60 requests per minute and 1000 per hour per IP address
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute", "1000/hour"],
    strategy="fixed-window"  # simple implementation; can switch to "moving-window" for sliding windows
)

# Per-endpoint rate limits
PER_ENDPOINT_RATE_LIMITS = {
    "/api/run": ["5/minute", "20/hour"],
    "/api/run/{run_id}/resume": ["5/minute", "20/hour"],
    "/api/schedules": ["10/minute", "50/hour"],
    "/api/schedules/{id}": ["5/minute", "20/hour"],
    "/api/schedules/{id}/run-now": ["5/minute", "20/hour"],
    "/api/memory": ["10/minute", "50/hour"],
    "/config": ["5/minute", "20/hour"],
    "/tool-calls": ["20/minute", "100/hour"],
    "/logs/{run_id}": ["10/minute", "50/hour"],
    "/health": ["30/minute", "200/hour"],
    "/metrics": ["30/minute", "200/hour"],
}

# The limiter's error handler is handled by our FastAPI exception handler
# (registered in main_api.py). No custom @limiter.error_handler needed here.