from __future__ import annotations

from app.services.admin_capacity import RequestWindow, capacity_level, percentile


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
    window.record(path="/api/v1/interviews", elapsed_ms=100, status_code=200)
    window.record(path="/api/v1/interviews", elapsed_ms=300, status_code=500)
    summary = window.summary()
    assert summary["apiP95Ms"] == 300
    assert summary["apiErrorRate"] == 50
