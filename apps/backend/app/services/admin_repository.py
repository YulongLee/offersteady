from __future__ import annotations

import json
import hashlib
import hmac
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import BoundedSemaphore
from time import time
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings


def now_ms() -> int:
    return int(time() * 1000)


class AdminRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._query_budget = BoundedSemaphore(max(1, settings.admin_max_concurrent_queries))
        self._ensure_tables()

    @contextmanager
    def connect(self, *, readonly: bool = False):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required for commercial admin")
        acquired = self._query_budget.acquire(
            timeout=max(0.1, self.settings.admin_query_timeout_ms / 1000)
        )
        if not acquired:
            raise TimeoutError("admin_database_budget_exhausted")
        try:
            with psycopg.connect(
                self.settings.database_url,
                connect_timeout=self.settings.database_connect_timeout_seconds,
                application_name=f"{self.settings.database_application_name}-admin",
                row_factory=dict_row,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, false)",
                        (str(self.settings.admin_query_timeout_ms),),
                    )
                    if readonly:
                        cursor.execute("SET TRANSACTION READ ONLY")
                yield connection
        finally:
            self._query_budget.release()

    def authorization_for_user(self, user_id: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM admin_authorizations WHERE user_id = %s", (user_id,))

    def authorization_by_login(self, login_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT a.* FROM admin_authorizations a
            JOIN auth_users u ON u.user_id = a.user_id
            WHERE LOWER(u.login_id) = LOWER(%s)
            """,
            (login_id,),
        )

    def list_administrators(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT a.user_id, a.role, a.status, a.authorization_version,
                   a.created_at_ms, a.updated_at_ms, a.disabled_at_ms,
                   CASE
                     WHEN phone.provider_subject_hint IS NOT NULL THEN phone.provider_subject_hint
                     WHEN LENGTH(u.login_id) <= 4 THEN '****'
                     ELSE LEFT(u.login_id, 3) || '****' || RIGHT(u.login_id, 4)
                   END AS masked_login,
                   LEFT(u.display_name, 24) AS display_name
            FROM admin_authorizations a
            JOIN auth_users u ON u.user_id = a.user_id
            LEFT JOIN LATERAL (
              SELECT b.provider_subject_hint
              FROM auth_identity_bindings b
              WHERE b.user_id = a.user_id AND b.provider = 'sms'
              LIMIT 1
            ) phone ON TRUE
            ORDER BY a.created_at_ms DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    def active_administrator_count(self) -> int:
        row = self._one(
            "SELECT COUNT(*) AS count FROM admin_authorizations WHERE status = 'active'",
            (),
        )
        return int(row["count"]) if row else 0

    def upsert_authorization(
        self,
        *,
        user_id: str,
        role: str,
        encrypted_secret: str,
        created_by_user_id: str | None,
    ) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_authorizations (
                  authorization_id, user_id, role, status, authorization_version,
                  totp_secret_ciphertext, created_by_user_id, created_at_ms, updated_at_ms
                ) VALUES (%s,%s,%s,'active',1,%s,%s,%s,%s)
                ON CONFLICT (user_id) DO UPDATE SET
                  role = EXCLUDED.role,
                  status = 'active',
                  authorization_version = admin_authorizations.authorization_version + 1,
                  totp_secret_ciphertext = EXCLUDED.totp_secret_ciphertext,
                  updated_at_ms = EXCLUDED.updated_at_ms,
                  disabled_at_ms = NULL
                RETURNING *
                """,
                (
                    f"admin-authz-{uuid4().hex}",
                    user_id,
                    role,
                    encrypted_secret,
                    created_by_user_id,
                    current,
                    current,
                ),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def user_by_login(self, login_id: str) -> dict[str, Any] | None:
        direct_login, sms_login = self._login_candidates(login_id)
        return self._one(
            """
            SELECT user_id, login_id, display_name
            FROM auth_users
            WHERE LOWER(login_id) = LOWER(%s)
               OR LOWER(login_id) = LOWER(%s)
            """,
            (direct_login, sms_login),
        )

    def _login_candidates(self, login_id: str) -> tuple[str, str]:
        normalized = login_id.strip()
        digits = re.sub(r"\D", "", normalized)
        if digits.startswith("86") and len(digits) == 13:
            digits = digits[2:]
        if re.fullmatch(r"1[3-9]\d{9}", digits):
            secret = self.settings.auth_jwt_secret or "offersteady-dev-jwt-secret"
            digest = hmac.new(
                secret.encode("utf-8"),
                f"+86{digits}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            return normalized, f"sms:{digest}"
        return normalized, f"sms:{normalized}"

    def disable_authorization(self, *, user_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT user_id, role, status FROM admin_authorizations WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            authorization = cursor.fetchone()
            if authorization is None:
                raise LookupError("admin_authorization_not_found")
            if authorization["status"] == "disabled":
                return dict(authorization)
            if authorization["role"] == "super_admin":
                cursor.execute(
                    "SELECT COUNT(*) AS count FROM admin_authorizations WHERE role = 'super_admin' AND status = 'active'"
                )
                if int(cursor.fetchone()["count"]) <= 1:
                    raise PermissionError("last_super_admin_cannot_be_disabled")
            cursor.execute(
                """
                UPDATE admin_authorizations
                SET status = 'disabled',
                    authorization_version = authorization_version + 1,
                    disabled_at_ms = %s,
                    updated_at_ms = %s
                WHERE user_id = %s
                RETURNING user_id, role, status, authorization_version, disabled_at_ms
                """,
                (current, current, user_id),
            )
            result = dict(cursor.fetchone())
            cursor.execute(
                """
                UPDATE admin_sessions
                SET status = 'revoked', revoked_at_ms = %s, last_used_at_ms = %s
                WHERE user_id = %s AND status = 'active'
                """,
                (current, current, user_id),
            )
            connection.commit()
        return result

    def validate_user_session(self, *, user_id: str, auth_session_id: str) -> bool:
        row = self._one(
            """
            SELECT 1 FROM auth_sessions
            WHERE auth_session_id = %s AND user_id = %s AND status = 'active' AND expires_at_ms > %s
            """,
            (auth_session_id, user_id, now_ms()),
        )
        return row is not None

    def create_session(self, values: dict[str, Any]) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_sessions (
                  admin_session_id, authorization_id, user_id, token_fingerprint,
                  authorization_version, role, permissions_json, status, issued_at_ms,
                  expires_at_ms, recent_mfa_at_ms, last_used_at_ms, ip_hash, user_agent_hash
                ) VALUES (
                  %(admin_session_id)s, %(authorization_id)s, %(user_id)s, %(token_fingerprint)s,
                  %(authorization_version)s, %(role)s, %(permissions_json)s::jsonb, 'active',
                  %(issued_at_ms)s, %(expires_at_ms)s, %(recent_mfa_at_ms)s,
                  %(last_used_at_ms)s, %(ip_hash)s, %(user_agent_hash)s
                )
                """,
                {**values, "permissions_json": json.dumps(values["permissions_json"])},
            )
            connection.commit()

    def session_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT s.*, a.status AS authorization_status, a.authorization_version AS current_authorization_version
            FROM admin_sessions s
            JOIN admin_authorizations a ON a.authorization_id = s.authorization_id
            WHERE s.token_fingerprint = %s
            """,
            (fingerprint,),
        )

    def touch_session(self, admin_session_id: str) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE admin_sessions SET last_used_at_ms = %s WHERE admin_session_id = %s",
                (now_ms(), admin_session_id),
            )
            connection.commit()

    def step_up_session(self, admin_session_id: str) -> int:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE admin_sessions SET recent_mfa_at_ms = %s, last_used_at_ms = %s WHERE admin_session_id = %s",
                (current, current, admin_session_id),
            )
            connection.commit()
        return current

    def revoke_session(self, admin_session_id: str) -> None:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_sessions SET status = 'revoked', revoked_at_ms = %s, last_used_at_ms = %s
                WHERE admin_session_id = %s AND status = 'active'
                """,
                (current, current, admin_session_id),
            )
            connection.commit()

    def append_audit(self, values: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_audit_events (
                  audit_event_id, actor_user_id, actor_role, action, resource_type,
                  resource_id, reason, request_id, result, safe_details_json,
                  source_ip_hash, user_agent_hash, created_at_ms
                ) VALUES (
                  %(audit_event_id)s, %(actor_user_id)s, %(actor_role)s, %(action)s,
                  %(resource_type)s, %(resource_id)s, %(reason)s, %(request_id)s,
                  %(result)s, %(safe_details_json)s::jsonb, %(source_ip_hash)s,
                  %(user_agent_hash)s, %(created_at_ms)s
                ) RETURNING *
                """,
                {**values, "safe_details_json": json.dumps(values.get("safe_details_json", {}))},
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def dashboard(self) -> dict[str, Any]:
        current = now_ms()
        since = current - 24 * 60 * 60 * 1000
        idle_cutoff = current - self.settings.interview_idle_timeout_seconds * 1000
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            queries = {
                "users": "SELECT COUNT(*) AS value FROM auth_users",
                "active_sessions": "SELECT COUNT(*) AS value FROM interview_sessions WHERE status = 'live' AND deleted_at_ms IS NULL AND last_activity_at_ms >= %s",
                "idle_sessions": "SELECT COUNT(*) AS value FROM interview_sessions WHERE status = 'live' AND deleted_at_ms IS NULL AND last_activity_at_ms < %s",
                "pending_orders": "SELECT COUNT(*) AS value FROM billing_checkout_orders WHERE status = 'payment_pending'",
                "failed_materials": "SELECT COUNT(*) AS value FROM material_documents WHERE status NOT IN ('ready','deleted')",
                "ai_calls_24h": "SELECT COUNT(*) AS value FROM ai_usage_records WHERE created_at_ms >= %s",
                "ai_errors_24h": "SELECT COUNT(*) AS value FROM ai_usage_records WHERE created_at_ms >= %s AND status <> 'success'",
            }
            result: dict[str, Any] = {}
            for key, query in queries.items():
                parameter = idle_cutoff if key in {"active_sessions", "idle_sessions"} else since
                cursor.execute(query, (parameter,) if "%s" in query else ())
                result[key] = int(cursor.fetchone()["value"])
        return {"updated_at_ms": current, "window_started_at_ms": since, **result}

    def capacity_counts(self) -> dict[str, int]:
        current = now_ms()
        active_cutoff = current - self.settings.interview_idle_timeout_seconds * 1000
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)::INTEGER AS active_interviews,
                       COUNT(DISTINCT owner_user_id)::INTEGER AS active_users
                FROM interview_sessions
                WHERE status = 'live' AND deleted_at_ms IS NULL
                  AND last_activity_at_ms >= %s
                """,
                (active_cutoff,),
            )
            sessions = cursor.fetchone()
            cursor.execute(
                """
                SELECT COUNT(*)::INTEGER AS database_connections,
                       current_setting('max_connections')::INTEGER AS database_connection_limit
                FROM pg_stat_activity
                WHERE datname = current_database()
                """
            )
            database = cursor.fetchone()
        return {
            "activeInterviews": int(sessions["active_interviews"] or 0),
            "activeUsers": int(sessions["active_users"] or 0),
            "databaseConnections": int(database["database_connections"] or 0),
            "databaseConnectionLimit": int(database["database_connection_limit"] or 0),
        }

    def record_capacity_peak(self, *, at_ms: int, active_interviews: int) -> None:
        five_minute_bucket = at_ms - at_ms % 300_000
        local = datetime.fromtimestamp(at_ms / 1000, tz=timezone.utc).astimezone(ZoneInfo("Asia/Shanghai"))
        daily_bucket = int(local.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        with self.connect() as connection, connection.cursor() as cursor:
            for bucket_start_ms, granularity in (
                (five_minute_bucket, "capacity_5m"),
                (daily_bucket, "daily"),
            ):
                cursor.execute(
                    """
                    INSERT INTO admin_metric_snapshots(
                      bucket_start_ms, granularity, metric_key, metric_value, sample_count,
                      coverage_state, definition_version, computed_at_ms
                    ) VALUES (%s,%s,'peak_concurrent_interviews',%s,1,'complete',1,%s)
                    ON CONFLICT (bucket_start_ms, granularity, metric_key) DO UPDATE SET
                      metric_value = GREATEST(
                        admin_metric_snapshots.metric_value,
                        EXCLUDED.metric_value
                      ),
                      sample_count = admin_metric_snapshots.sample_count + 1,
                      coverage_state = 'complete',
                      computed_at_ms = EXCLUDED.computed_at_ms
                    """,
                    (bucket_start_ms, granularity, active_interviews, at_ms),
                )
            connection.commit()

    def compute_and_upsert_metric(
        self,
        *,
        definition,
        bucket_start_ms: int,
        bucket_end_ms: int,
        granularity: str,
        coverage_state: str,
    ) -> bool:
        lock_key = f"admin-analytics:{granularity}:{bucket_start_ms}:{definition.key}"
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(hashtextextended(%s, 0)) AS acquired", (lock_key,))
            if not bool(cursor.fetchone()["acquired"]):
                connection.rollback()
                return False
            value = None
            sample_count = 0
            if definition.sql is not None:
                cursor.execute(definition.sql, (bucket_start_ms, bucket_end_ms))
                aggregate = cursor.fetchone()
                value = aggregate["value"]
                sample_count = int(aggregate["sample_count"] or 0)
                if value is None and not definition.backfillable:
                    coverage_state = "unavailable"
            cursor.execute(
                """
                INSERT INTO admin_metric_snapshots(
                  bucket_start_ms, granularity, metric_key, metric_value, sample_count,
                  coverage_state, definition_version, computed_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (bucket_start_ms, granularity, metric_key) DO UPDATE SET
                  metric_value = EXCLUDED.metric_value,
                  sample_count = EXCLUDED.sample_count,
                  coverage_state = EXCLUDED.coverage_state,
                  definition_version = EXCLUDED.definition_version,
                  computed_at_ms = EXCLUDED.computed_at_ms
                """,
                (
                    bucket_start_ms, granularity, definition.key, value, sample_count,
                    coverage_state, definition.version, now_ms(),
                ),
            )
            connection.commit()
        return True

    def create_analytics_run(self, values: dict[str, Any]) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_metric_aggregation_runs(
                  run_id, run_kind, granularity, range_started_at_ms, range_ended_at_ms,
                  status, started_at_ms
                ) VALUES (
                  %(run_id)s, %(run_kind)s, %(granularity)s, %(range_started_at_ms)s,
                  %(range_ended_at_ms)s, 'running', %(started_at_ms)s
                )
                """,
                values,
            )
            connection.commit()

    def finish_analytics_run(
        self,
        *,
        run_id: str,
        status: str,
        bucket_count: int,
        metric_count: int,
        safe_error_code: str | None,
    ) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_metric_aggregation_runs
                SET status = %s, bucket_count = %s, metric_count = %s,
                    safe_error_code = %s, completed_at_ms = %s
                WHERE run_id = %s
                """,
                (status, bucket_count, metric_count, safe_error_code, now_ms(), run_id),
            )
            connection.commit()

    def list_analytics_snapshots(
        self,
        *,
        start_ms: int,
        end_ms: int,
        metric_keys: list[str],
        granularity: str,
    ) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT bucket_start_ms, metric_key, metric_value, sample_count,
                   coverage_state, definition_version, computed_at_ms
            FROM admin_metric_snapshots
            WHERE granularity = %s AND bucket_start_ms >= %s AND bucket_start_ms < %s
              AND metric_key = ANY(%s)
            ORDER BY metric_key, bucket_start_ms
            """,
            (granularity, start_ms, end_ms, metric_keys),
        )

    def analytics_health(self, *, expected_since_ms: int) -> dict[str, Any]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_id, status, granularity, bucket_count, metric_count,
                       safe_error_code, started_at_ms, completed_at_ms
                FROM admin_metric_aggregation_runs
                ORDER BY started_at_ms DESC LIMIT 1
                """
            )
            latest = cursor.fetchone()
            cursor.execute(
                """
                SELECT MAX(computed_at_ms) AS last_success_at_ms,
                       COUNT(DISTINCT bucket_start_ms) FILTER (
                         WHERE granularity = 'daily' AND bucket_start_ms >= %s
                       )::INTEGER AS covered_days
                FROM admin_metric_snapshots
                """,
                (expected_since_ms,),
            )
            coverage = cursor.fetchone()
        return {
            "lastSuccessAtMs": coverage["last_success_at_ms"],
            "coveredDays": int(coverage["covered_days"] or 0),
            "latestRun": dict(latest) if latest else None,
        }

    def analytics_earliest_business_ms(self) -> int | None:
        row = self._one(
            """
            SELECT MIN(value) AS earliest FROM (
              SELECT MIN(created_at_ms) AS value FROM auth_users
              UNION ALL SELECT MIN(created_at_ms) FROM interview_sessions
              UNION ALL SELECT MIN(created_at_ms) FROM points_redemption_ledger
              UNION ALL SELECT MIN(created_at_ms) FROM billing_checkout_orders
              UNION ALL SELECT MIN(created_at_ms) FROM material_documents
              UNION ALL SELECT MIN(created_at_ms) FROM ai_usage_records
            ) source
            """,
            (),
        )
        return int(row["earliest"]) if row and row["earliest"] is not None else None

    def cleanup_hourly_analytics(self, *, before_ms: int) -> int:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM admin_metric_snapshots WHERE granularity = 'hourly' AND bucket_start_ms < %s",
                (before_ms,),
            )
            removed = cursor.rowcount
            connection.commit()
        return removed

    def observability(self) -> dict[str, Any]:
        current = now_ms()
        since = current - 24 * 60 * 60 * 1000
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT operation_kind, provider, model, status, COUNT(*)::INTEGER AS calls,
                       COALESCE(AVG(duration_ms), 0)::INTEGER AS average_duration_ms,
                       COALESCE(SUM(total_units), 0)::INTEGER AS total_units
                FROM ai_usage_records
                WHERE created_at_ms >= %s
                GROUP BY operation_kind, provider, model, status
                ORDER BY calls DESC
                LIMIT 100
                """,
                (since,),
            )
            ai = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT strategy, COUNT(*)::INTEGER AS traces,
                       COALESCE(AVG(candidate_count), 0)::REAL AS average_candidates,
                       COALESCE(AVG(returned_count), 0)::REAL AS average_returned,
                       COUNT(*) FILTER (WHERE safe_error_code IS NOT NULL)::INTEGER AS errors
                FROM rag_retrieval_traces
                WHERE created_at_ms >= %s
                GROUP BY strategy
                """,
                (since,),
            )
            rag = [dict(row) for row in cursor.fetchall()]
        manifest = json.loads(
            (Path(REPO_ROOT) / "apps/backend/app/desktop_release_manifest.json").read_text(encoding="utf8")
        )
        desktop = [{
            "platform": item.get("platform"),
            "architecture": item.get("architecture"),
            "version": item.get("version"),
            "published_at_ms": item.get("publishedAtMs"),
            "signing_status": item.get("signingStatus"),
            "development_only": item.get("developmentOnly"),
        } for item in manifest.get("entries", [])]
        return {
            "updated_at_ms": current,
            "window_started_at_ms": since,
            "ai": ai,
            "rag": rag,
            "desktop_releases": desktop,
        }

    def list_users(self, *, search: str, limit: int, offset: int) -> list[dict[str, Any]]:
        pattern = f"%{search.strip()}%"
        return self._all(
            """
            SELECT u.user_id, u.display_name, u.last_login_provider, u.last_login_at_ms,
                   u.created_at_ms,
                   COALESCE(SUM(l.points), 0)::INTEGER AS points_balance,
                   COALESCE(r.status, 'active') AS account_status,
                   MAX(CASE WHEN b.provider = 'sms' THEN b.provider_subject_hint END) AS phone_hint
            FROM auth_users u
            LEFT JOIN points_redemption_ledger l ON l.user_id = u.user_id
            LEFT JOIN admin_user_restrictions r ON r.user_id = u.user_id AND r.status = 'active'
            LEFT JOIN auth_identity_bindings b ON b.user_id = u.user_id
            WHERE (%s = '%%' OR u.user_id ILIKE %s OR u.display_name ILIKE %s)
            GROUP BY u.user_id, r.status
            ORDER BY u.created_at_ms DESC LIMIT %s OFFSET %s
            """,
            (pattern, pattern, pattern, limit, offset),
        )

    def list_orders(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT order_id, user_id, amount_cents, currency, channel, provider, status,
                   provider_trade_no, failure_reason, created_at_ms, updated_at_ms, paid_at_ms
            FROM billing_checkout_orders
            ORDER BY created_at_ms DESC LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    def list_redemption_batches(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT b.batch_id, b.campaign, b.points_per_code, b.code_count,
                   b.expires_at_ms, b.created_at_ms,
                   COUNT(c.code_digest) FILTER (WHERE c.status = 'active')::INTEGER AS active_count,
                   COUNT(c.code_digest) FILTER (WHERE c.status = 'redeemed')::INTEGER AS redeemed_count,
                   COUNT(c.code_digest) FILTER (WHERE c.status = 'disabled')::INTEGER AS disabled_count
            FROM admin_redemption_batches b
            LEFT JOIN points_redemption_codes c ON c.batch_id = b.batch_id
            GROUP BY b.batch_id
            ORDER BY b.created_at_ms DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    def create_redemption_batch(
        self,
        *,
        batch_id: str,
        actor_user_id: str,
        idempotency_key: str,
        campaign: str,
        reason: str,
        points: int,
        expires_at_ms: int,
        codes: list[str],
    ) -> tuple[dict[str, Any], bool]:
        if not self.settings.redemption_code_pepper:
            raise RuntimeError("redemption_code_pepper_not_configured")
        current = now_ms()
        pepper = self.settings.redemption_code_pepper.encode("utf-8")
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"admin-redemption:{actor_user_id}:{idempotency_key}",),
            )
            cursor.execute(
                """
                SELECT batch_id, campaign, points_per_code, code_count, expires_at_ms, created_at_ms
                FROM admin_redemption_batches
                WHERE actor_user_id = %s AND idempotency_key = %s
                """,
                (actor_user_id, idempotency_key),
            )
            existing = cursor.fetchone()
            if existing:
                return {**dict(existing), "codes": []}, True
            cursor.execute(
                """
                INSERT INTO admin_redemption_batches(
                  batch_id, actor_user_id, idempotency_key, campaign, reason,
                  points_per_code, code_count, expires_at_ms, created_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING batch_id, campaign, points_per_code, code_count, expires_at_ms, created_at_ms
                """,
                (
                    batch_id, actor_user_id, idempotency_key, campaign, reason,
                    points, len(codes), expires_at_ms, current,
                ),
            )
            batch = dict(cursor.fetchone())
            rows = []
            for code in codes:
                digest = hmac.new(pepper, code.upper().encode("utf-8"), hashlib.sha256).hexdigest()
                rows.append((digest, f"****-{code[-4:]}", points, batch_id, expires_at_ms, current, current))
            cursor.executemany(
                """
                INSERT INTO points_redemption_codes(
                  code_digest, public_hint, points, status, batch_id, expires_at_ms,
                  created_at_ms, updated_at_ms
                ) VALUES (%s,%s,%s,'active',%s,%s,%s,%s)
                """,
                rows,
            )
            connection.commit()
        return {**batch, "codes": codes}, False

    def list_materials(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT document_id, owner_user_id, document_kind, display_name, status,
                   created_at_ms, updated_at_ms
            FROM material_documents
            WHERE deleted_at_ms IS NULL
            ORDER BY updated_at_ms DESC LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

    def list_sessions(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        current = now_ms()
        idle_cutoff = current - self.settings.interview_idle_timeout_seconds * 1000
        return self._all(
            """
            SELECT session_id, owner_user_id, title,
                   CASE
                     WHEN status = 'live' AND last_activity_at_ms >= %s THEN 'active'
                     WHEN status = 'live' THEN 'idle-timeout'
                     ELSE status
                   END AS activity_state,
                   status, last_activity_at_ms,
                   GREATEST(0, ((%s - last_activity_at_ms) / 60000)::INTEGER) AS idle_minutes,
                   started_at_ms
            FROM interview_sessions
            WHERE deleted_at_ms IS NULL
            ORDER BY updated_at_ms DESC LIMIT %s OFFSET %s
            """,
            (idle_cutoff, current, limit, offset),
        )

    def list_audit(
        self,
        *,
        action: str | None,
        request_id: str | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT audit_event_id, actor_user_id, actor_role, action, resource_type,
                   resource_id, reason, request_id, result, safe_details_json, created_at_ms
            FROM admin_audit_events
            WHERE (%s::TEXT IS NULL OR action = %s)
              AND (%s::TEXT IS NULL OR request_id = %s)
            ORDER BY created_at_ms DESC LIMIT %s OFFSET %s
            """,
            (action, action, request_id, request_id, limit, offset),
        )

    def idempotent_result(self, *, actor_user_id: str, action: str, key: str) -> dict[str, Any] | None:
        row = self._one(
            "SELECT result_json FROM admin_idempotency_records WHERE actor_user_id = %s AND action = %s AND idempotency_key = %s",
            (actor_user_id, action, key),
        )
        return dict(row["result_json"]) if row else None

    def save_idempotent_result(self, *, actor_user_id: str, action: str, key: str, result: dict[str, Any]) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_idempotency_records(actor_user_id, action, idempotency_key, result_json, created_at_ms)
                VALUES (%s,%s,%s,%s::jsonb,%s) ON CONFLICT DO NOTHING
                """,
                (actor_user_id, action, key, json.dumps(result), now_ms()),
            )
            connection.commit()

    def set_user_restriction(self, *, user_id: str, active: bool, reason: str, actor_user_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM auth_users WHERE user_id = %s", (user_id,))
            if cursor.fetchone() is None:
                raise LookupError("user_not_found")
            cursor.execute(
                """
                INSERT INTO admin_user_restrictions (
                  restriction_id, user_id, status, reason, created_by_user_id, created_at_ms, updated_at_ms, revoked_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (user_id) DO UPDATE SET
                  status = EXCLUDED.status, reason = EXCLUDED.reason,
                  created_by_user_id = EXCLUDED.created_by_user_id,
                  updated_at_ms = EXCLUDED.updated_at_ms,
                  revoked_at_ms = EXCLUDED.revoked_at_ms
                RETURNING *
                """,
                (
                    f"restriction-{uuid4().hex}",
                    user_id,
                    "active" if active else "revoked",
                    reason,
                    actor_user_id,
                    current,
                    current,
                    None if active else current,
                ),
            )
            row = dict(cursor.fetchone())
            if active:
                cursor.execute(
                    """
                    UPDATE auth_sessions SET status = 'revoked', revoked_at_ms = %s
                    WHERE user_id = %s AND status = 'active'
                    """,
                    (current, user_id),
                )
            connection.commit()
        return row

    def adjust_points(self, *, user_id: str, points: int, reason: str, reference_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger(
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'admin_adjustment',%s,%s,%s,%s)
                RETURNING ledger_entry_id, user_id, points, created_at_ms, reference_id
                """,
                (f"ledger-{uuid4().hex}", user_id, points, current, reference_id, reason),
            )
            row = dict(cursor.fetchone())
            cursor.execute("SELECT COALESCE(SUM(points),0)::INTEGER AS balance FROM points_redemption_ledger WHERE user_id = %s", (user_id,))
            row["balance"] = int(cursor.fetchone()["balance"])
            if row["balance"] < 0:
                connection.rollback()
                raise ValueError("insufficient_points")
            connection.commit()
        return row

    def adjust_time(self, *, user_id: str, days: int, reason: str, reference_id: str, actor_user_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT GREATEST(
                  %s,
                  COALESCE((SELECT MAX(ends_at_ms) FROM billing_time_pass_entitlements WHERE user_id = %s), %s),
                  COALESCE((SELECT MAX(ends_at_ms) FROM admin_time_entitlements WHERE user_id = %s), %s)
                ) AS starts_at_ms
                """,
                (current, user_id, current, user_id, current),
            )
            starts = int(cursor.fetchone()["starts_at_ms"])
            ends = starts + days * 86_400_000
            cursor.execute(
                """
                INSERT INTO admin_time_entitlements(
                  entitlement_id, user_id, starts_at_ms, ends_at_ms, reference_id,
                  reason, created_by_user_id, created_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (f"admin-entitlement-{uuid4().hex}", user_id, starts, ends, reference_id, reason, actor_user_id, current),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def terminate_session(self, *, session_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE interview_sessions SET status = 'ended', continue_target = 'history',
                  ended_at_ms = %s, updated_at_ms = %s, last_activity_at_ms = %s
                WHERE session_id = %s AND status = 'live'
                RETURNING session_id, owner_user_id, status, ended_at_ms
                """,
                (current, current, current, session_id),
            )
            row = cursor.fetchone()
            connection.commit()
        if row is None:
            raise LookupError("active_session_not_found")
        return dict(row)

    def session_for_termination(self, session_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT session_id, owner_user_id, status, ended_at_ms
            FROM interview_sessions WHERE session_id = %s
            """,
            (session_id,),
        )

    def order_for_reconciliation(self, order_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT order_id, user_id, provider, status, amount_cents, provider_trade_no,
                   created_at_ms, updated_at_ms, expires_at_ms
            FROM billing_checkout_orders WHERE order_id = %s
            """,
            (order_id,),
        )

    def material_task_owner(self, task_id: str) -> dict[str, Any] | None:
        return self._one(
            """
            SELECT task_id, owner_user_id, document_id, current_stage
            FROM processing_tasks WHERE task_id = %s
            """,
            (task_id,),
        )

    def _one(self, query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
        return dict(row) if row else None

    def _all(self, query: str, params: tuple[object, ...]) -> list[dict[str, Any]]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def _ensure_tables(self) -> None:
        migrations = [
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0014_commercial_admin_console.sql",
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0015_admin_redemption_batches.sql",
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0017_admin_operations_analytics.sql",
        ]
        with self.connect() as connection, connection.cursor() as cursor:
            for migration in migrations:
                cursor.execute(migration.read_text(encoding="utf8"))
            connection.commit()
