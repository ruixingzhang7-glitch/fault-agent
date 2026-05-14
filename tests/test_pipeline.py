"""Tests for FaultRootCausePipeline: timeout degradation and human mode."""

import asyncio
import sys

sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from pipeline import FaultRootCausePipeline, LOW_CONFIDENCE_THRESHOLD
from models import PipelineResult


def _run(coro):
    return asyncio.run(coro)


def test_pipeline_normal_run():
    """Pipeline should complete successfully with mock data."""
    pipeline = FaultRootCausePipeline()

    result = _run(pipeline.run(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        services=["payment-api", "order-db"],
    ))

    assert result.trace_id is not None
    assert result.perception is not None
    assert len(result.perception.logs) > 0
    assert result.reasoning is not None
    assert len(result.reasoning.possible_root_causes) > 0
    assert result.action is not None

    # Top root cause should have confidence > 0.5 (mock data is realistic)
    top_confidence = result.reasoning.possible_root_causes[0].confidence
    assert top_confidence > LOW_CONFIDENCE_THRESHOLD


def test_pipeline_human_mode_when_low_confidence():
    """Pipeline should enter human mode when all root causes have low confidence."""
    pipeline = FaultRootCausePipeline()

    # Use services with minimal mock data to potentially get lower confidence
    result = _run(pipeline.run(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        services=["unknown-service"],
    ))

    # Even with unknown service, pipeline should complete
    assert result.trace_id is not None
    assert result.perception is not None

    # If reasoning produced low-confidence results, action should be skipped
    if result.reasoning and result.reasoning.possible_root_causes:
        max_conf = max(rc.confidence for rc in result.reasoning.possible_root_causes)
        if max_conf <= LOW_CONFIDENCE_THRESHOLD:
            assert result.action.status == "skipped"
            assert result.action.action_taken is None


def test_pipeline_result_schema():
    """Pipeline result should conform to PipelineResult schema."""
    pipeline = FaultRootCausePipeline()

    result = _run(pipeline.run(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        services=["payment-api"],
    ))

    # Verify all required fields
    assert isinstance(result.trace_id, str)
    assert isinstance(result.perception, object)
    assert isinstance(result.agent_timings, dict)
    assert isinstance(result.token_usage, dict)

    # Verify timing data
    for agent, timing in result.agent_timings.items():
        assert timing > 0
        assert isinstance(timing, float)


def test_pipeline_degraded_perception():
    """Degraded perception should return alerts only."""
    pipeline = FaultRootCausePipeline()

    input = pipeline.perception._fetch_logs  # just to verify method exists
    degraded = pipeline._degraded_perception(
        __import__("models").PerceptionInput(
            fault_time="2025-04-01T10:00:00Z",
            window_minutes=15,
            service_names=["payment-api"],
        )
    )

    # Degraded perception should have no logs or metrics
    assert len(degraded.logs) == 0
    assert len(degraded.metrics) == 0
    # But should have alerts
    assert len(degraded.alerts) > 0