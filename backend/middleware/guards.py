"""
Permission Guard Middleware
Enforces LLM access policy:
  ✅ GET  — read operations
  ✅ POST — create / write operations
  ❌ DELETE, PUT, PATCH — blocked entirely
  ❌ Any POST body containing destructive intent keywords — blocked

This is the single enforcement point. The LLM physically cannot delete
anything because those HTTP methods and endpoint patterns don't exist
and are rejected here before any handler runs.
"""

import json
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


# HTTP methods the LLM is never allowed to use
BLOCKED_METHODS = {"DELETE", "PUT", "PATCH"}

# Destructive keywords that should never appear in a tool server request body.
# Belt-and-suspenders check — these would be caught by missing endpoints anyway,
# but this adds a logging + rejection layer.
DESTRUCTIVE_PATTERNS = [
    r'\bdelete\b', r'\bdrop\b', r'\btruncate\b', r'\bdestroy\b',
    r'\bremove_file\b', r'\bunlink\b', r'\brmdir\b', r'\bshutil\.rmtree\b',
    r'\bos\.remove\b', r'\bfs\.unlink\b',
]

DESTRUCTIVE_RE = re.compile('|'.join(DESTRUCTIVE_PATTERNS), re.IGNORECASE)


class PermissionGuard(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        # ── 1. Block forbidden HTTP methods ─────────────────────────────────
        if request.method in BLOCKED_METHODS:
            return JSONResponse(
                status_code=405,
                content={
                    "error": "method_not_allowed",
                    "message": f"HTTP {request.method} is not permitted. "
                               "LLM tools have read (GET) and create/write (POST) access only. "
                               "DELETE operations are blocked.",
                    "allowed_methods": ["GET", "POST"]
                }
            )

        # ── 2. Scan POST body for destructive intent keywords ────────────────
        if request.method == "POST" and request.url.path.startswith("/tools/"):
            try:
                body_bytes = await request.body()
                body_str   = body_bytes.decode("utf-8", errors="ignore")

                if DESTRUCTIVE_RE.search(body_str):
                    matched = DESTRUCTIVE_RE.findall(body_str)
                    _log_blocked(request, matched)
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "destructive_operation_blocked",
                            "message": "Request body contains a destructive operation keyword. "
                                       "LLM tools are create/write only.",
                            "matched_keywords": matched,
                        }
                    )

                # Re-attach the body so the route handler can read it
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive

            except Exception:
                pass  # Don't block on guard errors — let the route handle it

        return await call_next(request)


def _log_blocked(request: Request, keywords: list):
    import logging
    logger = logging.getLogger("permission_guard")
    logger.warning(
        f"BLOCKED: {request.method} {request.url.path} "
        f"— destructive keywords detected: {keywords} "
        f"— client: {request.client.host if request.client else 'unknown'}"
    )
