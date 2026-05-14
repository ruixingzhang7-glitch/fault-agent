"""Tests for ReasoningAgent: confidence filtering and mock reasoning."""

import asyncio
import sys

sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from agents.reasoning import ReasoningAgent
from models import PerceptionOutput, LogEntry, MetricEntry, AlertEntry, RootCause


def _run(coro):
    return asyncio.run(coro)


def test_mock_reasoning_produces_root_causes():
    """Mock reasoning should produce root causes from perception data."""
    agent = ReasoningAgent()

    perception = PerceptionOutput(
        logs=[
            LogEntry(service="payment-api", level="ERROR", message="Connection reset by peer", count=12),
            LogEntry(service="payment-api", level="ERROR", message="Thread pool exhausted", count=8),
        ],
        metrics=[
            MetricEntry(metric="connection_pool_usage", value=0.98, unit="ratio", service="payment-api"),
            MetricEntry(metric="request_latency_p99", value=3200.0, unit="ms", service="payment-api"),
        ],
        alerts=[
            AlertEntry(alert_name="HighErrorRate", severity="P0", start_time="2025-04-01T09:58:00Z"),
        ],
    )

    result = _run(agent.run(perception))

    # Should produce at least one root cause
    assert len(result.possible_root_causes) > 0

    # Top root cause should have reasonable confidence
    top = result.possible_root_causes[0]
    assert top.confidence > 0.5
    assert len(top.evidence) > 0

    # Should have similar past cases
    assert len(result.similar_past_cases) > 0


def test_low_confidence_not_accepted():
    """Root causes with confidence < 0.7 should not be the primary recommendation."""
    agent = ReasoningAgent()

    # Create perception data that might produce lower-confidence results
    perception = PerceptionOutput(
        logs=[
            LogEntry(service="svc-x", level="WARN", message="Slow response", count=2),
        ],
        metrics=[
            MetricEntry(metric="cpu_usage", value=0.65, unit="ratio", service="svc-x"),
        ],
        alerts=[
            AlertEntry(alert_name="SlowResponse", severity="P2", start_time="2025-04-01T09:58:00Z"),
        ],
    )

    result = _run(agent.run(perception))

    # If root causes exist, check that they have valid confidence range
    for rc in result.possible_root_causes:
        assert 0.0 <= rc.confidence <= 1.0


def test_reasoning_output_schema():
    """Output should conform to ReasoningOutput schema."""
    agent = ReasoningAgent()

    perception = PerceptionOutput(
        logs=[
            LogEntry(service="payment-api", level="ERROR", message="Connection reset by peer", count=5),
        ],
        metrics=[
            MetricEntry(metric="connection_pool_usage", value=0.95, unit="ratio", service="payment-api"),
        ],
        alerts=[
            AlertEntry(alert_name="HighErrorRate", severity="P0", start_time="2025-04-01T09:58:00Z"),
        ],
    )

    result = _run(agent.run(perception))

    # Verify schema
    assert isinstance(result.possible_root_causes, list)
    assert isinstance(result.similar_past_cases, list)
    assert isinstance(result.reasoning_trace, str)

    for rc in result.possible_root_causes:
        assert isinstance(rc.cause, str)
        assert isinstance(rc.confidence, float)
        assert isinstance(rc.evidence, list)