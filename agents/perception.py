"""Perception Agent: fetches and aggregates monitoring data."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter

from models import LogEntry, MetricEntry, AlertEntry, PerceptionInput, PerceptionOutput
from utils.mock_data import LOG_MESSAGES, METRICS_DATA, ALERTS_DATA

logger = logging.getLogger("fault_agent")


class PerceptionAgent:
    """Fetches logs, metrics, and alerts for the fault time window,
    then deduplicates and aggregates the data."""

    async def run(self, input: PerceptionInput) -> PerceptionOutput:
        """Run perception with concurrent data fetching."""
        start = time.monotonic()

        # Concurrent fetch of logs, metrics, alerts
        logs_task = self._fetch_logs(input.service_names)
        metrics_task = self._fetch_metrics(input.service_names)
        alerts_task = self._fetch_alerts(input.service_names)

        raw_logs, raw_metrics, raw_alerts = await asyncio.gather(
            logs_task, metrics_task, alerts_task,
        )

        # Deduplicate logs: merge same message within 1-min window
        deduped_logs = self._deduplicate_logs(raw_logs)

        elapsed = time.monotonic() - start
        logger.info(f"PerceptionAgent completed in {elapsed:.2f}s, "
                    f"logs={len(deduped_logs)}, metrics={len(raw_metrics)}, "
                    f"alerts={len(raw_alerts)}")

        return PerceptionOutput(
            logs=deduped_logs,
            metrics=raw_metrics,
            alerts=raw_alerts,
        )

    async def _fetch_logs(self, services: list[str]) -> list[LogEntry]:
        """Fetch error logs for given services. # TODO: 替换为生产 API"""
        entries: list[LogEntry] = []
        for svc in services:
            msgs = LOG_MESSAGES.get(svc, [])
            for msg, level in msgs:
                # Simulate multiple occurrences
                count = 3 if level == "ERROR" else 1
                entries.append(LogEntry(service=svc, level=level, message=msg, count=count))
        return entries

    async def _fetch_metrics(self, services: list[str]) -> list[MetricEntry]:
        """Fetch metrics for given services. # TODO: 替换为生产 API"""
        entries: list[MetricEntry] = []
        for svc in services:
            for m in METRICS_DATA.get(svc, []):
                entries.append(MetricEntry(
                    metric=m["metric"], value=m["value"],
                    unit=m["unit"], service=svc,
                ))
        return entries

    async def _fetch_alerts(self, services: list[str]) -> list[AlertEntry]:
        """Fetch alerts for given services. # TODO: 替换为生产 API"""
        entries: list[AlertEntry] = []
        for svc in services:
            for a in ALERTS_DATA.get(svc, []):
                entries.append(AlertEntry(
                    alert_name=a["alert_name"], severity=a["severity"],
                    start_time=a["start_time"],
                ))
        return entries

    def _deduplicate_logs(self, logs: list[LogEntry]) -> list[LogEntry]:
        """Merge logs with the same service+level+message, summing counts.
        Keep top 5 highest-frequency errors."""
        counter: Counter[str] = Counter()
        msg_map: dict[str, LogEntry] = {}

        for log in logs:
            key = f"{log.service}|{log.level}|{log.message}"
            counter[key] += log.count
            msg_map[key] = log

        deduped: list[LogEntry] = []
        for key, total in counter.most_common():
            original = msg_map[key]
            deduped.append(LogEntry(
                service=original.service,
                level=original.level,
                message=original.message,
                count=total,
            ))

        # Ensure at least top 5 errors
        errors = [d for d in deduped if d.level == "ERROR"]
        if len(errors) < 5 and len(deduped) >= 5:
            return deduped[:5]
        return deduped