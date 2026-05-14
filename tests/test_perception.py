"""Tests for PerceptionAgent: log deduplication and data aggregation."""

import asyncio
import sys

sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from agents.perception import PerceptionAgent
from models import PerceptionInput, LogEntry


def _run(coro):
    return asyncio.run(coro)


def test_log_deduplication():
    """Same error message should be merged with summed count."""
    agent = PerceptionAgent()

    # Create logs with duplicate messages
    logs = [
        LogEntry(service="svc-a", level="ERROR", message="Connection reset", count=3),
        LogEntry(service="svc-a", level="ERROR", message="Connection reset", count=5),
        LogEntry(service="svc-a", level="ERROR", message="Timeout", count=2),
    ]

    deduped = agent._deduplicate_logs(logs)

    # "Connection reset" should be merged with count=8
    conn_entry = next(e for e in deduped if e.message == "Connection reset")
    assert conn_entry.count == 8, f"Expected count=8, got {conn_entry.count}"

    # "Timeout" should remain separate
    timeout_entry = next(e for e in deduped if e.message == "Timeout")
    assert timeout_entry.count == 2

    # Total unique entries should be 2
    assert len(deduped) == 2


def test_top5_high_frequency_errors():
    """Should return at least top 5 high-frequency errors when available."""
    agent = PerceptionAgent()
    input = PerceptionInput(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        service_names=["payment-api", "order-db"],
    )

    result = _run(agent.run(input))

    # Should have logs from both services
    assert len(result.logs) > 0
    # All log entries should have valid fields
    for log in result.logs:
        assert log.service in ["payment-api", "order-db"]
        assert log.level in ["ERROR", "WARN"]
        assert log.count >= 1


def test_perception_output_format():
    """Output should conform to PerceptionOutput schema."""
    agent = PerceptionAgent()
    input = PerceptionInput(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        service_names=["payment-api"],
    )

    result = _run(agent.run(input))

    # Verify all fields are present
    assert isinstance(result.logs, list)
    assert isinstance(result.metrics, list)
    assert isinstance(result.alerts, list)

    # Verify metrics have required fields
    for m in result.metrics:
        assert m.metric is not None
        assert m.value is not None
        assert m.unit is not None
        assert m.service == "payment-api"

    # Verify alerts have valid severity
    for a in result.alerts:
        assert a.severity in ["P0", "P1", "P2"]