"""
Tests for validation module
"""

import pytest
from validation import StartRunRequest, MemoryEntryRequest, ConfigUpdateRequest


def test_start_run_request_valid():
    """Test valid StartRunRequest."""
    data = {
        "task": "Test SEO task",
        "target": "test.com",
        "audience": "developers",
        "domain": "example.com",
        "notes": "some notes"
    }
    req = StartRunRequest(**data)
    assert req.task == "Test SEO task"
    assert req.target == "test.com"


def test_start_run_request_missing_task():
    """Test StartRunRequest without task fails."""
    with pytest.raises(Exception):  # Pydantic validation error
        StartRunRequest(target="test.com")


def test_start_run_request_whitespace_task():
    """Test StartRunRequest with whitespace-only task fails."""
    with pytest.raises(Exception):
        StartRunRequest(task="   ")


def test_memory_entry_learning_valid():
    """Test valid learning memory entry."""
    data = {
        "type": "learning",
        "data": {
            "task": "keyword research",
            "insights": ["insight1", "insight2"]
        }
    }
    req = MemoryEntryRequest(**data)
    assert req.type == "learning"
    assert "insights" in req.data


def test_memory_entry_history_valid():
    """Test valid history memory entry."""
    data = {
        "type": "history",
        "data": {
            "run_id": "run_20260101_120000",
            "task": "test task",
            "status": "completed"
        }
    }
    req = MemoryEntryRequest(**data)
    assert req.type == "history"
    assert req.data["run_id"] == "run_20260101_120000"


def test_memory_entry_learning_missing_insights():
    """Test learning entry without insights fails."""
    with pytest.raises(Exception):
        MemoryEntryRequest(type="learning", data={"task": "test"})


def test_config_update_requires_fields():
    """Test ConfigUpdateRequest requires at least one field."""
    with pytest.raises(Exception):
        ConfigUpdateRequest()


def test_config_update_with_model():
    """Test ConfigUpdateRequest with model field."""
    req = ConfigUpdateRequest(model={"provider": "openrouter"})
    assert req.model == {"provider": "openrouter"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
