"""
Persistent tool call logger
Stores tool calls to disk with rotation.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from threading import Lock

from fs_utils import _base

TOOL_LOG_DIR = lambda: _base() / "tool_logs"
TOOL_LOG_FILE = lambda: TOOL_LOG_DIR() / "tool_calls.jsonl"
MAX_LOG_SIZE_MB = 10
MAX_LOG_FILES = 7  # Keep 7 days of logs

_lock = Lock()


class PersistentToolLogger:
    """Logs tool calls to rotating JSONL files."""

    def __init__(self):
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        TOOL_LOG_DIR().mkdir(parents=True, exist_ok=True)

    def _get_current_log_path(self) -> Path:
        """Get today's log file path with date suffix."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return TOOL_LOG_DIR() / f"tool_calls.{today}.jsonl"

    def log_call(self, entry: dict):
        """Write a tool call entry to the log."""
        with _lock:
            log_path = self._get_current_log_path()
            try:
                with open(log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")

                # Check if we need to rotate (size-based)
                if log_path.exists() and log_path.stat().st_size > MAX_LOG_SIZE_MB * 1024 * 1024:
                    self._rotate_logs()
            except Exception as e:
                # Don't break the app if logging fails
                print(f"Failed to write tool log: {e}")

    def _rotate_logs(self):
        """Remove old log files beyond retention limit."""
        try:
            log_files = sorted(TOOL_LOG_DIR().glob("tool_calls.*.jsonl"))
            if len(log_files) > MAX_LOG_FILES:
                for old_file in log_files[:-MAX_LOG_FILES]:
                    old_file.unlink(missing_ok=True)
        except Exception as e:
            print(f"Log rotation failed: {e}")

    def get_recent_calls(self, days: int = 1, limit: int = 1000) -> list[dict]:
        """Read recent tool calls from log files."""
        calls = []
        try:
            # Get files for last N days
            from datetime import timedelta
            today = datetime.utcnow().date()
            for i in range(days):
                target_date = today - timedelta(days=i)
                date_str = target_date.strftime("%Y-%m-%d")
                log_file = TOOL_LOG_DIR() / f"tool_calls.{date_str}.jsonl"
                if log_file.exists():
                    with open(log_file) as f:
                        for line in f:
                            if line.strip():
                                try:
                                    calls.append(json.loads(line))
                                except json.JSONDecodeError:
                                    continue
                            if len(calls) >= limit:
                                break
                if len(calls) >= limit:
                    break
        except Exception as e:
            print(f"Failed to read tool logs: {e}")

        return calls[-limit:]  # Return most recent


# Global persistent logger instance
_persistent_logger = PersistentToolLogger()


def log_tool_call_persistent(entry: dict):
    """Log a tool call to persistent storage."""
    _persistent_logger.log_call(entry)


def get_persistent_tool_calls(days: int = 1, limit: int = 1000) -> list[dict]:
    """Retrieve persistent tool calls."""
    return _persistent_logger.get_recent_calls(days, limit)
