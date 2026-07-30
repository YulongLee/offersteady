from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.services.admin_repository import now_ms


SHANGHAI = ZoneInfo("Asia/Shanghai")
RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90}
MAX_METRICS_PER_QUERY = 12


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    unit: str
    group: str
    aggregation: str
    description: str
    sql: str | None
    backfillable: bool = True
    version: int = 1


BOUNDS = "WITH bounds AS (SELECT %s::BIGINT AS start_ms, %s::BIGINT AS end_ms)"
METRICS: dict[str, MetricDefinition] = {
    "new_users": MetricDefinition("new_users", "新增用户", "人", "growth", "sum", "自然日内首次注册的用户数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM auth_users, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "active_users": MetricDefinition("active_users", "活跃用户", "人", "growth", "sum", "自然日内登录、进入面试或调用 AI 的去重用户数。", f"""{BOUNDS}
        SELECT COUNT(DISTINCT user_id)::DOUBLE PRECISION AS value, COUNT(DISTINCT user_id)::BIGINT AS sample_count
        FROM (
          SELECT user_id FROM auth_users, bounds WHERE last_login_at_ms >= start_ms AND last_login_at_ms < end_ms
          UNION SELECT owner_user_id FROM interview_sessions, bounds WHERE last_activity_at_ms >= start_ms AND last_activity_at_ms < end_ms
          UNION SELECT owner_user_id FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms
        ) activity"""),
    "interviews_created": MetricDefinition("interviews_created", "创建面试", "场", "interview", "sum", "自然日内创建且未软删除的面试数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM interview_sessions, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms AND deleted_at_ms IS NULL"),
    "interviews_completed": MetricDefinition("interviews_completed", "完成面试", "场", "interview", "sum", "自然日内正常或自动结束的面试数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM interview_sessions, bounds WHERE ended_at_ms >= start_ms AND ended_at_ms < end_ms AND deleted_at_ms IS NULL"),
    "answer_requests": MetricDefinition("answer_requests", "回答请求", "次", "interview", "sum", "面试场景中的文本回答模型调用数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms AND session_id IS NOT NULL AND operation_kind NOT IN ('vision', 'screenshot-answer')"),
    "screenshot_answers": MetricDefinition("screenshot_answers", "截图回答", "次", "interview", "sum", "截图或视觉回答模型调用数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms AND operation_kind IN ('vision', 'screenshot-answer')"),
    "points_consumed": MetricDefinition("points_consumed", "积分消耗", "点", "commercial", "sum", "自然日内积分账本负向流水的绝对值。", f"{BOUNDS} SELECT COALESCE(SUM(-points) FILTER (WHERE points < 0), 0)::DOUBLE PRECISION AS value, COUNT(*) FILTER (WHERE points < 0)::BIGINT AS sample_count FROM points_redemption_ledger, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "orders_created": MetricDefinition("orders_created", "创建订单", "单", "commercial", "sum", "自然日内创建的支付订单数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM billing_checkout_orders, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "orders_paid": MetricDefinition("orders_paid", "支付成功", "单", "commercial", "sum", "自然日内渠道确认支付成功的订单数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM billing_checkout_orders, bounds WHERE paid_at_ms >= start_ms AND paid_at_ms < end_ms AND status = 'paid'"),
    "paid_revenue_cents": MetricDefinition("paid_revenue_cents", "实收金额", "分", "commercial", "sum", "自然日内支付成功订单金额。", f"{BOUNDS} SELECT COALESCE(SUM(amount_cents), 0)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM billing_checkout_orders, bounds WHERE paid_at_ms >= start_ms AND paid_at_ms < end_ms AND status = 'paid'"),
    "payment_success_rate": MetricDefinition("payment_success_rate", "支付成功率", "%", "commercial", "weighted_average", "按创建订单统计的支付成功比例。", f"{BOUNDS} SELECT CASE WHEN COUNT(*) = 0 THEN NULL ELSE COUNT(*) FILTER (WHERE status = 'paid') * 100.0 / COUNT(*) END::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM billing_checkout_orders, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "materials_uploaded": MetricDefinition("materials_uploaded", "上传资料", "份", "material", "sum", "自然日内上传且未软删除的资料数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM material_documents, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms AND deleted_at_ms IS NULL"),
    "materials_ready": MetricDefinition("materials_ready", "资料可用", "份", "material", "sum", "自然日内完成处理并可使用的资料数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM processing_tasks, bounds WHERE completed_at_ms >= start_ms AND completed_at_ms < end_ms AND current_stage = 'COMPLETED'"),
    "material_success_rate": MetricDefinition("material_success_rate", "资料成功率", "%", "material", "weighted_average", "自然日内已结束资料任务的成功比例。", f"{BOUNDS} SELECT CASE WHEN COUNT(*) = 0 THEN NULL ELSE COUNT(*) FILTER (WHERE current_stage = 'COMPLETED') * 100.0 / COUNT(*) END::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM processing_tasks, bounds WHERE updated_at_ms >= start_ms AND updated_at_ms < end_ms AND current_stage IN ('COMPLETED', 'FAILED', 'QUARANTINED')"),
    "ai_requests": MetricDefinition("ai_requests", "AI 调用", "次", "quality", "sum", "自然日内所有模型调用次数。", f"{BOUNDS} SELECT COUNT(*)::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "ai_error_rate": MetricDefinition("ai_error_rate", "AI 异常率", "%", "quality", "weighted_average", "模型调用中非成功状态的比例。", f"{BOUNDS} SELECT CASE WHEN COUNT(*) = 0 THEN NULL ELSE COUNT(*) FILTER (WHERE status <> 'success') * 100.0 / COUNT(*) END::DOUBLE PRECISION AS value, COUNT(*)::BIGINT AS sample_count FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "ai_avg_duration_ms": MetricDefinition("ai_avg_duration_ms", "AI 平均耗时", "ms", "quality", "weighted_average", "具有耗时记录的模型调用平均耗时。", f"{BOUNDS} SELECT AVG(duration_ms)::DOUBLE PRECISION AS value, COUNT(duration_ms)::BIGINT AS sample_count FROM ai_usage_records, bounds WHERE created_at_ms >= start_ms AND created_at_ms < end_ms"),
    "answer_first_token_ms": MetricDefinition("answer_first_token_ms", "回答首字延迟", "ms", "quality", "weighted_average", "从完整性能事件上线后开始覆盖的回答首字延迟。", None, backfillable=False),
    "asr_final_latency_ms": MetricDefinition("asr_final_latency_ms", "ASR 最终延迟", "ms", "quality", "weighted_average", "从能力上线后开始覆盖的实时转写最终延迟。", None, backfillable=False),
    "realtime_errors": MetricDefinition("realtime_errors", "实时链路异常", "次", "quality", "sum", "从聚合能力上线后开始覆盖的实时发布与转写异常数。", None, backfillable=False),
}


class AnalyticsRepository(Protocol):
    def compute_and_upsert_metric(self, *, definition: MetricDefinition, bucket_start_ms: int, bucket_end_ms: int, granularity: str, coverage_state: str) -> bool: ...
    def create_analytics_run(self, values: dict[str, Any]) -> None: ...
    def finish_analytics_run(self, *, run_id: str, status: str, bucket_count: int, metric_count: int, safe_error_code: str | None) -> None: ...
    def list_analytics_snapshots(self, *, start_ms: int, end_ms: int, metric_keys: list[str], granularity: str) -> list[dict[str, Any]]: ...
    def analytics_health(self, *, expected_since_ms: int) -> dict[str, Any]: ...
    def analytics_earliest_business_ms(self) -> int | None: ...
    def cleanup_hourly_analytics(self, *, before_ms: int) -> int: ...


def day_bounds(day: date) -> tuple[int, int]:
    start = datetime.combine(day, datetime_time.min, tzinfo=SHANGHAI)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def local_day_from_ms(value: int) -> date:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone(SHANGHAI).date()


def range_dates(range_key: str, *, today: date | None = None) -> tuple[date, date, date]:
    if range_key not in RANGE_DAYS:
        raise ValueError("unsupported_analytics_range")
    end = today or datetime.now(SHANGHAI).date()
    days = RANGE_DAYS[range_key]
    start = end - timedelta(days=days - 1)
    previous_start = start - timedelta(days=days)
    return previous_start, start, end


def summarize(definition: MetricDefinition, rows: list[dict[str, Any]]) -> float | None:
    values = [(float(row["metric_value"]), int(row["sample_count"])) for row in rows if row.get("metric_value") is not None]
    if not values:
        return None
    if definition.aggregation == "sum":
        return sum(value for value, _ in values)
    weighted = sum(value * count for value, count in values)
    samples = sum(count for _, count in values)
    return weighted / samples if samples else None


class AdminAnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def aggregate_days(self, *, start: date, end: date, run_kind: str = "manual") -> dict[str, Any]:
        if end < start or (end - start).days > 3660:
            raise ValueError("analytics_backfill_range_invalid")
        range_start_ms, _ = day_bounds(start)
        _, range_end_ms = day_bounds(end)
        run_id = f"analytics-run-{uuid4().hex}"
        self.repository.create_analytics_run({
            "run_id": run_id, "run_kind": run_kind, "granularity": "daily",
            "range_started_at_ms": range_start_ms, "range_ended_at_ms": range_end_ms,
            "started_at_ms": now_ms(),
        })
        buckets = 0
        metrics = 0
        try:
            current = start
            while current <= end:
                bucket_start, bucket_end = day_bounds(current)
                for definition in METRICS.values():
                    coverage = "complete" if definition.sql is not None else "unavailable"
                    if self.repository.compute_and_upsert_metric(
                        definition=definition,
                        bucket_start_ms=bucket_start,
                        bucket_end_ms=bucket_end,
                        granularity="daily",
                        coverage_state=coverage,
                    ):
                        metrics += 1
                buckets += 1
                current += timedelta(days=1)
            self.repository.finish_analytics_run(
                run_id=run_id, status="completed", bucket_count=buckets,
                metric_count=metrics, safe_error_code=None,
            )
            return {"runId": run_id, "status": "completed", "bucketCount": buckets, "metricCount": metrics}
        except Exception as exc:
            self.repository.finish_analytics_run(
                run_id=run_id, status="failed", bucket_count=buckets,
                metric_count=metrics, safe_error_code=exc.__class__.__name__,
            )
            raise

    def aggregate_hour(self, *, moment: datetime | None = None) -> dict[str, Any]:
        current = (moment or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start_ms = int(current.timestamp() * 1000)
        end_ms = int((current + timedelta(hours=1)).timestamp() * 1000)
        run_id = f"analytics-run-{uuid4().hex}"
        self.repository.create_analytics_run({
            "run_id": run_id, "run_kind": "scheduled", "granularity": "hourly",
            "range_started_at_ms": start_ms, "range_ended_at_ms": end_ms,
            "started_at_ms": now_ms(),
        })
        metric_count = 0
        try:
            for definition in METRICS.values():
                if self.repository.compute_and_upsert_metric(
                    definition=definition, bucket_start_ms=start_ms, bucket_end_ms=end_ms,
                    granularity="hourly", coverage_state="complete" if definition.sql else "unavailable",
                ):
                    metric_count += 1
            self.repository.finish_analytics_run(
                run_id=run_id, status="completed", bucket_count=1,
                metric_count=metric_count, safe_error_code=None,
            )
            return {"runId": run_id, "status": "completed", "bucketCount": 1, "metricCount": metric_count}
        except Exception as exc:
            self.repository.finish_analytics_run(
                run_id=run_id, status="failed", bucket_count=0,
                metric_count=metric_count, safe_error_code=exc.__class__.__name__,
            )
            raise

    def run_scheduled(self) -> dict[str, Any]:
        hourly = self.aggregate_hour()
        yesterday = datetime.now(SHANGHAI).date() - timedelta(days=1)
        daily = self.aggregate_days(
            start=yesterday - timedelta(days=6),
            end=yesterday,
            run_kind="scheduled",
        )
        removed = self.repository.cleanup_hourly_analytics(
            before_ms=now_ms() - 180 * 86_400_000
        )
        return {"hourly": hourly, "daily": daily, "expiredHourlyRows": removed}

    def backfill_all(self) -> dict[str, Any]:
        earliest = self.repository.analytics_earliest_business_ms()
        today = datetime.now(SHANGHAI).date()
        start = local_day_from_ms(earliest) if earliest is not None else today
        return self.aggregate_days(start=start, end=today, run_kind="backfill")

    def trends(self, *, range_key: str, metric_keys: list[str] | None = None, today: date | None = None) -> dict[str, Any]:
        previous_start, start, end = range_dates(range_key, today=today)
        selected = metric_keys or ["new_users", "interviews_created", "paid_revenue_cents", "material_success_rate", "ai_avg_duration_ms"]
        if len(selected) > MAX_METRICS_PER_QUERY or not selected or any(key not in METRICS for key in selected):
            raise ValueError("analytics_metrics_invalid")
        query_start_ms, _ = day_bounds(previous_start)
        _, query_end_ms = day_bounds(end)
        rows = self.repository.list_analytics_snapshots(
            start_ms=query_start_ms, end_ms=query_end_ms,
            metric_keys=selected, granularity="daily",
        )
        by_metric: dict[str, list[dict[str, Any]]] = {key: [] for key in selected}
        for row in rows:
            by_metric[str(row["metric_key"])].append(row)
        current_start_ms, _ = day_bounds(start)
        metrics: list[dict[str, Any]] = []
        for key in selected:
            definition = METRICS[key]
            metric_rows = by_metric[key]
            current_rows = [row for row in metric_rows if int(row["bucket_start_ms"]) >= current_start_ms]
            previous_rows = [row for row in metric_rows if int(row["bucket_start_ms"]) < current_start_ms]
            current_value = summarize(definition, current_rows)
            previous_value = summarize(definition, previous_rows)
            change_percent = None
            if current_value is not None and previous_value not in {None, 0}:
                change_percent = (current_value - float(previous_value)) * 100 / abs(float(previous_value))
            points_by_day = {
                local_day_from_ms(int(row["bucket_start_ms"])).isoformat(): row
                for row in current_rows
            }
            points = []
            cursor = start
            while cursor <= end:
                row = points_by_day.get(cursor.isoformat())
                points.append({
                    "date": cursor.isoformat(),
                    "value": None if row is None else row["metric_value"],
                    "coverage": "unavailable" if row is None else row["coverage_state"],
                })
                cursor += timedelta(days=1)
            metrics.append({
                "key": key, "label": definition.label, "unit": definition.unit,
                "group": definition.group, "aggregation": definition.aggregation,
                "description": definition.description, "definitionVersion": definition.version,
                "backfillable": definition.backfillable,
                "summary": {"current": current_value, "previous": previous_value, "changePercent": change_percent},
                "points": points,
            })
        health = self._health_with_pending(
            self.repository.analytics_health(expected_since_ms=current_start_ms),
            expected_days=RANGE_DAYS[range_key],
        )
        return {
            "range": range_key, "timezone": "Asia/Shanghai",
            "startedOn": start.isoformat(), "endedOn": end.isoformat(),
            "generatedAtMs": now_ms(), "metrics": metrics, "health": health,
        }

    def health(self) -> dict[str, Any]:
        since, _ = day_bounds(datetime.now(SHANGHAI).date() - timedelta(days=30))
        return self._health_with_pending(
            self.repository.analytics_health(expected_since_ms=since),
            expected_days=31,
        )

    @staticmethod
    def _health_with_pending(health: dict[str, Any], *, expected_days: int) -> dict[str, Any]:
        return {
            **health,
            "pendingDays": max(0, expected_days - int(health.get("coveredDays") or 0)),
        }
