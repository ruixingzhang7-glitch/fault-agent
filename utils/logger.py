"""Structured logger with trace_id support."""

import logging
import sys
import uuid


def get_trace_id() -> str:
    return str(uuid.uuid4())[:8]


class TraceFormatter(logging.Formatter):
    def __init__(self, trace_id: str = ""):
        super().__init__()
        self.trace_id = trace_id

    def format(self, record: logging.LogRecord) -> str:
        trace = getattr(record, "trace_id", self.trace_id)
        ts = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        return f"[{ts}] [trace:{trace}] [{record.levelname}] {record.getMessage()}"


def setup_logger(trace_id: str = "") -> logging.Logger:
    logger = logging.getLogger("fault_agent")
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TraceFormatter(trace_id))
    logger.addHandler(handler)
    return logger