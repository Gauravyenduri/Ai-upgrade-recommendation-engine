"""Pydantic request/response models (the public API contract)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RolloutStrategy(str, Enum):
    CANARY = "CANARY"
    LINEAR = "LINEAR"
    ALL_AT_ONCE = "ALL_AT_ONCE"


class Criticality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HourlyUsage(BaseModel):
    """Mean utilization (0-100) for a given hour of day (0-23)."""
    hour: int = Field(ge=0, le=23)
    utilization: float = Field(ge=0, le=100)


class ResourceMetrics(BaseModel):
    resource_id: str
    resource_type: str = "database"
    current_version: str
    target_version: str
    criticality: Criticality = Criticality.MEDIUM
    # operational metrics
    error_rate: float = Field(0.0, ge=0, le=1, description="recent error ratio 0-1")
    cpu_p95: float = Field(0.0, ge=0, le=100)
    open_incidents: int = Field(0, ge=0)
    days_since_last_upgrade: int = Field(0, ge=0)
    # usage pattern (24 entries ideally)
    hourly_usage: list[HourlyUsage] = Field(default_factory=list)


class MaintenanceWindowSuggestion(BaseModel):
    start_hour_utc: int
    end_hour_utc: int
    rationale: str


class RecommendationRequest(BaseModel):
    metrics: ResourceMetrics
    # if true, force generation of an LLM narrative even for low-risk items
    explain_verbose: bool = False


class Recommendation(BaseModel):
    resource_id: str
    recommended_strategy: RolloutStrategy
    risk_score: float = Field(ge=0, le=1)
    maintenance_window: MaintenanceWindowSuggestion
    requires_human_review: bool
    factors: list[str]
    explanation: str
    generated_at: datetime
    review_status: str = "PENDING"


class ReviewDecision(BaseModel):
    reviewer: str
    approved: bool
    note: Optional[str] = None
