"""Reasoning Agent: causal chain analysis with LLM and historical case matching."""

from __future__ import annotations

import json
import logging
import os
import time

from models import PerceptionOutput, ReasoningOutput, RootCause
from vector_store import VectorStore

logger = logging.getLogger("fault_agent")

# Few-shot prompt for LLM reasoning
REASONING_PROMPT = """You are a fault root cause analyst. Given monitoring data from a production incident, perform causal chain analysis to identify root causes.

## Input Format
You receive aggregated logs, metrics, and alerts from the fault time window.

## Analysis Steps
1. Extract suspicious clues: error spikes, latency increases, change events.
2. For each clue, expand a 3-layer causal chain (e.g., timeout → thread pool full → DB connection leak).
3. Assign a confidence score (0-1) to each root cause candidate based on evidence strength.

## Output Format (JSON)
{
  "possible_root_causes": [
    {"cause": "description of root cause", "confidence": 0.85, "evidence": ["evidence1", "evidence2"]}
  ],
  "reasoning_trace": "brief summary of reasoning process"
}

## Example
Input monitoring data:
- Logs: payment-api ERROR "Connection reset by peer" (count=12), "Thread pool exhausted" (count=8)
- Metrics: payment-api request_latency_p99=3200ms, connection_pool_usage=0.98
- Alerts: HighErrorRate P0, ThreadPoolExhausted P1

Output:
{
  "possible_root_causes": [
    {
      "cause": "Database connection leak in payment-api ORM layer causing thread pool exhaustion",
      "confidence": 0.88,
      "evidence": [
        "connection_pool_usage at 0.98 indicates near exhaustion",
        "Thread pool exhausted errors correlate with connection pool state",
        "Connection reset by peer suggests upstream DB rejecting connections"
      ]
    },
    {
      "cause": "Upstream payment gateway instability causing cascading failures",
      "confidence": 0.65,
      "evidence": [
        "Connection reset by peer could indicate gateway issues",
        "High error rate could be caused by external dependency"
      ]
    }
  ],
  "reasoning_trace": "High connection pool usage + thread exhaustion → likely connection leak; also considered upstream gateway as secondary cause"
}

---

Now analyze the following monitoring data and output your root cause analysis in JSON format:

Logs:
{logs}

Metrics:
{metrics}

Alerts:
{alerts}
"""


