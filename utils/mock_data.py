"""Mock data simulating monitoring, logs, and alerts."""

from __future__ import annotations

# Realistic error messages for mock data
LOG_MESSAGES = {
    "payment-api": [
        ("Connection reset by peer", "ERROR"),
        ("Deadlock found when trying to get lock", "ERROR"),
        ("Timeout waiting for response from order-db", "ERROR"),
        ("HTTP 503 Service Unavailable", "ERROR"),
        ("Thread pool exhausted, rejecting task", "ERROR"),
        ("Rate limit exceeded for upstream gateway", "WARN"),
        ("SSL handshake failed with payment-gateway", "ERROR"),
    ],
    "order-db": [
        ("Too many connections to database", "ERROR"),
        ("Lock wait timeout exceeded", "ERROR"),
        ("Out of memory for query buffer", "ERROR"),
        ("Replication lag exceeds threshold: 120s", "WARN"),
        ("Disk usage at 95% on /data partition", "WARN"),
        ("Slow query detected: SELECT * FROM orders", "WARN"),
    ],
}

METRICS_DATA = {
    "payment-api": [
        {"metric": "request_latency_p99", "value": 3200.0, "unit": "ms"},
        {"metric": "error_rate", "value": 0.15, "unit": "ratio"},
        {"metric": "active_threads", "value": 200.0, "unit": "count"},
        {"metric": "connection_pool_usage", "value": 0.98, "unit": "ratio"},
    ],
    "order-db": [
        {"metric": "query_latency_avg", "value": 850.0, "unit": "ms"},
        {"metric": "active_connections", "value": 150.0, "unit": "count"},
        {"metric": "replication_lag", "value": 120.0, "unit": "s"},
        {"metric": "disk_usage_ratio", "value": 0.95, "unit": "ratio"},
    ],
}

ALERTS_DATA = {
    "payment-api": [
        {"alert_name": "HighErrorRate", "severity": "P0", "start_time": "2025-04-01T09:58:00Z"},
        {"alert_name": "ThreadPoolExhausted", "severity": "P1", "start_time": "2025-04-01T09:55:00Z"},
        {"alert_name": "ConnectionPoolNearFull", "severity": "P1", "start_time": "2025-04-01T09:52:00Z"},
    ],
    "order-db": [
        {"alert_name": "TooManyDBConnections", "severity": "P0", "start_time": "2025-04-01T09:57:00Z"},
        {"alert_name": "ReplicationLagHigh", "severity": "P2", "start_time": "2025-04-01T09:50:00Z"},
        {"alert_name": "DiskUsageCritical", "severity": "P1", "start_time": "2025-04-01T09:45:00Z"},
    ],
}

# Historical fault cases for vector store mock
HISTORICAL_CASES = [
    {
        "case_id": "CASE-2024-001",
        "title": "Payment API connection pool leak causing thread exhaustion",
        "symptoms": ["connection_pool_usage > 0.9", "active_threads near limit", "request latency spike"],
        "root_cause": "Database connection leak in payment-api ORM layer",
        "resolution": "restart_connection_pool(payment-api)",
    },
    {
        "case_id": "CASE-2024-002",
        "title": "Order DB deadlock cascade from batch update",
        "symptoms": ["deadlock errors", "query latency increase", "replication lag"],
        "root_cause": "Batch order status update causing row-level deadlocks",
        "resolution": "rollback_last_deployment(order-db)",
    },
    {
        "case_id": "CASE-2024-003",
        "title": "Rate limit exhaustion under traffic surge",
        "symptoms": ["rate limit exceeded", "503 errors", "upstream gateway timeout"],
        "root_cause": "Flash sale traffic exceeded rate limit configuration",
        "resolution": "increase_rate_limit(payment-api, 2.0)",
    },
    {
        "case_id": "CASE-2024-004",
        "title": "Disk full causing DB query failures",
        "symptoms": ["disk usage > 90%", "out of memory", "slow queries"],
        "root_cause": "Log rotation failure filled /data partition on order-db",
        "resolution": "circuit_breaker_trip(order-db)",
    },
    {
        "case_id": "CASE-2024-005",
        "title": "SSL cert expiry breaking payment gateway",
        "symptoms": ["SSL handshake failed", "connection reset", "503 errors"],
        "root_cause": "Payment gateway SSL certificate expired",
        "resolution": "restart_connection_pool(payment-api)",
    },
]