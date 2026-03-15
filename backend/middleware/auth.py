"""
Authentication middleware for SEO Agent backend

Implements API key-based authentication to protect admin endpoints.
"""

import os
import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("auth")
from audit_logger import log_audit

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates API keys for protected endpoints."""

    def __init__(self, app, allowed_endpoints):
        super().__init__(app)
        self.allowed_endpoints = allowed_endpoints
        self.valid_api_keys = self._load_api_keys()

    def _load_api_keys(self) -> list[str]:
        """Load API keys from environment variables."""
        # API keys can be provided as comma-separated values in environment variables
        # or as a single API_KEY env var
        api_keys = os.environ.get("API_KEYS", os.environ.get("API_KEY", ""))
        if not api_keys:
            logger.warning("No API keys configured. Authentication is disabled.")
            return []

        # Split by comma and strip whitespace
        return [key.strip() for key in api_keys.split(",") if key.strip()]

    def _get_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from request headers."""
        # Check for X-API-Key header first
        api_key = request.headers.get("x-api-key")
        if api_key:
            return api_key

        # Check for Authorization: Bearer <token> header
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()

        return None

    def _is_protected_endpoint(self, path: str) -> bool:
        """Check if endpoint is protected by authentication."""
        # Check if path matches any protected endpoint pattern
        for pattern in self.allowed_endpoints:
            if pattern.endswith("/*"):
                # Wildcard pattern (e.g., "/api/run/*")
                if path.startswith(pattern[:-1]):
                    return True
            elif path == pattern:
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        # Only apply auth to protected endpoints
        if self._is_protected_endpoint(request.url.path):
            api_key = self._get_api_key(request)

            # If no API keys are configured, allow all requests (fallback for development)
            if not self.valid_api_keys:
                # If no API keys are configured, allow all requests (fallback for development)
                # but log this for audit purposes
                log_audit(
                    action="auth_disabled",
                    resource=request.url.path,
                    request=request,
                    details={"reason": "no_api_keys_configured"}
                )
                return await call_next(request)

            # Validate the API key
            if not api_key:
                log_audit(
                    action="auth_failure",
                    resource=request.url.path,
                    request=request,
                    details={"reason": "missing_api_key"}
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "missing_api_key",
                        "message": "API key is required for this endpoint"
                    }
                )

            if api_key not in self.valid_api_keys:
                logger.warning(f"Unauthorized access attempt to {request.url.path} with invalid API key")
                log_audit(
                    action="auth_failure",
                    resource=request.url.path,
                    request=request,
                    details={"reason": "invalid_api_key", "provided_key_prefix": api_key[:8] if api_key else None}
                )
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "invalid_api_key",
                        "message": "Invalid API key"
                    }
                )

            # Authentication successful - log it
            log_audit(
                action="auth_success",
                resource=request.url.path,
                request=request,
                details={"api_key_prefix": api_key[:8] if api_key else None}
            )

        response = await call_next(request)

        # After successful completion of admin action, also log success (we'll also log specific actions separately)
        return response

        return await call_next(request)


def get_auth_middleware(app):
    """Get configured authentication middleware."""
    # Define protected endpoints (including wildcard patterns)
    protected_endpoints = [
        "/api/run/*",
        "/config",
        "/api/memory",
        "/api/schedules/*",
        "/api/stream/*",
        "/logs/*",
    ]

    return APIKeyAuthMiddleware(app, protected_endpoints)