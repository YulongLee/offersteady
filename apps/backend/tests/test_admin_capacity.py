from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.admin_capacity import AdminCapacityMonitor, RequestWindow, capacity_level, percentile


def test_capacity_helpers_use_nearest_rank_and_thresholds() -> None:
    assert percentile([10, 20, 30, 40, 50], 0.95) == 50
    assert capacity_level(None, 10, 20) == "unavailable"
    assert capacity_level(9, 10, 20) == "healthy"
    assert capacity_level(10, 10, 20) == "warning"
    assert capacity_level(20, 10, 20) == "critical"


def test_request_window_excludes_health_and_capacity_self_polling() -> None:
    window = RequestWindow()
    window.record(path="/healthz", elapsed_ms=999, status_code=500)
    window.record(path="/api/v1/admin/capacity", elapsed_ms=999, status_code=500)
    window.record(path="/api/v1/admin/server-health", elapsed_ms=999, status_code=500)
    window.record(path="/api/v1/interviews", elapsed_ms=100, status_code=200)
    window.record(path="/api/v1/interviews", elapsed_ms=300, status_code=500)
    summary = window.summary()
    assert summary["apiP95Ms"] == 300
    assert summary["apiErrorRate"] == 50


def test_request_window_classifies_control_recovery_and_sse_without_payloads() -> None:
    window = RequestWindow()
    window.record(path="/api/v1/interviews", elapsed_ms=80, status_code=200)
    window.record(path="/api/v1/realtime-speech/sessions/synthetic/snapshot", elapsed_ms=240, status_code=200)
    window.record(path="/api/v1/realtime-speech/sessions/synthetic/stream", elapsed_ms=3_500, status_code=200)
    window.record(path="/api/v1/screenshot-answer/desktop-devices/synthetic/capture-requests/stream", elapsed_ms=9_000, status_code=200)
    summary = window.summary()

    assert summary["apiP95Ms"] == 240
    assert summary["controlApiP95Ms"] == 80
    assert summary["recoverySnapshotP95Ms"] == 240
    assert summary["sseStreamDurationP95Ms"] == 9_000
    assert summary["sseStreamDurationRequestCount"] == 2
    assert summary["sseHandshakeP95Ms"] == 9_000
    assert summary["controlApiRequestCount"] == 1
    assert summary["recoverySnapshotRequestCount"] == 1
    assert summary["sseHandshakeRequestCount"] == 2
    assert "synthetic" not in str(summary)


def test_admin_requests_do_not_inflate_user_api_p95() -> None:
    window = RequestWindow()
    window.record(path="/api/v1/admin/dashboard", elapsed_ms=900, status_code=200)
    window.record(path="/api/v1/web/state", elapsed_ms=20, status_code=200)
    summary = window.summary()
    assert summary["userApiP95Ms"] == 20
    assert summary["telemetryP95Ms"] == 900


def test_request_window_breakdown_normalizes_ids_and_separates_telemetry() -> None:
    window = RequestWindow()
    window.record(path="/api/v1/realtime-speech/sessions/session-abc123/performance-ack?userId=private", elapsed_ms=600, status_code=200)
    window.record(path="/api/v1/realtime-speech/sessions/session-def456/performance-ack", elapsed_ms=500, status_code=500)
    window.record(path="/api/v1/interviews/550e8400-e29b-41d4-a716-446655440000", elapsed_ms=40, status_code=200)
    window.record(path="/api/v1/realtime-speech/sessions/session-abc123/snapshot", elapsed_ms=150, status_code=200)

    summary = window.summary()
    classes = summary["requestBreakdown"]["classes"]
    assert classes["telemetry"]["requestCount"] == 2
    assert classes["telemetry"]["errorCount"] == 1
    assert summary["userApiP95Ms"] == 40
    assert summary["telemetryP95Ms"] == 600
    slow_routes = summary["requestBreakdown"]["slowRoutes"]
    assert slow_routes[0]["route"] == "/api/v1/realtime-speech/sessions/{id}/performance-ack"
    assert "session-abc123" not in str(summary)
    assert "private" not in str(summary)


def test_request_window_breakdown_is_bounded_and_empty_safe() -> None:
    window = RequestWindow()
    empty = window.summary()["requestBreakdown"]
    assert empty["slowRoutes"] == []
    assert empty["classes"]["user_api"]["requestCount"] == 0
    for index in range(12):
        window.record(path=f"/api/v1/interviews/{index}", elapsed_ms=float(index + 1), status_code=200)
    assert len(window.summary()["requestBreakdown"]["slowRoutes"]) <= 8


class HealthRepository:
    def capacity_counts(self):
        return {"activeInterviews": 2, "activeUsers": 2, "databaseConnections": 3, "databaseConnectionLimit": 100}

    def analytics_health(self, *, expected_since_ms: int):
        assert expected_since_ms > 0
        return {"lastSuccessAtMs": 9_999_999_999_999}

    def payment_configuration_health(self):
        return {"configuredChannels": 2, "readyChannels": 1, "enabledChannels": 1}

    def record_capacity_peak(self, **values):
        del values


