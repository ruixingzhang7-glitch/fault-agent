"""FaultRootCausePipeline: orchestrates the three agents with timeout and fallback."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid

from agents.perception import PerceptionAgent
from agents.reasoning import ReasoningAgent
from agents.action import ActionAgent
from models import (
    ActionInput,
    ActionOutput,
    PerceptionInput,
    PerceptionOutput,
    PipelineResult,
    ReasoningOutput,
)
from utils.logger import get_trace_id, setup_logger

logger = logging.getLogger("fault_agent")

PERCEPTION_TIMEOUT = 5.0  # seconds
LOW_CONFIDENCE_THRESHOLD = 0.5


class FaultRootCausePipeline:
    """Orchestrates Perception → Reasoning → Action with safety controls."""

    def __init__(self) -> None:
        self.perception = PerceptionAgent()
        self.reasoning = ReasoningAgent()
        self.action = ActionAgent()

    async def run(
        self,
        fault_time: str,
        window_minutes: int = 15,
        services: list[str] | None = None,
    ) -> PipelineResult:
        """Run the full fault root cause analysis pipeline."""
        trace_id = get_trace_id()
        setup_logger(trace_id)

        logger.info(f"Pipeline started: trace_id={trace_id}, "
                    f"fault_time={fault_time}, services={services}")

        result = PipelineResult(trace_id=trace_id)
        timings: dict[str, float] = {}
        tokens: dict[str, int] = {}

        # ── Step 1: Perception ──
        perception_input = PerceptionInput(
            fault_time=fault_time,
            window_minutes=window_minutes,
            service_names=services or [],
        )

        try:
            start = time.monotonic()
            perception_data = await asyncio.wait_for(
                self.perception.run(perception_input),
                timeout=PERCEPTION_TIMEOUT,
            )
            timings["perception"] = time.monotonic() - start
            result.perception = perception_data
            logger.info(f"Perception completed in {timings['perception']:.2f}s")
        except asyncio.TimeoutError:
            logger.warning(f"Perception timed out after {PERCEPTION_TIMEOUT}s, "
                           f"using degraded alert data")
            timings["perception"] = PERCEPTION_TIMEOUT
            result.perception = self._degraded_perception(perception_input)
            result.error = "perception_timeout_degraded"

        # ── Step 2: Reasoning ──
        try:
            start = time.monotonic()
            reasoning_data = await self.reasoning.run(result.perception)
            timings["reasoning"] = time.monotonic() - start
            result.reasoning = reasoning_data
            logger.info(f"Reasoning completed in {timings['reasoning']:.2f}s")
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            timings["reasoning"] = time.monotonic() - start
            result.error = f"reasoning_failed: {e}"
            result.action = ActionOutput(
                action_taken=None,
                status="skipped",
                message=f"推理失败，需人工排查。错误: {e}",
                notified_users=["值班工程师"],
            )
            result.agent_timings = timings
            result.token_usage = tokens
            return result

        # Check if all root causes have low confidence → human intervention mode
        if reasoning_data.possible_root_causes:
            max_confidence = max(
                rc.confidence for rc in reasoning_data.possible_root_causes
            )
            if max_confidence <= LOW_CONFIDENCE_THRESHOLD:
                logger.warning(f"All root causes have confidence ≤ {LOW_CONFIDENCE_THRESHOLD}, "
                               f"entering human intervention mode")
                result.action = ActionOutput(
                    action_taken=None,
                    status="skipped",
                    message="所有根因置信度 ≤ 0.5，需人工排查。"
                            f"候选根因: {', '.join(rc.cause for rc in reasoning_data.possible_root_causes)}",
                    notified_users=["值班工程师", "架构师"],
                )
                result.agent_timings = timings
                result.token_usage = tokens
                return result

        # ── Step 3: Action ──
        if reasoning_data.possible_root_causes:
            top_cause = reasoning_data.possible_root_causes[0]
            action_input = ActionInput(root_cause=top_cause)

            try:
                start = time.monotonic()
                action_data = await self.action.run(action_input)
                timings["action"] = time.monotonic() - start
                result.action = action_data
                logger.info(f"Action completed in {timings['action']:.2f}s")
            except Exception as e:
                logger.error(f"Action failed: {e}")
                timings["action"] = time.monotonic() - start
                result.action = ActionOutput(
                    action_taken=None,
                    status="skipped",
                    message=f"行动执行失败: {e}",
                    notified_users=["值班工程师"],
                )

        result.agent_timings = timings
        result.token_usage = tokens
        logger.info(f"Pipeline completed: trace_id={trace_id}")
        return result

    def _degraded_perception(self, input: PerceptionInput) -> PerceptionOutput:
        """Fallback: use only the most recent 1 minute of alerts when
        perception times out."""
        from models import AlertEntry
        from utils.mock_data import ALERTS_DATA

        alerts: list[AlertEntry] = []
        for svc in input.service_names:
            for a in ALERTS_DATA.get(svc, []):
                alerts.append(AlertEntry(
                    alert_name=a["alert_name"],
                    severity=a["severity"],
                    start_time=a["start_time"],
                ))

        logger.info(f"Degraded perception: using {len(alerts)} alerts only")
        return PerceptionOutput(
            logs=[],
            metrics=[],
            alerts=alerts,
        )