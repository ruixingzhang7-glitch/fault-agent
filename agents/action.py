"""Action Agent: executes recovery actions based on root cause analysis."""

from __future__ import annotations

import logging
import time

from models import ActionInput, ActionOutput, RootCause

logger = logging.getLogger("fault_agent")

# Safety threshold: don't auto-execute if confidence is below this
CONFIDENCE_THRESHOLD = 0.7


class ActionAgent:
    """Executes temporary recovery plans and notifies responsible engineers."""

    # Action registry: maps root cause keywords to recovery actions
    ACTION_MAP: dict[str, tuple[str, str]] = {
        "connection": ("restart_connection_pool", "重启连接池以释放泄漏连接"),
        "pool": ("restart_connection_pool", "重启连接池以释放泄漏连接"),
        "deadlock": ("rollback_last_deployment", "回滚最近部署以消除死锁引入的变更"),
        "timeout": ("circuit_breaker_trip", "触发熔断器以隔离超时依赖"),
        "rate limit": ("increase_rate_limit", "提升限流阈值以缓解流量压力"),
        "disk": ("circuit_breaker_trip", "触发熔断器以隔离磁盘满的数据库"),
        "latency": ("circuit_breaker_trip", "触发熔断器以隔离高延迟依赖"),
    }

    async def run(self, input: ActionInput) -> ActionOutput:
        """Execute recovery action or skip if confidence is too low."""
        start = time.monotonic()
        root_cause = input.root_cause

        # Safety check: skip auto-execution if confidence below threshold
        if root_cause.confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"Confidence {root_cause.confidence:.2f} < {CONFIDENCE_THRESHOLD}, "
                        f"skipping auto-execution")
            elapsed = time.monotonic() - start
            logger.info(f"ActionAgent completed in {elapsed:.2f}s (skipped)")
            return ActionOutput(
                action_taken=None,
                status="skipped",
                message=self._build_notification(root_cause, action=None, estimated_recovery="需人工评估"),
                notified_users=["值班工程师"],
            )

        # Find matching action
        action_name, action_desc = self._match_action(root_cause.cause)

        if action_name is None:
            logger.info(f"No matching action for root cause: {root_cause.cause}")
            elapsed = time.monotonic() - start
            logger.info(f"ActionAgent completed in {elapsed:.2f}s (no matching action)")
            return ActionOutput(
                action_taken=None,
                status="skipped",
                message=self._build_notification(root_cause, action=None, estimated_recovery="需人工评估"),
                notified_users=["值班工程师"],
            )

        # Dry run first
        dry_run_result = self._dry_run(action_name, root_cause)
        logger.info(f"Dry run result: {dry_run_result}")

        # Execute the action (mock)
        execution_result = self._execute_action(action_name, root_cause)
        logger.info(f"Execution result: {execution_result}")

        elapsed = time.monotonic() - start
        logger.info(f"ActionAgent completed in {elapsed:.2f}s (executed: {action_name})")

        return ActionOutput(
            action_taken=action_name,
            status="executed",
            message=self._build_notification(
                root_cause, action=f"{action_name} - {action_desc}",
                estimated_recovery="预计3-5分钟恢复",
            ),
            notified_users=["值班工程师", "服务负责人"],
        )

    def _match_action(self, cause: str) -> tuple[str | None, str | None]:
        """Match root cause description to a recovery action."""
        cause_lower = cause.lower()
        for keyword, (action, desc) in self.ACTION_MAP.items():
            if keyword in cause_lower:
                return action, desc
        return None, None

    def _dry_run(self, action_name: str, root_cause: RootCause) -> str:
        """Simulate the action without real effects. # TODO: 替换为生产 dry_run"""
        simulations = {
            "restart_connection_pool": f"[DRY RUN] 将重启 {root_cause.cause} 涉及服务的连接池，预计释放 {8} 个泄漏连接",
            "circuit_breaker_trip": f"[DRY RUN] 将触发熔断器隔离故障依赖，预计减少 {60}% 的错误传播",
            "rollback_last_deployment": f"[DRY RUN] 将回滚最近部署版本，预计恢复到稳定状态",
            "increase_rate_limit": f"[DRY RUN] 将提升限流阈值至当前值的2倍，预计允许更多请求通过",
        }
        return simulations.get(action_name, f"[DRY RUN] 未知动作: {action_name}")

    def _execute_action(self, action_name: str, root_cause: RootCause) -> str:
        """Execute the recovery action (mock). # TODO: 替换为生产 API"""
        # All actions are simulated — just log the execution
        logger.info(f"[ACTION] Executing: {action_name} for root cause: {root_cause.cause}")
        return f"Action {action_name} executed successfully (mock)"

    def _build_notification(
        self,
        root_cause: RootCause,
        action: str | None,
        estimated_recovery: str,
    ) -> str:
        """Build notification message for responsible engineers."""
        action_text = action if action else "无自动执行动作，需人工介入"
        confidence_text = f"置信度: {root_cause.confidence:.2f}"
        evidence_text = "证据: " + "; ".join(root_cause.evidence[:3])

        message = (
            f"【故障根因通知】\n"
            f"根因: {root_cause.cause}\n"
            f"{confidence_text}\n"
            f"{evidence_text}\n"
            f"执行动作: {action_text}\n"
            f"{estimated_recovery}\n"
        )

        # Simulate DingTalk/Feishu webhook notification
        self._send_notification(message)
        return message

    def _send_notification(self, message: str) -> None:
        """Simulate DingTalk/Feishu webhook. # TODO: 替换为真实 webhook"""
        print(f"\n{'='*50}")
        print(f"[钉钉/飞书 Webhook 模拟通知]")
        print(message)
        print(f"{'='*50}\n")