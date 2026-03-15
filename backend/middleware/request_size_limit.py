"""
FastAPI Middleware: Request Size Limit
Rejects requests with Content-Length exceeding configured limit.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Maximum request body size in bytes (default 10MB)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce maximum request body size."""

    def __init__(self, app, max_size: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "request_too_large",
                            "message": f"Request body size exceeds maximum allowed size of {self.max_size} bytes",
                            "max_size": self.max_size,
                            "received_size": size
                        }
                    )
            except ValueError:
                # Invalid content-length header, let it pass through
                pass

        response = await call_next(request)
        return response
