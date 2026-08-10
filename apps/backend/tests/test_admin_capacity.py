from __future__ import annotations

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
        "loadAverage1m": 0.5, "uptimeSeconds": 86_400.0,
    })
    report = monitor.server_report()
    assert report["overall"] == "warning"
    assert {item["key"] for item in report["resources"]} == {"cpuPercent", "memoryPercent", "diskPercent", "loadAverage1m", "uptimeSeconds"}
    dependencies = {item["key"]: item for item in report["dependencies"]}
    assert dependencies["backend"]["status"] == "healthy"
    assert dependencies["postgresql"]["status"] == "healthy"
    assert dependencies["redis"]["status"] == "unavailable"
    assert dependencies["analytics"]["status"] == "healthy"
    assert dependencies["payment_config"]["status"] == "healthy"
    assert monitor.server_report() is report


def test_server_health_keeps_partial_results_when_database_probe_fails(monkeypatch) -> None:
    class BrokenRepository(HealthRepository):
        def capacity_counts(self):
            raise TimeoutError("synthetic timeout")

    monitor = AdminCapacityMonitor(Settings(redis_url=None), BrokenRepository())
    monkeypatch.setattr(monitor, "_resource_counts", lambda: {
        "cpuPercent": None, "memoryPercent": 96.0, "diskPercent": 20.0,
        "loadAverage1m": None, "uptimeSeconds": None,
    })
    report = monitor.server_report()
    assert report["overall"] == "critical"
    assert next(item for item in report["dependencies"] if item["key"] == "postgresql")["status"] == "unavailable"
    assert next(item for item in report["resources"] if item["key"] == "memoryPercent")["level"] == "critical"
