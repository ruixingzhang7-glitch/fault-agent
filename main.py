"""Example entry point for the fault root cause analysis pipeline."""

import asyncio
import json
import sys

# Ensure project root is in path for imports
sys.path.insert(0, "/Users/wisers/Desktop/aiops/fault_agent")

from pipeline import FaultRootCausePipeline


async def demo():
    """Run a demo fault root cause analysis."""
    pipeline = FaultRootCausePipeline()

    result = await pipeline.run(
        fault_time="2025-04-01T10:00:00Z",
        window_minutes=15,
        services=["payment-api", "order-db"],
    )

    # Print structured result
    print("\n" + "=" * 60)
    print("故障根因定位结果")
    print("=" * 60)
    print(f"Trace ID: {result.trace_id}")

    print("\n── 感知数据 ──")
    print(f"  日志条数: {len(result.perception.logs)}")
    for log in result.perception.logs[:5]:
        print(f"    [{log.service}] {log.level}: {log.message} (count={log.count})")
    print(f"  指标条数: {len(result.perception.metrics)}")
    for m in result.perception.metrics[:4]:
        print(f"    [{m.service}] {m.metric}={m.value}{m.unit}")
    print(f"  告警条数: {len(result.perception.alerts)}")
    for a in result.perception.alerts[:3]:
        print(f"    [{a.alert_name}] {a.severity} since {a.start_time}")

    if result.reasoning:
        print("\n── 推理结果 ──")
        for rc in result.reasoning.possible_root_causes:
            print(f"  根因: {rc.cause}")
            print(f"  置信度: {rc.confidence:.2f}")
            print(f"  证据: {', '.join(rc.evidence[:3])}")
        if result.reasoning.similar_past_cases:
            print(f"  相似历史案例: {', '.join(result.reasoning.similar_past_cases)}")

    if result.action:
        print("\n── 行动结果 ──")
        print(f"  执行动作: {result.action.action_taken or '无'}")
        print(f"  状态: {result.action.status}")
        print(f"  通知内容:\n{result.action.message}")

    print("\n── 执行统计 ──")
    for agent, timing in result.agent_timings.items():
        print(f"  {agent}: {timing:.2f}s")
    if result.error:
        print(f"  错误: {result.error}")

    print("=" * 60)

    # Also output as JSON for programmatic consumption
    print("\nJSON 输出:")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(demo())