"""
Tests for fs_utils security and basic functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import fs_utils as fs


def test_run_id_validation_rejects_path_traversal():
    """Test that malicious run_ids are rejected."""
    malicious_ids = [
        "../../../etc/passwd",
        "..\\windows\\system32",
        "run_../etc/passwd",
        "run_20260101_120000/../../../etc/passwd",
        "run_20260101_120000..",  # Directory traversal via ..
        "run_",  # Incomplete
        "run_2026",  # Too short
        "run_20260101_120000_extra",  # Too long
        "",  # Empty
        "random_string",
    ]

    for run_id in malicious_ids:
        with pytest.raises(ValueError):
            fs.get_run_dir(run_id)


def test_run_id_validation_accepts_valid():
    """Test that valid run_ids are accepted."""
    valid_ids = [
        "run_20260101_120000",
        "run_20261231_235959",
        "run_20260101_000000",
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily override _base to use temp dir
        original_base = fs._base
        fs._base = lambda: Path(tmpdir)

        try:
            for run_id in valid_ids:
                # Should not raise
                run_dir = fs.get_run_dir(run_id)
                assert run_dir.exists()
                assert run_dir.is_dir()
                assert run_id in str(run_dir)
        finally:
            fs._base = original_base


def test_csv_injection_prevention():
    """Test that CSV fields are properly escaped."""
    dangerous_inputs = [
        "=cmd|'/c calc'!A1",  # Excel formula
        "+cmd|'/c calc'!A1",
        "-cmd|'/c calc'!A1",
        "@SUM(1+1)",
        "\t=1+1",
        "\r=1+1",
        "\n=1+1",
    ]

    for dangerous in dangerous_inputs:
        row = {"run_id": "test", "task": dangerous}
        # The function should escape this
        from fs_utils import _escape_csv_field
        escaped = _escape_csv_field(dangerous)
        assert escaped.startswith("'"), f"Failed to escape: {dangerous}"


def test_tool_call_logging():
    """Test that tool call logging works."""
    from main_api import log_tool_call

    # Clear existing log
    from main_api import tool_call_log
    initial_len = len(tool_call_log)

    log_tool_call("test_tool", {"arg": "value"}, {"result": "ok"}, 100)

    assert len(tool_call_log) == initial_len + 1
    entry = tool_call_log[-1]
    assert entry["tool"] == "test_tool"
    assert entry["duration_ms"] == 100
    assert entry["status"] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
