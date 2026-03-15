"""
API Request Validation Models
Provides Pydantic models for validating all API requests.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


class StartRunRequest(BaseModel):
    """Request to start a new pipeline run"""
    task: str = Field(..., min_length=1, max_length=1000, description="The SEO task/topic")
    target: Optional[str] = Field(None, max_length=500, description="Target market or niche")
    audience: Optional[str] = Field(None, max_length=500, description="Target audience description")
    domain: Optional[str] = Field(None, max_length=500, description="Target domain if applicable")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes or context")

    @field_validator('task')
    @classmethod
    def task_not_just_whitespace(cls, v):
        if v and not v.strip():
            raise ValueError('Task cannot be empty or whitespace only')
        return v.strip()


class ScheduleConfig(BaseModel):
    """Schedule configuration"""
    name: str = Field(..., min_length=1, max_length=200)
    frequency: str = Field(..., pattern=r'^(daily|weekly|monthly|custom)$')
    cron_expr: Optional[str] = Field(None, max_length=100)
    hour: int = Field(9, ge=0, le=23)
    minute: int = Field(0, ge=0, le=59)
    day_of_week: Optional[str] = Field(None, pattern=r'^(mon|tue|wed|thu|fri|sat|sun)$')
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    task_config: StartRunRequest

    @field_validator('cron_expr')
    @classmethod
    def validate_cron_if_custom(cls, v, info):
        freq = info.data.get('frequency')
        if freq == 'custom' and not v:
            raise ValueError('cron_expr is required for custom frequency')
        return v


class MemoryEntryRequest(BaseModel):
    """Request to add memory entry"""
    type: str = Field(..., pattern=r'^(learning|history)$')
    data: dict = Field(..., description="Entry data")

    @model_validator(mode='after')
    def validate_learning_structure(self):
        if self.type == 'learning':
            required_fields = ['task', 'insights']
            for field in required_fields:
                if field not in self.data:
                    raise ValueError(f'Learning entry must include "{field}" field')
        elif self.type == 'history':
            required_fields = ['run_id', 'task', 'status']
            for field in required_fields:
                if field not in self.data:
                    raise ValueError(f'History entry must include "{field}" field')
        return self


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration"""
    model: Optional[dict] = None
    pipeline: Optional[dict] = None
    env: Optional[dict] = None

    @model_validator(mode='after')
    def at_least_one_field(self):
        if not any([self.model, self.pipeline, self.env]):
            raise ValueError('At least one of model, pipeline, or env must be provided')
        return self


class ToolCallRequest(BaseModel):
    """Request to call a tool"""
    query: Optional[str] = Field(None, min_length=1)
    keywords: Optional[List[str]] = Field(None, min_items=1)
    limit: Optional[int] = Field(None, ge=1, le=1000)
    num_results: Optional[int] = Field(None, ge=1, le=100)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    location_code: Optional[int] = Field(None)
    site_url: Optional[str] = Field(None)
    page_url: Optional[str] = Field(None)
    days: Optional[int] = Field(None, ge=1, ge=365)
    drop_threshold: Optional[float] = Field(None, ge=0)
    drop_pct: Optional[float] = Field(None, ge=0, le=100)
    run_id: Optional[str] = Field(None)
    stage: Optional[str] = Field(None)
    data: Optional[dict] = Field(None)
    line: Optional[str] = Field(None)