def test_server_health_reports_resources_and_isolates_missing_redis(monkeypatch) -> None:
    monitor = AdminCapacityMonitor(Settings(redis_url=None), HealthRepository())
    monkeypatch.setattr(monitor, "_resource_counts", lambda: {
        "cpuPercent": 12.0, "memoryPercent": 34.0, "diskPercent": 45.0,
        "hostMemoryPercent": 40.0,
        "loadAverage1m": 0.5, "uptimeSeconds": 86_400.0,
    })
    report = monitor.server_report()
    assert report["overall"] == "warning"
    assert {item["key"] for item in report["resources"]} == {"cpuPercent", "memoryPercent", "hostMemoryPercent", "diskPercent", "loadAverage1m", "uptimeSeconds"}
    dependencies = {item["key"]: item for item in report["dependencies"]}
    assert dependencies["backend"]["status"] == "healthy"
    assert dependencies["postgresql"]["status"] == "healthy"
    assert dependencies["redis"]["status"] == "unavailable"
    assert dependencies["analytics"]["status"] == "healthy"
    assert dependencies["payment_config"]["status"] == "healthy"
    assert "requestBreakdown" in report["supporting"]
    assert monitor.server_report() is report


def test_server_health_keeps_partial_results_when_database_probe_fails(monkeypatch) -> None:
    class BrokenRepository(HealthRepository):
        def capacity_counts(self):
            raise TimeoutError("synthetic timeout")

    monitor = AdminCapacityMonitor(Settings(redis_url=None), BrokenRepository())
    monkeypatch.setattr(monitor, "_resource_counts", lambda: {
        "cpuPercent": None, "memoryPercent": 96.0, "diskPercent": 20.0,
        "hostMemoryPercent": 96.0,
        "loadAverage1m": None, "uptimeSeconds": None,
    })
    report = monitor.server_report()
    assert report["overall"] == "critical"
    assert next(item for item in report["dependencies"] if item["key"] == "postgresql")["status"] == "unavailable"
    assert next(item for item in report["resources"] if item["key"] == "memoryPercent")["level"] == "critical"


def test_memory_collector_separates_rss_from_host_total_without_cgroup_limit(monkeypatch) -> None:
    def read_text(path: Path, *args, **kwargs):
        del args, kwargs
        if str(path).endswith("memory.current"):
            return "1024"
        if str(path).endswith("memory.max"):
            return "max"
        if str(path) == "/proc/self/status":
            return "Name:\tpython\nVmRSS:\t2000 kB\n"
        if str(path) == "/proc/meminfo":
            return "MemTotal: 100000 kB\nMemAvailable: 60000 kB\n"
        raise OSError("unsupported synthetic path")

    monkeypatch.setattr(Path, "read_text", read_text)
    stats = AdminCapacityMonitor._memory_stats()
    assert stats["containerBytes"] == 1024
    assert stats["containerPercent"] == 2.0
    assert stats["hostPercent"] == 40.0
    assert stats["containerSource"] == "rss-host-total"


def test_capacity_report_serializes_memory_sources_in_supporting_fields(monkeypatch) -> None:
    monitor = AdminCapacityMonitor(Settings(redis_url=None), HealthRepository())
    sample = {
        "atMs": 1,
        "containerMemoryBytes": 4096,
        "containerMemoryLimitBytes": 8192,
        "containerMemorySource": "cgroup",
        "memoryPercent": 50.0,
        "hostMemoryPercent": 37.5,
    }
    monkeypatch.setattr(monitor, "_load_samples", lambda: [sample])

    supporting = monitor.report()["supporting"]
    assert supporting["containerMemory"] == {
        "bytes": 4096,
        "limitBytes": 8192,
        "source": "cgroup",
    }
    assert supporting["hostMemoryPercent"] == 37.5


def test_capacity_peak_failure_is_degraded_and_never_breaks_sampling(monkeypatch, caplog) -> None:
    class BrokenPeakRepository(HealthRepository):
        def record_capacity_peak(self, **values):
            del values
            raise RuntimeError("synthetic constraint rejection")

    monitor = AdminCapacityMonitor(Settings(redis_url=None), BrokenPeakRepository())
    monkeypatch.setattr(monitor, "_resource_counts", lambda: {})
    first = monitor.sample()
    second = monitor.sample()

    assert first["capacityPeakPersistence"] == "degraded"
    assert second["capacityPeakPersistence"] == "degraded"
    assert [record.message for record in caplog.records].count("admin_capacity_peak_persistence_failed") == 1


def test_capacity_granularity_migration_is_wired_and_idempotent() -> None:
    migration = Path("apps/backend/migrations/versions/0031_capacity_metric_granularity.sql").read_text(encoding="utf8")
    repository_source = Path("apps/backend/app/services/admin_repository.py").read_text(encoding="utf8")

    assert "capacity_5m" in migration
    assert "'hourly'" in migration
    assert "'daily'" in migration
    assert "DROP CONSTRAINT IF EXISTS admin_metric_snapshots_granularity_check" in migration
    assert "NOT VALID" in migration
    assert "VALIDATE CONSTRAINT" in migration
    assert "0031_capacity_metric_granularity.sql" in repository_source
