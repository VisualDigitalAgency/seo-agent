"""
Audit Logger
Logs administrative actions for security and compliance.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Callable, Any
from fastapi import Request

AUDIT_LOG_PATH = lambda: Path(os.getcwd() if not Path("/data").exists() else "/data") / "audit.log"


def log_audit(action: str, user: str = "anonymous", resource: str = None, details: dict = None, request: Request = None):
    """
    Write an audit log entry.

    Args:
        action: Action performed (e.g., "delete_run", "update_config", "create_schedule")
        user: User identifier (API key, username, etc.)
        resource: Resource affected (run_id, schedule_id, etc.)
        details: Additional details about the action
        request: FastAPI request object for extracting IP, user agent
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user": user,
        "resource": resource,
        "details": details or {},
    }

    if request:
        entry["ip"] = request.client.host if request.client else None
        entry["user_agent"] = request.headers.get("user-agent", "")

    log_line = json.dumps(entry) + "\n"

    try:
        AUDIT_LOG_PATH().parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH(), "a") as f:
            f.write(log_line)
    except Exception as e:
        # Don't let audit logging failure break the app
        print(f"Audit log write failed: {e}")


def audit_required(action: str = None, resource_getter: Callable = None):
    """
    Decorator for FastAPI endpoints to automatically log audit entries.

    Args:
        action: Audit action name. If None, derived from endpoint function name.
        resource_getter: Callable that returns resource identifier from request/response.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get('request') or (args[0] if args else None)
            user = _extract_user(request)

            # Determine action name
            act = action or func.__name__

            # Determine resource identifier
            res = None
            if resource_getter:
                try:
                    res = resource_getter(*args, **kwargs)
                except Exception:
                    pass

            # Call the original function
            result = await func(*args, **kwargs)

            # Log audit entry after successful completion
            log_audit(
                action=act,
                user=user,
                resource=res,
                request=request,
                details={"result": "success"}
            )

            return result
        return wrapper
    return decorator


def _extract_user(request: Request) -> str:
    """Extract user identifier from request."""
    # Check for API key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api:{api_key[:8]}..."  # Log partial key for privacy

    # Check for Bearer token
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return f"bearer:{token[:8]}..."

    return "anonymous"