class ReasoningAgent:
    """Performs causal chain reasoning using LLM and historical case matching."""

    def __init__(self) -> None:
        self.vector_store = VectorStore()
        self._llm_available = bool(os.environ.get("OPENAI_API_KEY"))

    async def run(self, perception: PerceptionOutput) -> ReasoningOutput:
        """Run reasoning: LLM analysis + historical case cross-validation."""
        start = time.monotonic()

        # Build fault feature signature for vector search
        feature_sig = self._build_feature_signature(perception)

        # Retrieve similar historical cases
        similar_cases = self.vector_store.search(feature_sig, top_k=3)
        case_ids = [c["case_id"] for c in similar_cases]

        # LLM reasoning
        root_causes = await self._llm_reason(perception, similar_cases)

        elapsed = time.monotonic() - start
        logger.info(f"ReasoningAgent completed in {elapsed:.2f}s, "
                    f"root_causes={len(root_causes)}, similar_cases={len(case_ids)}")

        return ReasoningOutput(
            possible_root_causes=root_causes,
            similar_past_cases=case_ids,
            reasoning_trace=self._summarize_trace(root_causes, similar_cases),
        )

    def _build_feature_signature(self, perception: PerceptionOutput) -> str:
        """Build a text signature from perception data for vector search."""
        parts: list[str] = []
        for log in perception.logs:
            parts.append(f"{log.service} {log.level} {log.message}")
        for m in perception.metrics:
            parts.append(f"{m.service} {m.metric}={m.value}{m.unit}")
        for a in perception.alerts:
            parts.append(f"{a.alert_name} {a.severity}")
        return " ".join(parts)

    async def _llm_reason(
        self,
        perception: PerceptionOutput,
        similar_cases: list[dict],
    ) -> list[RootCause]:
        """Use LLM to analyze perception data and produce root cause candidates."""
        if not self._llm_available:
            logger.info("OPENAI_API_KEY not set, using mock reasoning")
            return self._mock_reason(perception, similar_cases)

        try:
            import openai
            client = openai.OpenAI()

            prompt = REASONING_PROMPT.format(
                logs=self._format_logs(perception.logs),
                metrics=self._format_metrics(perception.metrics),
                alerts=self._format_alerts(perception.alerts),
            )

            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            usage = response.usage
            if usage:
                logger.info(f"LLM token usage: prompt_tokens={usage.prompt_tokens}, "
                            f"completion_tokens={usage.completion_tokens}")

            content = response.choices[0].message.content
            parsed = json.loads(content)

            root_causes = [
                RootCause(
                    cause=rc["cause"],
                    confidence=rc["confidence"],
                    evidence=rc["evidence"],
                )
                for rc in parsed.get("possible_root_causes", [])
            ]

            # Cross-validate with historical cases: boost confidence if similar case exists
            for rc in root_causes:
                for case in similar_cases:
                    if self._cause_matches_case(rc.cause, case):
                        rc.confidence = min(rc.confidence + 0.05, 1.0)
                        rc.evidence.append(f"Similar past case: {case['case_id']} - {case['title']}")

            return root_causes

        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}, falling back to mock")
            return self._mock_reason(perception, similar_cases)

    def _mock_reason(
        self,
        perception: PerceptionOutput,
        similar_cases: list[dict],
    ) -> list[RootCause]:
        """Mock reasoning when LLM is unavailable."""
        root_causes: list[RootCause] = []

        # Analyze logs for clues
        for log in perception.logs:
            if "connection" in log.message.lower() or "pool" in log.message.lower():
                root_causes.append(RootCause(
                    cause="Database connection pool leak causing service degradation",
                    confidence=0.85,
                    evidence=[
                        f"Log: {log.message} (count={log.count})",
                        "Connection-related errors indicate pool exhaustion",
                    ],
                ))
            if "deadlock" in log.message.lower():
                root_causes.append(RootCause(
                    cause="Database deadlock cascade from concurrent operations",
                    confidence=0.75,
                    evidence=[
                        f"Log: {log.message} (count={log.count})",
                        "Deadlock errors suggest concurrent access conflicts",
                    ],
                ))
            if "timeout" in log.message.lower():
                root_causes.append(RootCause(
                    cause="Upstream dependency timeout causing cascading failures",
                    confidence=0.70,
                    evidence=[
                        f"Log: {log.message} (count={log.count})",
                        "Timeout errors suggest dependency unavailability",
                    ],
                ))

        # Analyze metrics for clues
        for m in perception.metrics:
            if m.metric == "connection_pool_usage" and m.value > 0.9:
                root_causes.append(RootCause(
                    cause="Connection pool near exhaustion blocking new requests",
                    confidence=0.90,
                    evidence=[
                        f"Metric: {m.metric}={m.value} on {m.service}",
                        "Pool usage >90% indicates imminent exhaustion",
                    ],
                ))
            if m.metric == "request_latency_p99" and m.value > 1000:
                root_causes.append(RootCause(
                    cause="High request latency indicating resource bottleneck",
                    confidence=0.80,
                    evidence=[
                        f"Metric: {m.metric}={m.value}{m.unit} on {m.service}",
                        "P99 latency >1s indicates severe degradation",
                    ],
                ))

        # Cross-validate with historical cases
        for rc in root_causes:
            for case in similar_cases:
                if self._cause_matches_case(rc.cause, case):
                    rc.confidence = min(rc.confidence + 0.05, 1.0)
                    rc.evidence.append(f"Similar past case: {case['case_id']} - {case['title']}")

        # Deduplicate and sort by confidence
        seen: set[str] = set()
        unique: list[RootCause] = []
        for rc in root_causes:
            short = rc.cause[:40]
            if short not in seen:
                seen.add(short)
                unique.append(rc)
        unique.sort(key=lambda x: x.confidence, reverse=True)

        return unique[:3]  # Top 3 candidates

    def _cause_matches_case(self, cause: str, case: dict) -> bool:
        """Check if a root cause description matches a historical case."""
        cause_lower = cause.lower()
        case_text = f"{case['title']} {case['root_cause']} {' '.join(case['symptoms'])}".lower()
        cause_words = set(cause_lower.split())
        case_words = set(case_text.split())
        overlap = len(cause_words & case_words)
        return overlap >= 2

    def _summarize_trace(
        self, root_causes: list[RootCause], similar_cases: list[dict],
    ) -> str:
        """Generate a brief reasoning trace summary."""
        if not root_causes:
            return "No root causes identified"
        top = root_causes[0]
        case_refs = ", ".join(c["case_id"] for c in similar_cases) if similar_cases else "none"
        return f"Top cause: {top.cause} (conf={top.confidence:.2f}), similar cases: {case_refs}"

    def _format_logs(self, logs: list) -> str:
        return "\n".join(f"- {l.service} {l.level} \"{l.message}\" (count={l.count})" for l in logs)

    def _format_metrics(self, metrics: list) -> str:
        return "\n".join(f"- {m.service} {m.metric}={m.value}{m.unit}" for m in metrics)

    def _format_alerts(self, alerts: list) -> str:
        return "\n".join(f"- {a.alert_name} {a.severity} since {a.start_time}" for a in alerts)