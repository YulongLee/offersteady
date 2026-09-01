from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import monotonic, sleep
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app.core.config import get_settings
from app.services.promotion_repository import ATTRIBUTION_MODELS, PromotionRepository, now_ms


ALLOWED_EVENT_KEYS = frozenset({
    "event_kind", "event_id", "event_type", "link_id", "visitor_hmac", "click_hmac", "occurred_at_ms",
    "destination_key", "referrer_host", "device_class", "qualification_state", "exclusion_reason",
    "conversion_type", "source_record_id", "user_id", "amount_cents", "currency",
    "claim_key",
})
FORBIDDEN_KEY_MARKERS = ("phone", "token", "password", "authorization", "transcript", "audio", "screenshot", "answer", "raw_ip", "user_agent")


def _stream_has_messages(response: object) -> bool:
    return bool(response) and any(bool(messages) for _, messages in response)  # type: ignore[union-attr]


def _json_metric_default(value: object) -> float:
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"unsupported promotion metric type: {type(value).__name__}")


def sanitize_event(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("invalid_promotion_event")
    keys = {str(key) for key in payload}
    if not keys.issubset(ALLOWED_EVENT_KEYS) or any(marker in key.lower() for key in keys for marker in FORBIDDEN_KEY_MARKERS):
        raise ValueError("promotion_event_contains_disallowed_fields")
    result = {key: payload[key] for key in keys}
    for key, value in result.items():
        if isinstance(value, str) and len(value) > 512:
            raise ValueError(f"promotion_event_field_too_large:{key}")
    return result


class PromotionAnalyticsJob:
    def __init__(self, repository: PromotionRepository) -> None:
        self.repository = repository
        self.settings = repository.settings

    def consume(self, *, limit: int = 500) -> dict[str, int]:
        if not self.settings.redis_url:
            return {"accepted": 0, "rejected": 0, "deferred": 0}
        import redis

        client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True, socket_timeout=2)
        group = "offersteady-promotion-analytics"
        consumer = "offersteady-promotion-worker"
        try:
            client.xgroup_create(self.settings.promotion_redis_stream, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        accepted = rejected = deferred = 0
        response = client.xreadgroup(group, consumer, {self.settings.promotion_redis_stream: "0"}, count=limit)
        if not _stream_has_messages(response):
            response = client.xreadgroup(group, consumer, {self.settings.promotion_redis_stream: ">"}, count=limit, block=50)
        for _, messages in response:
            for stream_id, fields in messages:
                should_ack = False
                try:
                    event = sanitize_event(json.loads(fields.get("payload", "{}")))
                    if event.get("event_kind") == "claim":
                        self.repository.claim_identity(
                            claim_key=str(event["claim_key"]),
                            visitor_hmac=str(event["visitor_hmac"]),
                            user_id=str(event["user_id"]),
                        )
                    elif event.get("event_kind") == "conversion":
                        self.repository.record_conversion(
                            event_id=str(event["event_id"]),
                            conversion_type=str(event["conversion_type"]),
                            source_record_id=str(event["source_record_id"]),
                            visitor_hmac=str(event["visitor_hmac"]) if event.get("visitor_hmac") else None,
                            user_id=str(event["user_id"]) if event.get("user_id") else None,
                            occurred_at_ms=int(event["occurred_at_ms"]),
                            amount_cents=int(event["amount_cents"]) if event.get("amount_cents") is not None else None,
                            currency=str(event["currency"]) if event.get("currency") else None,
                        )
                    else:
                        self.repository.record_touchpoint(event)
                    accepted += 1
                    should_ack = True
                except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                    rejected += 1
                    should_ack = True
                except Exception:
                    deferred += 1
                if should_ack:
                    client.xack(self.settings.promotion_redis_stream, group, stream_id)
        return {"accepted": accepted, "rejected": rejected, "deferred": deferred}

    def derive_authoritative_conversions(self, *, start_ms: int, end_ms: int) -> int:
        current = now_ms()
        with self.repository.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO promotion_conversion_events
                   (conversion_event_id,event_id,conversion_type,source_record_id,visitor_hmac,user_id,occurred_at_ms,created_at_ms)
                   SELECT 'promotion-conversion-' || md5('registration:' || u.user_id),
                          'authority-registration-' || u.user_id,'registration',u.user_id,b.visitor_hmac,u.user_id,u.created_at_ms,%s
                   FROM auth_users u LEFT JOIN promotion_identity_bindings b ON b.user_id=u.user_id AND b.deleted_at_ms IS NULL
                   WHERE u.created_at_ms >= %s AND u.created_at_ms < %s
                   ON CONFLICT (conversion_type,source_record_id) DO NOTHING""",
                (current, start_ms, end_ms),
            )
            inserted = cursor.rowcount
            cursor.execute(
                """INSERT INTO promotion_conversion_events
                   (conversion_event_id,event_id,conversion_type,source_record_id,visitor_hmac,user_id,occurred_at_ms,created_at_ms)
                   SELECT 'promotion-conversion-' || md5('use:' || first_use.user_id),
                          'authority-use-' || first_use.user_id,'use',first_use.session_id,b.visitor_hmac,first_use.user_id,first_use.started_at_ms,%s
                   FROM (SELECT DISTINCT ON (i.owner_user_id) i.owner_user_id AS user_id,i.session_id,i.started_at_ms
                         FROM interview_sessions i JOIN auth_users u ON u.user_id=i.owner_user_id
                         WHERE i.started_at_ms IS NOT NULL ORDER BY i.owner_user_id,i.started_at_ms) first_use
                   LEFT JOIN promotion_identity_bindings b ON b.user_id=first_use.user_id AND b.deleted_at_ms IS NULL
                   WHERE first_use.started_at_ms >= %s AND first_use.started_at_ms < %s
                   ON CONFLICT (conversion_type,source_record_id) DO NOTHING""",
                (current, start_ms, end_ms),
            )
            inserted += cursor.rowcount
            cursor.execute(
                """INSERT INTO promotion_conversion_events
                   (conversion_event_id,event_id,conversion_type,source_record_id,visitor_hmac,user_id,amount_cents,currency,occurred_at_ms,created_at_ms)
                   SELECT 'promotion-conversion-' || md5('order:' || o.order_id),
                          'authority-order-' || o.order_id,'order',o.order_id,b.visitor_hmac,o.user_id,o.amount_cents,o.currency,o.created_at_ms,%s
                   FROM billing_checkout_orders o JOIN auth_users u ON u.user_id=o.user_id
                   LEFT JOIN promotion_identity_bindings b ON b.user_id=o.user_id AND b.deleted_at_ms IS NULL
                   WHERE o.created_at_ms >= %s AND o.created_at_ms < %s
                   ON CONFLICT (conversion_type,source_record_id) DO NOTHING""",
                (current, start_ms, end_ms),
            )
            inserted += cursor.rowcount
            cursor.execute(
                """INSERT INTO promotion_conversion_events
                   (conversion_event_id,event_id,conversion_type,source_record_id,visitor_hmac,user_id,amount_cents,currency,occurred_at_ms,created_at_ms)
                   SELECT 'promotion-conversion-' || md5('payment:' || o.order_id),
                          'authority-payment-' || o.order_id,'payment',o.order_id,b.visitor_hmac,o.user_id,o.amount_cents,o.currency,o.paid_at_ms,%s
                   FROM billing_checkout_orders o JOIN auth_users u ON u.user_id=o.user_id
                   LEFT JOIN promotion_identity_bindings b ON b.user_id=o.user_id AND b.deleted_at_ms IS NULL
                   WHERE o.status='paid' AND o.paid_at_ms >= %s AND o.paid_at_ms < %s
                   ON CONFLICT (conversion_type,source_record_id) DO NOTHING""",
                (current, start_ms, end_ms),
            )
            inserted += cursor.rowcount
            connection.commit()
        return inserted

    def materialize_attribution(self, *, start_ms: int, end_ms: int) -> int:
        total = 0
        current = now_ms()
        for model in ATTRIBUTION_MODELS:
            link_field = "first_touch_link_id" if model == "first_touch" else "last_non_direct_link_id"
            with self.repository.connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    f"""INSERT INTO promotion_attribution_facts
                       (attribution_fact_id,conversion_type,source_record_id,attribution_model,model_version,
                        channel_id,campaign_id,link_id,bucket_code,amount_cents,occurred_at_ms,computed_at_ms)
                       SELECT 'promotion-fact-' || md5(e.conversion_type || ':' || e.source_record_id || ':{model}:{self.settings.promotion_model_version}'),
                              e.conversion_type,e.source_record_id,%s,%s,l.channel_id,l.campaign_id,l.link_id,
                              CASE WHEN l.link_id IS NULL THEN 'unattributed' ELSE NULL END,
                              e.amount_cents,e.occurred_at_ms,%s
                       FROM promotion_conversion_events e
                       LEFT JOIN promotion_identity_bindings b ON b.deleted_at_ms IS NULL AND (
                         (e.user_id IS NOT NULL AND b.user_id=e.user_id) OR
                         (e.user_id IS NULL AND e.visitor_hmac IS NOT NULL AND b.visitor_hmac=e.visitor_hmac)
                       )
                       LEFT JOIN promotion_links l ON l.link_id=b.{link_field}
                       WHERE e.occurred_at_ms >= %s AND e.occurred_at_ms < %s
                         AND (e.conversion_type <> 'download' OR b.identity_binding_id IS NOT NULL OR e.occurred_at_ms < %s)
                       ON CONFLICT (conversion_type,source_record_id,attribution_model,model_version)
                       DO UPDATE SET channel_id=EXCLUDED.channel_id,campaign_id=EXCLUDED.campaign_id,link_id=EXCLUDED.link_id,
                         bucket_code=EXCLUDED.bucket_code,computed_at_ms=EXCLUDED.computed_at_ms
                       WHERE promotion_attribution_facts.bucket_code='unattributed' AND EXCLUDED.link_id IS NOT NULL""",
                    (model, self.settings.promotion_model_version, current, start_ms, end_ms, current - self.settings.promotion_attribution_window_days * 86_400_000),
                )
                total += cursor.rowcount
                connection.commit()
        return total

    def snapshot_day(self, day: datetime) -> int:
        timezone_info = ZoneInfo(self.settings.promotion_reporting_timezone)
        start = day.astimezone(timezone_info).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        records: list[tuple[str, str, dict[str, object], dict[str, object]]] = []
        for model in ATTRIBUTION_MODELS:
            overview = self.repository.overview(start_ms=start_ms, end_ms=end_ms, model=model)
            coverage = self.coverage_metadata(start_ms=start_ms, end_ms=end_ms, model=model)
            records.append((model, "overview:all", overview, coverage))
            for dimension in ("channel", "campaign", "link"):
                for item in self.repository.dimension_report(start_ms=start_ms, end_ms=end_ms, model=model, dimension=dimension):
                    dimension_id = str(item["dimension_id"])
                    metrics = {key: value for key, value in item.items() if key not in {"dimension_id", "dimension_name"}}
                    records.append((model, f"{dimension}:{dimension_id}", metrics, coverage))
        count = 0
        with self.repository.connect() as connection, connection.cursor() as cursor:
            for model, dimension_key, metrics, coverage in records:
                dimension_type, dimension_id = dimension_key.split(":", 1)
                cursor.execute(
                    """INSERT INTO promotion_metric_snapshots
                       (bucket_date,attribution_model,model_version,dimension_type,dimension_id,metrics_json,coverage_json,computed_at_ms)
                       VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
                       ON CONFLICT (bucket_date,attribution_model,model_version,dimension_type,dimension_id)
                       DO UPDATE SET metrics_json=EXCLUDED.metrics_json,coverage_json=EXCLUDED.coverage_json,computed_at_ms=EXCLUDED.computed_at_ms""",
                    (start.date(), model, self.settings.promotion_model_version, dimension_type, dimension_id,
                     json.dumps(metrics, default=_json_metric_default), json.dumps(coverage, default=_json_metric_default), now_ms()),
                )
                count += 1
            connection.commit()
        return count

    def coverage_metadata(self, *, start_ms: int, end_ms: int, model: str) -> dict[str, object]:
        recent = end_ms + self.settings.promotion_attribution_window_days * 86_400_000 > now_ms()
        buckets = self.repository.attribution_buckets(start_ms=start_ms, end_ms=end_ms, model=model)
        unattributed = next((item for item in buckets if item.get("bucket") == "unattributed"), None)
        return {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "timezone": self.settings.promotion_reporting_timezone,
            "attributionModel": model,
            "modelVersion": self.settings.promotion_model_version,
            "coverageStart": start_ms,
            "freshness": "current",
            "unattributedCount": int(unattributed.get("registrations") or 0) if unattributed else 0,
            "cohortState": "observing" if recent else "mature",
        }

    def cleanup_retention(self) -> int:
        cutoff = now_ms() - self.settings.promotion_touchpoint_retention_days * 86_400_000
        with self.repository.connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM promotion_touchpoints WHERE occurred_at_ms < %s", (cutoff,))
            count = cursor.rowcount
            connection.commit()
        return count

    def reconcile(self, *, start_ms: int, end_ms: int) -> int:
        with self.repository.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                    (SELECT COUNT(*) FROM auth_users WHERE created_at_ms >= %s AND created_at_ms < %s) AS global_registrations,
                    (SELECT COUNT(*) FROM billing_checkout_orders WHERE created_at_ms >= %s AND created_at_ms < %s) AS global_orders,
                    (SELECT COUNT(*) FROM billing_checkout_orders WHERE status='paid' AND paid_at_ms >= %s AND paid_at_ms < %s) AS global_paid,
                    (SELECT COUNT(DISTINCT source_record_id) FROM promotion_attribution_facts WHERE conversion_type='registration' AND attribution_model='first_touch' AND model_version=%s AND occurred_at_ms >= %s AND occurred_at_ms < %s) AS attributed_registrations,
                    (SELECT COUNT(DISTINCT source_record_id) FROM promotion_attribution_facts WHERE conversion_type='order' AND attribution_model='first_touch' AND model_version=%s AND occurred_at_ms >= %s AND occurred_at_ms < %s) AS attributed_orders,
                    (SELECT COUNT(DISTINCT source_record_id) FROM promotion_attribution_facts WHERE conversion_type='payment' AND attribution_model='first_touch' AND model_version=%s AND occurred_at_ms >= %s AND occurred_at_ms < %s) AS attributed_paid""",
                (start_ms, end_ms, start_ms, end_ms, start_ms, end_ms,
                 self.settings.promotion_model_version, start_ms, end_ms,
                 self.settings.promotion_model_version, start_ms, end_ms,
                 self.settings.promotion_model_version, start_ms, end_ms),
            )
            row = cursor.fetchone()
        return sum(
            max(0, int(row[attributed]) - int(row[global_key]))
            for attributed, global_key in (
                ("attributed_registrations", "global_registrations"),
                ("attributed_orders", "global_orders"),
                ("attributed_paid", "global_paid"),
            )
        )

    def run_once(self) -> dict[str, int | str]:
        run_id = f"promotion-run-{uuid4().hex}"
        end_ms = now_ms()
        start_ms = end_ms - 90 * 86_400_000
        if not self.settings.database_url:
            raise RuntimeError("database_url is required for promotion analytics")
        with psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-promotion-lock",
            row_factory=dict_row,
        ) as lock_connection, lock_connection.cursor() as lock_cursor:
            lock_cursor.execute("SELECT pg_try_advisory_lock(hashtextextended('offersteady:promotion-analytics',0)) AS acquired")
            if not lock_cursor.fetchone()["acquired"]:
                return {"status": "skipped", "processed": 0}
            lock_cursor.execute(
                """INSERT INTO promotion_analytics_runs
                   (run_id,run_kind,status,range_started_at_ms,range_ended_at_ms,started_at_ms)
                   VALUES (%s,'scheduled','running',%s,%s,%s)""",
                (run_id, start_ms, end_ms, end_ms),
            )
            lock_connection.commit()
            try:
                consumed = self.consume()
                conversions = self.derive_authoritative_conversions(start_ms=start_ms, end_ms=end_ms)
                facts = self.materialize_attribution(start_ms=start_ms, end_ms=end_ms)
                timezone_info = ZoneInfo(self.settings.promotion_reporting_timezone)
                local_today = datetime.now(timezone_info)
                snapshots = sum(self.snapshot_day(local_today - timedelta(days=offset)) for offset in range(0, 8))
                removed = self.cleanup_retention()
                mismatches = self.reconcile(start_ms=start_ms, end_ms=end_ms)
                processed = int(consumed["accepted"]) + conversions + facts
                status = "completed"
                error = None
            except Exception as exc:
                processed = snapshots = removed = mismatches = 0
                status = "failed"
                error = type(exc).__name__[:80]
            finally:
                lock_cursor.execute(
                    """UPDATE promotion_analytics_runs SET status=%s,processed_count=%s,mismatch_count=%s,
                       safe_error_code=%s,completed_at_ms=%s WHERE run_id=%s""",
                    (status, processed, mismatches, error, now_ms(), run_id),
                )
                lock_cursor.execute("SELECT pg_advisory_unlock(hashtextextended('offersteady:promotion-analytics',0))")
                lock_connection.commit()
        return {"status": status, "processed": processed, "snapshots": snapshots, "retentionRemoved": removed, "mismatches": mismatches}


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run isolated promotion analytics aggregation")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--ingest-interval-seconds", type=int, default=settings.promotion_ingest_interval_seconds)
    args = parser.parse_args()
    if not settings.promotion_enabled:
        raise SystemExit("promotion analytics is disabled")
    job = PromotionAnalyticsJob(PromotionRepository(settings))
    if args.once:
        print(json.dumps(job.run_once(), ensure_ascii=False))
        return
    aggregate_interval = max(30, args.interval_seconds)
    ingest_interval = max(1, min(args.ingest_interval_seconds, aggregate_interval))
    next_aggregation_at = 0.0
    while True:
        current = monotonic()
        if current >= next_aggregation_at:
            job.run_once()
            next_aggregation_at = monotonic() + aggregate_interval
        else:
            try:
                job.consume()
            except Exception:
                # Ingestion is isolated from product traffic and will retry on the
                # next bounded cycle. The scheduled run records aggregate health.
                pass
        sleep(min(ingest_interval, max(1.0, next_aggregation_at - monotonic())))


if __name__ == "__main__":
    main()
