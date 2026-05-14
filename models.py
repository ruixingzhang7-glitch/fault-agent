"""Pydantic models for all agent inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Perception Agent ──

class LogEntry(BaseModel):
    service: str
    level: str = "ERROR"
    message: str
    count: int = 1


class MetricEntry(BaseModel):
    metric: str
    value: float
    unit: str
    service: str


class AlertEntry(BaseModel):
    alert_name: str
    severity: str = Field(pattern=r"^(P0|P1|P2)$")
    start_time: str  # ISO8601


class PerceptionInput(BaseModel):
    fault_time: str  # ISO8601
    window_minutes: int = 15
    service_names: list[str]


class PerceptionOutput(BaseModel):
    logs: list[LogEntry]
    metrics: list[MetricEntry]
    alerts: list[AlertEntry]


# ── Reasoning Agent ──

class RootCause(BaseModel):
    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


class ReasoningOutput(BaseModel):
    possible_root_causes: list[RootCause]
    similar_past_cases: list[str] = []
    reasoning_trace: str = ""


# ── Action Agent ──

class ActionInput(BaseModel):
    root_cause: RootCause


class ActionOutput(BaseModel):
    action_taken: str | None = None
    status: str = Field(pattern=r"^(executed|skipped)$")
    message: str
    notified_users: list[str] = []


# ── Pipeline ──

class PipelineResult(BaseModel):
    trace_id: str
    perception: PerceptionOutput | None = None
    reasoning: ReasoningOutput | None = None
    action: ActionOutput | None = None
    agent_timings: dict[str, float] = {}  # agent_name → seconds
    token_usage: dict[str, int] = {}  # agent_name → total_tokens
    error: str | None = None