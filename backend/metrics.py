"""
Monitoring Metrics Endpoint
Provides system and application metrics in Prometheus format or simple JSON.
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from fastapi import Request, Response, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

logger = logging.getLogger("seo-backend")

# Metrics storage (in-memory, could be backed by Redis in production)
_metrics = {
    "api_calls": defaultdict(int),
    "api_errors": defaultdict(int),
    "pipeline_runs": {"total": 0, "running": 0, "completed": 0, "failed": 0},
    "tool_calls": defaultdict(lambda: {"total": 0, "errors": 0, "total_duration_ms": 0}),
    "start_time": time.time(),
    "circuit_breaker_trips": defaultdict(int),
    "rate_limit_hits": defaultdict(int),
    "auth_failures": defaultdict(int),
    "security_blocks": defaultdict(int),
}

# Alert thresholds (configurable)
ALERT_THRESHOLDS = {
    "error_rate": 0.05,           # 5% error rate triggers alert
    "high_latency": 2000,        # 2 seconds average latency
    "circuit_breaker_open": 3,   # 3+ trips in 5 minutes
    "rate_limit_exceeded": 100,  # 100+ rate limit hits in 1 hour
    "auth_failures": 50,         # 50+ auth failures in 1 hour
    "security_blocks": 20,       # 20+ security blocks in 1 hour
}

# Lock for thread-safety if needed
import threading
_metrics_lock = threading.Lock()


def increment_api_call(endpoint: str):
    with _metrics_lock:
        _metrics["api_calls"][endpoint] += 1


def increment_api_error(endpoint: str):
    with _metrics_lock:
        _metrics["api_errors"][endpoint] += 1


def record_pipeline_run(status: str):
    with _metrics_lock:
        _metrics["pipeline_runs"]["total"] += 1
        if status in _metrics["pipeline_runs"]:
            _metrics["pipeline_runs"][status] += 1


def record_tool_call(tool_name: str, duration_ms: int, error: bool = False):
    with _metrics_lock:
        stats = _metrics["tool_calls"][tool_name]
        stats["total"] += 1
        stats["total_duration_ms"] += duration_ms
        if error:
            stats["errors"] += 1
        # Check for alert conditions
        if stats["errors"] / stats["total"] > ALERT_THRESHOLDS["error_rate"]:
            _trigger_alert(f"High error rate for tool {tool_name}")
        if stats["total_duration_ms"] / stats["total"] > ALERT_THRESHOLDS["high_latency"]:
            _trigger_alert(f"High latency for tool {tool_name}")

def record_circuit_breaker_trip(provider: str):
    with _metrics_lock:
        _metrics["circuit_breaker_trips"][provider] += 1
        if _metrics["circuit_breaker_trips"][provider] >= ALERT_THRESHOLDS["circuit_breaker_open"]:
            _trigger_alert(f"Circuit breaker open for provider {provider}")

def record_rate_limit_hit(endpoint: str):
    with _metrics_lock:
        _metrics["rate_limit_hits"][endpoint] += 1
        if _metrics["rate_limit_hits"][endpoint] >= ALERT_THRESHOLDS["rate_limit_exceeded"]:
            _trigger_alert(f"High rate limit hits for endpoint {endpoint}")

def record_auth_failure(endpoint: str):
    with _metrics_lock:
        _metrics["auth_failures"][endpoint] += 1
        if _metrics["auth_failures"][endpoint] >= ALERT_THRESHOLDS["auth_failures"]:
            _trigger_alert(f"High authentication failures for endpoint {endpoint}")

def record_security_block(action: str):
    with _metrics_lock:
        _metrics["security_blocks"][action] += 1
        if _metrics["security_blocks"][action] >= ALERT_THRESHOLDS["security_blocks"]:
            _trigger_alert(f"High security blocks for action {action}")


def get_uptime_seconds() -> float:
    return time.time() - _metrics["start_time"]


def get_active_runs_count() -> int:
    """Count currently running pipelines."""
    try:
        import fs_utils as fs
        runs = fs.list_all_runs()
        return sum(1 for r in runs if r.get("status") == "running")
    except Exception:
        return 0


def get_metrics_prometheus() -> str:
    """Return metrics in Prometheus text format."""
    lines = []

    # Uptime
    uptime = get_uptime_seconds()
    lines.append(f"# HELP seo_uptime_seconds Application uptime in seconds")
    lines.append(f"# TYPE seo_uptime_seconds gauge")
    lines.append(f"seo_uptime_seconds {uptime}")

    # Active runs
    active_runs = get_active_runs_count()
    lines.append(f"# HELP seo_active_runs Number of currently running pipelines")
    lines.append(f"# TYPE seo_active_runs gauge")
    lines.append(f"seo_active_runs {active_runs}")

    # Pipeline runs total
    pr = _metrics["pipeline_runs"]
    lines.append(f"# HELP seo_pipeline_runs_total Total number of pipeline runs")
    lines.append(f"# TYPE seo_pipeline_runs_total counter")
    lines.append(f"seo_pipeline_runs_total {pr.get('total', 0)}")

    # Pipeline runs by status
    for status in ["completed", "failed", "running"]:
        count = pr.get(status, 0)
        lines.append(f"# HELP seo_pipeline_runs_{status} Pipeline runs with status {status}")
        lines.append(f"# TYPE seo_pipeline_runs_{status} counter")
        lines.append(f"seo_pipeline_runs_{status} {count}")

    # API calls total
    api_calls = _metrics["api_calls"]
    lines.append(f"# HELP seo_api_calls_total Total API calls by endpoint")
    lines.append(f"# TYPE seo_api_calls_total counter")
    for endpoint, count in api_calls.items():
        lines.append(f'seo_api_calls_total{{endpoint="{endpoint}"}} {count}')

    # API errors total
    api_errors = _metrics["api_errors"]
    lines.append(f"# HELP seo_api_errors_total Total API errors by endpoint")
    lines.append(f"# TYPE seo_api_errors_total counter")
    for endpoint, count in api_errors.items():
        lines.append(f'seo_api_errors_total{{endpoint="{endpoint}"}} {count}')

    # Tool calls
    tool_stats = _metrics["tool_calls"]
    lines.append(f"# HELP seo_tool_calls_total Total calls to each tool")
    lines.append(f"# TYPE seo_tool_calls_total counter")
    lines.append(f"# HELP seo_tool_errors_total Total errors from each tool")
    lines.append(f"# TYPE seo_tool_errors_total counter")
    lines.append(f"# HELP seo_tool_call_duration_ms_total Total duration in ms for tool calls")
    lines.append(f"# TYPE seo_tool_call_duration_ms_total counter")

    for tool, stats in tool_stats.items():
        lines.append(f'seo_tool_calls_total{{tool="{tool}"}} {stats["total"]}')
        lines.append(f'seo_tool_errors_total{{tool="{tool}"}} {stats["errors"]}')
        lines.append(f'seo_tool_call_duration_ms_total{{tool="{tool}"}} {stats["total_duration_ms"]}')
        if stats["total"] > 0:
            avg = stats["total_duration_ms"] / stats["total"]
            lines.append(f"# HELP seo_tool_call_duration_ms_avg Average tool call duration")
            lines.append(f"# TYPE seo_tool_call_duration_ms_avg gauge")
            lines.append(f'seo_tool_call_duration_ms_avg{{tool="{tool}"}} {avg:.2f}')

    # Circuit breaker trips
    circuit_breaker_trips = _metrics["circuit_breaker_trips"]
    lines.append(f"# HELP seo_circuit_breaker_trips Total circuit breaker trips by provider")
    lines.append(f"# TYPE seo_circuit_breaker_trips counter")
    for provider, count in circuit_breaker_trips.items():
        lines.append(f'seo_circuit_breaker_trips{{provider="{provider}"}} {count}')

    # Rate limit hits
    rate_limit_hits = _metrics["rate_limit_hits"]
    lines.append(f"# HELP seo_rate_limit_hits Total rate limit hits by endpoint")
    lines.append(f"# TYPE seo_rate_limit_hits counter")
    for endpoint, count in rate_limit_hits.items():
        lines.append(f'seo_rate_limit_hits{{endpoint="{endpoint}"}} {count}')

    # Authentication failures
    auth_failures = _metrics["auth_failures"]
    lines.append(f"# HELP seo_auth_failures Total authentication failures by endpoint")
    lines.append(f"# TYPE seo_auth_failures counter")
    for endpoint, count in auth_failures.items():
        lines.append(f'seo_auth_failures{{endpoint="{endpoint}"}} {count}')

    # Security blocks
    security_blocks = _metrics["security_blocks"]
    lines.append(f"# HELP seo_security_blocks Total security blocks by action")
    lines.append(f"# TYPE seo_security_blocks counter")
    for action, count in security_blocks.items():
        lines.append(f'seo_security_blocks{{action="{action}"}} {count}')

    return "\n".join(lines) + "\n"


def _trigger_alert(message: str):
    """Trigger an alert. In production, this would send to PagerDuty, Slack, etc."""
    logger = logging.getLogger("seo-backend")
    logger.error(f"🚨 ALERT: {message}")
    # TODO: Integrate with actual alerting service (PagerDuty, Slack, etc.)
    # For now, log to file and include in metrics response
    _metrics.setdefault("alerts", []).append({
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "level": "critical"
    })
    # Keep only last 100 alerts in memory
    if len(_metrics.get("alerts", [])) > 100:
        _metrics["alerts"] = _metrics["alerts"][-100:]


def get_metrics_json() -> dict:
    """Return metrics in JSON format."""
    result = {
        "uptime_seconds": get_uptime_seconds(),
        "active_runs": get_active_runs_count(),
        "pipeline_runs": dict(_metrics["pipeline_runs"]),
        "api_calls": dict(_metrics["api_calls"]),
        "api_errors": dict(_metrics["api_errors"]),
        "tool_calls": {k: dict(v) for k, v in _metrics["tool_calls"].items()},
        "circuit_breaker_trips": dict(_metrics["circuit_breaker_trips"]),
        "rate_limit_hits": dict(_metrics["rate_limit_hits"]),
        "auth_failures": dict(_metrics["auth_failures"]),
        "security_blocks": dict(_metrics["security_blocks"]),
        "alerts": _metrics.get("alerts", [])[-20:],  # Last 20 alerts
    }

    # Calculate error rates
    for endpoint in _metrics["api_calls"]:
        calls = _metrics["api_calls"][endpoint]
        errors = _metrics["api_errors"].get(endpoint, 0)
        if calls > 0:
            result.setdefault("error_rates", {})[endpoint] = errors / calls

    return result
