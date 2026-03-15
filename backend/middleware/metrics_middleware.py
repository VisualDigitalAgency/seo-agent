"""
FastAPI Metrics Middleware
Records API call counts and errors for monitoring.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from . import metrics as app_metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to record API call metrics."""

    async def dispatch(self, request: Request, call_next):
        start_time = None  # Could be used for latency tracking

        try:
            response = await call_next(request)
            # Record successful call
            app_metrics.increment_api_call(request.url.path)
            return response
        except Exception as e:
            # Record error
            app_metrics.increment_api_error(request.url.path)
            raise
