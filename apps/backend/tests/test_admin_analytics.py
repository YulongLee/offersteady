from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.admin_analytics import (
    AdminAnalyticsService,
    METRICS,
    day_bounds,
    local_day_from_ms,
    range_dates,
    summarize,
)
from app.services.admin_repository import AdminRepository


class AnalyticsRepositoryStub:
    def __init__(self) -> None:
        self.snapshots: dict[tuple[int, str, str], dict[str, object]] = {}
        self.runs: list[dict[str, object]] = []

    def compute_and_upsert_metric(self, *, definition, bucket_start_ms, bucket_end_ms, granularity, coverage_state):
        self.snapshots[(bucket_start_ms, granularity, definition.key)] = {
            "bucket_start_ms": bucket_start_ms,
            "metric_key": definition.key,
            "metric_value": None if definition.sql is None else 1.0,
            "sample_count": 0 if definition.sql is None else 1,
            "coverage_state": coverage_state,
            "definition_version": definition.version,
        }
        return True

    def create_analytics_run(self, values):
        self.runs.append({**values, "status": "running"})

    def finish_analytics_run(self, *, run_id, status, bucket_count, metric_count, safe_error_code):
        self.runs[-1].update(status=status, bucket_count=bucket_count, metric_count=metric_count, safe_error_code=safe_error_code)

    def list_analytics_snapshots(self, *, start_ms, end_ms, metric_keys, granularity):
        return [
            value for (bucket, grain, key), value in self.snapshots.items()
            if start_ms <= bucket < end_ms and grain == granularity and key in metric_keys
        ]

    def analytics_health(self, *, expected_since_ms):
        return {"lastSuccessAtMs": 1, "coveredDays": 1, "latestRun": self.runs[-1] if self.runs else None}

    def analytics_earliest_business_ms(self):
        return day_bounds(date(2026, 7, 1))[0]

    def cleanup_hourly_analytics(self, *, before_ms):
        matching = [key for key in self.snapshots if key[1] == "hourly" and key[0] < before_ms]
        for key in matching:
            del self.snapshots[key]
        return len(matching)


def test_shanghai_day_bounds_are_stable_and_reversible() -> None:
    start, end = day_bounds(date(2026, 7, 31))
    assert end - start == 86_400_000
    assert local_day_from_ms(start) == date(2026, 7, 31)
    assert datetime.fromtimestamp(start / 1000, timezone.utc).hour == 16


def test_supported_ranges_include_equal_previous_window() -> None:
    previous, start, end = range_dates("30d", today=date(2026, 7, 31))
    assert (end - start).days == 29
    assert (start - previous).days == 30


def test_daily_aggregation_is_idempotent_and_computes_runtime_metrics() -> None:
    repository = AnalyticsRepositoryStub()
    service = AdminAnalyticsService(repository)
    service.aggregate_days(start=date(2026, 7, 1), end=date(2026, 7, 1))
    first_count = len(repository.snapshots)
    service.aggregate_days(start=date(2026, 7, 1), end=date(2026, 7, 1))
    assert len(repository.snapshots) == first_count == len(METRICS)
    asr = next(value for (_, _, key), value in repository.snapshots.items() if key == "asr_final_latency_ms")
    assert asr["coverage_state"] == "complete"
    assert asr["metric_value"] == 1.0


def test_ai_metrics_use_persisted_runtime_fields_and_canonical_success_status() -> None:
    assert "first_token_ms" in (METRICS["answer_first_token_ms"].sql or "")
    assert "final_latency_ms" in (METRICS["asr_final_latency_ms"].sql or "")
    assert "status <> 'succeeded'" in (METRICS["ai_error_rate"].sql or "")
    assert "operation_kind = 'chat'" in (METRICS["answer_requests"].sql or "")


def test_trends_align_missing_dates_and_calculate_period_summary() -> None:
    repository = AnalyticsRepositoryStub()
    service = AdminAnalyticsService(repository)
    service.aggregate_days(start=date(2026, 7, 1), end=date(2026, 7, 2))
    response = service.trends(range_key="7d", metric_keys=["new_users"], today=date(2026, 7, 7))
    metric = response["metrics"][0]
    assert len(metric["points"]) == 7
    assert metric["points"][0]["value"] == 1.0
    assert metric["points"][-1]["value"] is None
    assert "user_id" not in str(response)


def test_weighted_summary_uses_sample_count() -> None:
    definition = METRICS["ai_avg_duration_ms"]
    value = summarize(definition, [
        {"metric_value": 100.0, "sample_count": 1},
        {"metric_value": 300.0, "sample_count": 3},
    ])
    assert value == 250.0


def test_peak_concurrency_uses_maximum_and_is_not_backfilled() -> None:
    definition = METRICS["peak_concurrent_interviews"]
    assert definition.backfillable is False
    assert summarize(definition, [
        {"metric_value": 2.0, "sample_count": 10},
        {"metric_value": 7.0, "sample_count": 1},
        {"metric_value": 4.0, "sample_count": 20},
    ]) == 7.0


def test_repository_analytics_upsert_uses_lock_and_conflict_update() -> None:
    constants = " ".join(
        item for item in AdminRepository.compute_and_upsert_metric.__code__.co_consts
        if isinstance(item, str)
    )
    assert "pg_try_advisory_xact_lock" in constants
    assert "ON CONFLICT" in constants
    assert "unavailable" in constants


def test_capacity_peak_upsert_never_reduces_saved_maximum() -> None:
    constants = " ".join(
        item for item in AdminRepository.record_capacity_peak.__code__.co_consts
        if isinstance(item, str)
    )
    assert "capacity_5m" in constants
    assert "GREATEST" in constants


def test_trend_endpoint_is_hidden_without_commercial_admin_access() -> None:
    get_settings.cache_clear()
    response = TestClient(create_app()).get("/api/v1/admin/analytics/trends?range=30d")
    assert response.status_code == 404


def test_trends_reject_unknown_or_unbounded_metrics() -> None:
    service = AdminAnalyticsService(AnalyticsRepositoryStub())
    try:
        service.trends(range_key="30d", metric_keys=["unknown"])
    except ValueError as exc:
        assert str(exc) == "analytics_metrics_invalid"
    else:
        raise AssertionError("unknown analytics metric must be rejected")
