"""Tests for ActionAgent: dry-run and safety interception."""

import asyncio
import sys

sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from agents.action import ActionAgent, CONFIDENCE_THRESHOLD
from models import ActionInput, ActionOutput, RootCause


def _run(coro):
    return asyncio.run(coro)


def test_action_skipped_when_low_confidence():
    """Action should be skipped when root cause confidence < 0.7."""
    agent = ActionAgent()

    low_confidence_cause = RootCause(
        cause="Possible upstream issue",
        confidence=0.55,
        evidence=["Some weak evidence"],
    )

    result = _run(agent.run(ActionInput(root_cause=low_confidence_cause)))

    assert result.status == "skipped"
    assert result.action_taken is None
    assert "需人工" in result.message or "人工" in result.message


def test_action_executed_when_high_confidence():
    """Action should be executed when root cause confidence >= 0.7."""
    agent = ActionAgent()

    high_confidence_cause = RootCause(
        cause="Database connection pool leak causing thread exhaustion",
        confidence=0.85,
        evidence=["connection_pool_usage at 0.98", "Thread pool exhausted errors"],
    )

    result = _run(agent.run(ActionInput(root_cause=high_confidence_cause)))

    assert result.status == "executed"
    assert result.action_taken is not None
    assert "restart_connection_pool" in result.action_taken


def test_dry_run_before_execution():
    """Dry run should be called before actual execution."""
    agent = ActionAgent()

    cause = RootCause(
        cause="Database connection pool leak",
        confidence=0.90,
        evidence=["Pool usage at 98%"],
    )

    # Dry run should produce a simulation message
    dry_run_result = agent._dry_run("restart_connection_pool", cause)
    assert "[DRY RUN]" in dry_run_result

    # Execute should log the action
    exec_result = agent._execute_action("restart_connection_pool", cause)
    assert "mock" in exec_result.lower()


def test_notification_message_format():
    """Notification should contain root cause, action, and estimated recovery."""
    agent = ActionAgent()

    cause = RootCause(
        cause="Connection pool exhaustion",
        confidence=0.88,
        evidence=["Pool usage >90%", "Thread pool full"],
    )

    result = _run(agent.run(ActionInput(root_cause=cause)))

    # Message should contain key information
    assert "根因" in result.message
    assert "置信度" in result.message
    assert "执行动作" in result.message


def test_circuit_breaker_action():
    """Timeout-related root cause should trigger circuit breaker."""
    agent = ActionAgent()

    cause = RootCause(
        cause="Upstream dependency timeout causing cascading failures",
        confidence=0.75,
        evidence=["Timeout errors", "503 responses"],
    )

    result = _run(agent.run(ActionInput(root_cause=cause)))

    assert result.status == "executed"
    assert result.action_taken == "circuit_breaker_trip"