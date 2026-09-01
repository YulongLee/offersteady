from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import time
from typing import Any, Iterator
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings
from app.services.postgres_migrations import apply_sql_migrations


ATTRIBUTION_MODELS = frozenset({"first_touch", "last_non_direct_touch"})
MODEL_VERSION = 1
KNOWN_BOT_MARKERS = (
    "bot", "crawler", "spider", "preview", "facebookexternalhit", "twitterbot",
    "bytespider", "baiduspider", "wechat", "micromessenger", "curl/", "wget/",
)
_queue_counter_lock = Lock()
_queue_counters: dict[str, int | str | None] = {"accepted": 0, "dropped": 0, "lastErrorCode": None}


def validate_promotion_runtime(settings: Settings) -> None:
    """Fail closed before production attribution can use weak or missing secrets."""
    if not settings.promotion_enabled:
        return
    if not settings.database_url:
        raise RuntimeError("promotion analytics requires OFFERSTEADY_DATABASE_URL")
    if not settings.redis_url:
        raise RuntimeError("promotion analytics requires OFFERSTEADY_REDIS_URL")
    if settings.environment in {"staging", "production"}:
        secret = settings.promotion_visitor_hmac_secret
        if len(secret) < 32 or secret == "offersteady-local-promotion-hmac":
            raise RuntimeError("promotion analytics requires a production OFFERSTEADY_PROMOTION_VISITOR_HMAC_SECRET")


def now_ms() -> int:
    return int(time() * 1000)


def safe_destination(path: str, allowed_prefixes: list[str]) -> bool:
    if not path.startswith("/") or path.startswith("//") or "://" in path or "\r" in path or "\n" in path:
        return False
    clean_path = path.split("?", 1)[0]
    return any(clean_path == prefix or (prefix != "/" and clean_path.startswith(f"{prefix.rstrip('/')}/")) for prefix in allowed_prefixes)


def classify_client(user_agent: str | None, *, admin_preview: bool, internal_test: bool) -> str | None:
    if admin_preview:
        return "admin_preview"
    if internal_test:
        return "internal_test"
    lowered = (user_agent or "").lower()[:512]
    if not lowered:
        return "missing_user_agent"
    return "known_bot_or_preview" if any(marker in lowered for marker in KNOWN_BOT_MARKERS) else None


def device_class(user_agent: str | None) -> str:
    lowered = (user_agent or "").lower()[:512]
    if any(marker in lowered for marker in ("ipad", "tablet")):
        return "tablet"
    if any(marker in lowered for marker in ("mobile", "iphone", "android")):
        return "mobile"
    return "desktop" if lowered else "unknown"


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def cost_metrics(*, cost_cents: int | None, revenue_cents: int, paying_users: int) -> dict[str, float | int | str | None]:
    if cost_cents is None:
        return {"costCents": None, "cacCents": None, "roas": None, "roi": None, "costCoverage": "missing"}
    if cost_cents == 0:
        return {"costCents": 0, "cacCents": None, "roas": None, "roi": None, "costCoverage": "complete"}
    return {
        "costCents": cost_cents,
        "cacCents": round(cost_cents / paying_users) if paying_users else None,
        "roas": round(revenue_cents / cost_cents, 6),
        "roi": round((revenue_cents - cost_cents) / cost_cents, 6),
        "costCoverage": "complete",
    }


class PromotionRepository:
    """Bounded PostgreSQL access for promotion control-plane and analytics facts only."""

    def __init__(self, settings: Settings, *, migrate: bool = True) -> None:
        validate_promotion_runtime(settings)
        self.settings = settings
        self._query_budget = BoundedSemaphore(max(1, settings.admin_max_concurrent_queries))
        if migrate:
            self.ensure_schema()

    @contextmanager
    def connect(self, *, readonly: bool = False) -> Iterator[psycopg.Connection]:
        if not self.settings.database_url:
            raise RuntimeError("database_url is required for promotion analytics")
        acquired = self._query_budget.acquire(timeout=max(0.05, self.settings.admin_query_timeout_ms / 1000))
        if not acquired:
            raise TimeoutError("promotion_database_budget_exhausted")
        try:
            with psycopg.connect(
                self.settings.database_url,
                connect_timeout=self.settings.database_connect_timeout_seconds,
                application_name=f"{self.settings.database_application_name}-promotion",
                row_factory=dict_row,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('statement_timeout', %s, false)", (str(self.settings.admin_query_timeout_ms),))
                    if readonly:
                        cursor.execute("SET TRANSACTION READ ONLY")
                yield connection
        finally:
            self._query_budget.release()

    def ensure_schema(self) -> None:
        migration = Path(REPO_ROOT) / "apps/backend/migrations/versions/0038_promotion_center.sql"
        with self.connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, [migration])
            connection.commit()

    def _one(self, query: str, params: tuple[object, ...]) -> dict[str, Any] | None:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
        return dict(row) if row else None

    def _all(self, query: str, params: tuple[object, ...]) -> list[dict[str, Any]]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def create_channel(self, *, code: str, name: str, sort_order: int, actor_user_id: str) -> dict[str, Any]:
        current = now_ms()
        channel_id = f"promotion-channel-{uuid4().hex}"
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO promotion_channels
                   (channel_id, code, name, sort_order, status, is_system, created_by_user_id, created_at_ms, updated_at_ms)
                   VALUES (%s,%s,%s,%s,'active',FALSE,%s,%s,%s) RETURNING *""",
                (channel_id, code, name, sort_order, actor_user_id, current, current),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def list_channels(self, *, include_inactive: bool = True) -> list[dict[str, Any]]:
        return self._all(
            """SELECT channel_id, code, name, sort_order, status, is_system, created_at_ms, updated_at_ms
               FROM promotion_channels WHERE (%s OR status = 'active') ORDER BY sort_order, created_at_ms""",
            (include_inactive,),
        )

    def update_channel(self, channel_id: str, *, name: str | None, sort_order: int | None, status: str | None) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM promotion_channels WHERE channel_id=%s FOR UPDATE", (channel_id,))
            existing = cursor.fetchone()
            if not existing:
                raise LookupError("promotion_channel_not_found")
            if existing["is_system"] and status == "inactive":
                raise PermissionError("system_promotion_channel_cannot_be_disabled")
            if status == "inactive":
                cursor.execute("SELECT 1 FROM promotion_links WHERE channel_id=%s AND status='active' LIMIT 1", (channel_id,))
                if cursor.fetchone():
                    raise ValueError("active_links_must_be_disabled_first")
            cursor.execute(
                """UPDATE promotion_channels SET name=COALESCE(%s,name), sort_order=COALESCE(%s,sort_order),
                   status=COALESCE(%s,status), updated_at_ms=%s WHERE channel_id=%s RETURNING *""",
                (name, sort_order, status, current, channel_id),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def create_campaign(self, values: dict[str, Any], *, actor_user_id: str) -> dict[str, Any]:
        current = now_ms()
        campaign_id = f"promotion-campaign-{uuid4().hex}"
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO promotion_campaigns
                   (campaign_id,name,objective,status,starts_at_ms,ends_at_ms,budget_cents,notes,created_by_user_id,created_at_ms,updated_at_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (campaign_id, values["name"], values["objective"], values["status"], values.get("starts_at_ms"), values.get("ends_at_ms"), values.get("budget_cents"), values["notes"], actor_user_id, current, current),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def list_campaigns(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """SELECT c.*, COALESCE(link_stats.link_count,0) AS link_count,
                      COALESCE(link_stats.channel_count,0) AS channel_count,
                      COALESCE(costs.actual_cost_cents,0) AS actual_cost_cents
               FROM promotion_campaigns c
               LEFT JOIN (
                 SELECT campaign_id,COUNT(*) AS link_count,COUNT(DISTINCT channel_id) AS channel_count
                 FROM promotion_links WHERE campaign_id IS NOT NULL GROUP BY campaign_id
               ) link_stats ON link_stats.campaign_id=c.campaign_id
               LEFT JOIN (
                 SELECT campaign_id,SUM(amount_cents) AS actual_cost_cents
                 FROM promotion_cost_entries WHERE campaign_id IS NOT NULL GROUP BY campaign_id
               ) costs ON costs.campaign_id=c.campaign_id
               ORDER BY c.created_at_ms DESC LIMIT %s OFFSET %s""",
            (limit, offset),
        )

    def campaign(self, campaign_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM promotion_campaigns WHERE campaign_id=%s", (campaign_id,))
        if row:
            row["links"] = self._all(
                """SELECT l.link_id,l.slug,l.content_name,l.status,l.destination_path,c.code AS channel_code,c.name AS channel_name
                   FROM promotion_links l JOIN promotion_channels c ON c.channel_id=l.channel_id
                   WHERE l.campaign_id=%s ORDER BY l.created_at_ms DESC""",
                (campaign_id,),
            )
        return row

    def update_campaign(self, campaign_id: str, values: dict[str, Any]) -> dict[str, Any]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE promotion_campaigns SET name=%s,objective=%s,status=%s,starts_at_ms=%s,ends_at_ms=%s,
                   budget_cents=%s,notes=%s,updated_at_ms=%s WHERE campaign_id=%s RETURNING *""",
                (values["name"], values["objective"], values["status"], values.get("starts_at_ms"), values.get("ends_at_ms"), values.get("budget_cents"), values["notes"], now_ms(), campaign_id),
            )
            row = cursor.fetchone()
            if not row:
                raise LookupError("promotion_campaign_not_found")
            connection.commit()
        return dict(row)

    def _new_slug(self) -> str:
        return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]

    def create_link(self, values: dict[str, Any], *, actor_user_id: str, cloned_from_link_id: str | None = None) -> dict[str, Any]:
        if not safe_destination(values["destination_path"], self.settings.promotion_allowed_destination_prefixes):
            raise ValueError("promotion_destination_not_allowed")
        current = now_ms()
        link_id = f"promotion-link-{uuid4().hex}"
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT status,is_system FROM promotion_channels WHERE channel_id=%s", (values["channel_id"],))
            channel = cursor.fetchone()
            if not channel or channel["status"] != "active" or channel["is_system"]:
                raise ValueError("active_non_system_channel_required")
            if values.get("campaign_id"):
                cursor.execute("SELECT 1 FROM promotion_campaigns WHERE campaign_id=%s", (values["campaign_id"],))
                if not cursor.fetchone():
                    raise ValueError("promotion_campaign_not_found")
            for _ in range(5):
                try:
                    cursor.execute(
                        """INSERT INTO promotion_links
                           (link_id,slug,content_name,channel_id,campaign_id,destination_path,status,starts_at_ms,ends_at_ms,
                            cloned_from_link_id,created_by_user_id,created_at_ms,updated_at_ms)
                           VALUES (%s,%s,%s,%s,%s,%s,'active',%s,%s,%s,%s,%s,%s) RETURNING *""",
                        (link_id, self._new_slug(), values["content_name"], values["channel_id"], values.get("campaign_id"), values["destination_path"], values.get("starts_at_ms"), values.get("ends_at_ms"), cloned_from_link_id, actor_user_id, current, current),
                    )
                    row = dict(cursor.fetchone())
                    connection.commit()
                    return row
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
            raise RuntimeError("promotion_slug_generation_failed")

    def list_links(self, *, limit: int, offset: int, status: str | None = None) -> list[dict[str, Any]]:
        return self._all(
            """SELECT l.*, ch.code AS channel_code,ch.name AS channel_name,c.name AS campaign_name,
                      COUNT(*) FILTER (WHERE t.event_type='qualified_visit' AND t.qualification_state='qualified') AS qualified_visits,
                      COUNT(DISTINCT t.visitor_hmac) FILTER (WHERE t.event_type='qualified_visit' AND t.qualification_state='qualified') AS unique_visitors
               FROM promotion_links l JOIN promotion_channels ch ON ch.channel_id=l.channel_id
               LEFT JOIN promotion_campaigns c ON c.campaign_id=l.campaign_id
               LEFT JOIN promotion_touchpoints t ON t.link_id=l.link_id
               WHERE (%s::text IS NULL OR l.status=%s::text)
               GROUP BY l.link_id,ch.code,ch.name,c.name ORDER BY l.created_at_ms DESC LIMIT %s OFFSET %s""",
            (status, status, limit, offset),
        )

    def link_by_slug(self, slug: str) -> dict[str, Any] | None:
        return self._one(
            """SELECT l.*,c.status AS campaign_status,ch.status AS channel_status
               FROM promotion_links l JOIN promotion_channels ch ON ch.channel_id=l.channel_id
               LEFT JOIN promotion_campaigns c ON c.campaign_id=l.campaign_id WHERE l.slug=%s""",
            (slug,),
        )

    def update_link(self, link_id: str, values: dict[str, Any]) -> dict[str, Any]:
        if not safe_destination(values["destination_path"], self.settings.promotion_allowed_destination_prefixes):
            raise ValueError("promotion_destination_not_allowed")
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM promotion_links WHERE link_id=%s FOR UPDATE", (link_id,))
            existing = cursor.fetchone()
            if not existing:
                raise LookupError("promotion_link_not_found")
            if existing["attribution_locked_at_ms"] is not None and (
                existing["channel_id"] != values["channel_id"] or existing["campaign_id"] != values.get("campaign_id")
            ):
                raise ValueError("promotion_link_attribution_locked_clone_required")
            cursor.execute(
                """UPDATE promotion_links SET content_name=%s,channel_id=%s,campaign_id=%s,destination_path=%s,status=%s,
                   starts_at_ms=%s,ends_at_ms=%s,updated_at_ms=%s WHERE link_id=%s RETURNING *""",
                (values["content_name"], values["channel_id"], values.get("campaign_id"), values["destination_path"], values["status"], values.get("starts_at_ms"), values.get("ends_at_ms"), now_ms(), link_id),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def clone_link(self, link_id: str, changes: dict[str, Any], *, actor_user_id: str) -> dict[str, Any]:
        source = self._one("SELECT * FROM promotion_links WHERE link_id=%s", (link_id,))
        if not source:
            raise LookupError("promotion_link_not_found")
        values = {
            "content_name": changes.get("content_name") or f"{source['content_name']}（副本）",
            "channel_id": changes.get("channel_id") or source["channel_id"],
            "campaign_id": changes.get("campaign_id") if "campaign_id" in changes else source["campaign_id"],
            "destination_path": source["destination_path"],
            "starts_at_ms": source["starts_at_ms"],
            "ends_at_ms": source["ends_at_ms"],
        }
        return self.create_link(values, actor_user_id=actor_user_id, cloned_from_link_id=link_id)

    def resolve_active_link(self, slug: str, *, at_ms: int) -> dict[str, Any] | None:
        row = self.link_by_slug(slug)
        if not row or row["status"] != "active" or row["channel_status"] != "active":
            return None
        if row["campaign_id"] and row["campaign_status"] != "active":
            return None
        if row["starts_at_ms"] is not None and int(row["starts_at_ms"]) > at_ms:
            return None
        if row["ends_at_ms"] is not None and int(row["ends_at_ms"]) <= at_ms:
            return None
        return row

    def record_touchpoint(self, event: dict[str, Any]) -> bool:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO promotion_touchpoints
                   (touchpoint_id,event_id,event_type,link_id,visitor_hmac,click_hmac,occurred_at_ms,destination_key,
                    referrer_host,device_class,qualification_state,exclusion_reason,created_at_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (event_id) DO NOTHING RETURNING touchpoint_id""",
                (f"promotion-touch-{uuid4().hex}", event["event_id"], event["event_type"], event["link_id"], event.get("visitor_hmac"), event.get("click_hmac"), event["occurred_at_ms"], event["destination_key"], event.get("referrer_host"), event.get("device_class"), event["qualification_state"], event.get("exclusion_reason"), now_ms()),
            )
            inserted = cursor.fetchone() is not None
            if inserted and event["event_type"] == "qualified_visit" and event["qualification_state"] == "qualified":
                cursor.execute(
                    "UPDATE promotion_links SET attribution_locked_at_ms=COALESCE(attribution_locked_at_ms,%s) WHERE link_id=%s",
                    (event["occurred_at_ms"], event["link_id"]),
                )
            connection.commit()
        return inserted

    def claim_identity(self, *, claim_key: str, visitor_hmac: str, user_id: str) -> dict[str, Any]:
        current = now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (f"promotion-claim:{user_id}",))
            cursor.execute("SELECT * FROM promotion_identity_bindings WHERE claim_key=%s", (claim_key,))
            replay = cursor.fetchone()
            if replay:
                if replay["user_id"] != user_id:
                    raise PermissionError("promotion_claim_key_conflict")
                return {**dict(replay), "idempotent_replay": True}
            cursor.execute("SELECT created_at_ms FROM auth_users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise LookupError("promotion_claim_user_not_found")
            registered_at = int(user["created_at_ms"])
            registration_grace_ms = 10 * 60_000
            acquisition_cutoff = min(current, registered_at + registration_grace_ms)
            is_registration_claim = current <= registered_at + registration_grace_ms
            window_start = acquisition_cutoff - self.settings.promotion_attribution_window_days * 86_400_000
            cursor.execute(
                """SELECT touchpoint_id,link_id FROM promotion_touchpoints
                   WHERE visitor_hmac=%s AND event_type='qualified_visit' AND qualification_state='qualified'
                     AND occurred_at_ms >= %s AND occurred_at_ms <= %s AND %s
                   ORDER BY occurred_at_ms ASC LIMIT 1""",
                (visitor_hmac, window_start, acquisition_cutoff, is_registration_claim),
            )
            first = cursor.fetchone()
            cursor.execute(
                """SELECT touchpoint_id,link_id FROM promotion_touchpoints
                   WHERE visitor_hmac=%s AND event_type='qualified_visit' AND qualification_state='qualified'
                     AND occurred_at_ms >= %s AND occurred_at_ms <= %s AND %s
                   ORDER BY occurred_at_ms DESC LIMIT 1""",
                (visitor_hmac, window_start, acquisition_cutoff, is_registration_claim),
            )
            last = cursor.fetchone()
            cursor.execute("SELECT * FROM promotion_identity_bindings WHERE user_id=%s AND deleted_at_ms IS NULL FOR UPDATE", (user_id,))
            locked = cursor.fetchone()
            if locked:
                return {**dict(locked), "idempotent_replay": False, "acquisition_already_locked": True}
            binding_id = f"promotion-binding-{uuid4().hex}"
            cursor.execute(
                """INSERT INTO promotion_identity_bindings
                   (identity_binding_id,claim_key,visitor_hmac,user_id,first_touchpoint_id,last_non_direct_touchpoint_id,
                    first_touch_link_id,last_non_direct_link_id,acquisition_locked_at_ms,created_at_ms,updated_at_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                (binding_id, claim_key, visitor_hmac, user_id,
                 first["touchpoint_id"] if first else None, last["touchpoint_id"] if last else None,
                 first["link_id"] if first else None, last["link_id"] if last else None,
                 current, current, current),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return {**row, "idempotent_replay": False}

    def add_cost(self, values: dict[str, Any], *, actor_user_id: str) -> dict[str, Any]:
        columns = {"channel": "channel_id", "campaign": "campaign_id", "link": "link_id"}
        scope_column = columns[values["scope_type"]]
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO promotion_cost_entries
                    (cost_entry_id,scope_type,{scope_column},cost_date,amount_cents,currency,reason,created_by_user_id,created_at_ms)
                    VALUES (%s,%s,%s,%s,%s,'CNY',%s,%s,%s) RETURNING *""",
                (f"promotion-cost-{uuid4().hex}", values["scope_type"], values["scope_id"], values["cost_date"], values["amount_cents"], values["reason"], actor_user_id, now_ms()),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def record_conversion(
        self,
        *,
        event_id: str,
        conversion_type: str,
        source_record_id: str,
        visitor_hmac: str | None,
        user_id: str | None,
        occurred_at_ms: int,
        amount_cents: int | None = None,
        currency: str | None = None,
    ) -> bool:
        if conversion_type not in {"download", "registration", "use", "order", "payment"}:
            raise ValueError("invalid_promotion_conversion_type")
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO promotion_conversion_events
                   (conversion_event_id,event_id,conversion_type,source_record_id,visitor_hmac,user_id,
                    amount_cents,currency,occurred_at_ms,created_at_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (conversion_type,source_record_id) DO NOTHING RETURNING conversion_event_id""",
                (f"promotion-conversion-{uuid4().hex}", event_id, conversion_type, source_record_id, visitor_hmac, user_id, amount_cents, currency, occurred_at_ms, now_ms()),
            )
            inserted = cursor.fetchone() is not None
            connection.commit()
        return inserted

    def reverse_cost(self, cost_entry_id: str, *, reason: str, actor_user_id: str) -> dict[str, Any]:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM promotion_cost_entries WHERE cost_entry_id=%s FOR UPDATE", (cost_entry_id,))
            original = cursor.fetchone()
            if not original:
                raise LookupError("promotion_cost_not_found")
            if original["reversal_of_entry_id"] is not None or int(original["amount_cents"]) < 0:
                raise ValueError("promotion_cost_reversal_cannot_be_reversed")
            cursor.execute("SELECT 1 FROM promotion_cost_entries WHERE reversal_of_entry_id=%s", (cost_entry_id,))
            if cursor.fetchone():
                raise ValueError("promotion_cost_already_reversed")
            scope_column = {"channel": "channel_id", "campaign": "campaign_id", "link": "link_id"}[original["scope_type"]]
            cursor.execute(
                f"""INSERT INTO promotion_cost_entries
                    (cost_entry_id,scope_type,{scope_column},cost_date,amount_cents,currency,reason,reversal_of_entry_id,created_by_user_id,created_at_ms)
                    VALUES (%s,%s,%s,%s,%s,'CNY',%s,%s,%s,%s) RETURNING *""",
                (f"promotion-cost-{uuid4().hex}", original["scope_type"], original[scope_column], original["cost_date"], -int(original["amount_cents"]), reason, cost_entry_id, actor_user_id, now_ms()),
            )
            row = dict(cursor.fetchone())
            connection.commit()
        return row

    def overview(self, *, start_ms: int, end_ms: int, model: str) -> dict[str, Any]:
        if model not in ATTRIBUTION_MODELS:
            raise ValueError("unsupported_attribution_model")
        link_field = "first_touch_link_id" if model == "first_touch" else "last_non_direct_link_id"
        observation_end = min(now_ms(), end_ms + self.settings.promotion_attribution_window_days * 86_400_000)
        row = self._one(
            f"""WITH cohort AS (
                 SELECT DISTINCT ON (t.visitor_hmac) t.visitor_hmac,t.link_id,t.occurred_at_ms
                 FROM promotion_touchpoints t
                 WHERE t.event_type='qualified_visit' AND t.qualification_state='qualified'
                   AND t.occurred_at_ms >= %s AND t.occurred_at_ms < %s AND t.visitor_hmac IS NOT NULL
                 ORDER BY t.visitor_hmac,t.occurred_at_ms
               ), attributed_users AS (
                 SELECT DISTINCT b.user_id,b.visitor_hmac,l.link_id
                 FROM promotion_identity_bindings b JOIN promotion_links l ON l.link_id=b.{link_field}
                 JOIN auth_users u ON u.user_id=b.user_id
                 WHERE b.user_id IS NOT NULL AND b.deleted_at_ms IS NULL AND b.visitor_hmac IN (SELECT visitor_hmac FROM cohort)
                   AND u.created_at_ms >= %s AND u.created_at_ms < %s
               ), paid AS (
                 SELECT o.order_id,o.user_id,o.amount_cents FROM billing_checkout_orders o
                 WHERE o.status='paid' AND o.user_id IN (SELECT user_id FROM attributed_users)
                   AND o.paid_at_ms >= %s AND o.paid_at_ms < %s
               ), costs AS (
                 SELECT SUM(amount_cents) AS amount_cents, COUNT(*) FILTER (WHERE amount_cents > 0) AS entries
                 FROM promotion_cost_entries WHERE cost_date >= %s AND cost_date < %s
               ) SELECT
                 (SELECT COUNT(*) FROM promotion_touchpoints WHERE event_type='qualified_visit' AND qualification_state='qualified' AND occurred_at_ms >= %s AND occurred_at_ms < %s) AS qualified_visits,
                 (SELECT COUNT(*) FROM cohort) AS unique_visitors,
                 (SELECT COUNT(DISTINCT user_id) FROM attributed_users) AS registrations,
                 (SELECT COUNT(DISTINCT COALESCE(e.user_id::text,e.visitor_hmac)) FROM promotion_conversion_events e
                   WHERE e.conversion_type='download' AND e.occurred_at_ms >= %s AND e.occurred_at_ms < %s
                     AND (e.user_id IN (SELECT user_id FROM attributed_users) OR e.visitor_hmac IN (SELECT visitor_hmac FROM cohort))) AS downloads,
                 (SELECT COUNT(DISTINCT i.owner_user_id) FROM interview_sessions i WHERE i.owner_user_id IN (SELECT user_id FROM attributed_users)
                   AND i.started_at_ms >= %s AND i.started_at_ms < %s) AS activated_users,
                 (SELECT COUNT(*) FROM billing_checkout_orders o WHERE o.user_id IN (SELECT user_id FROM attributed_users)
                   AND o.created_at_ms >= %s AND o.created_at_ms < %s) AS orders,
                 (SELECT COUNT(DISTINCT user_id) FROM paid) AS paying_users,
                 (SELECT COUNT(*) FROM paid) AS paid_orders,
                 (SELECT COALESCE(SUM(amount_cents),0) FROM paid) AS revenue_cents,
                 (SELECT amount_cents FROM costs) AS cost_cents,
                 (SELECT entries FROM costs) AS cost_entries,
                 (SELECT COUNT(*) FROM promotion_touchpoints WHERE qualification_state='excluded' AND occurred_at_ms >= %s AND occurred_at_ms < %s) AS excluded_bots""",
            (start_ms, end_ms, start_ms, observation_end, start_ms, observation_end,
             self._date_for_ms(start_ms), self._date_for_ms(end_ms - 1) + timedelta(days=1),
             start_ms, end_ms, start_ms, observation_end, start_ms, observation_end,
             start_ms, observation_end, start_ms, end_ms),
        ) or {}
        visits = int(row.get("unique_visitors") or 0)
        registrations = int(row.get("registrations") or 0)
        activated = int(row.get("activated_users") or 0)
        payers = int(row.get("paying_users") or 0)
        revenue = int(row.get("revenue_cents") or 0)
        costs = int(row["cost_cents"]) if row.get("cost_entries") else None
        return {
            "qualifiedVisits": int(row.get("qualified_visits") or 0),
            "uniqueVisitors": visits,
            "registrations": registrations,
            "downloads": int(row.get("downloads") or 0),
            "activatedUsers": activated,
            "orders": int(row.get("orders") or 0),
            "payingUsers": payers,
            "paidOrders": int(row.get("paid_orders") or 0),
            "revenueCents": revenue,
            "registrationRate": rate(registrations, visits),
            "activationRate": rate(activated, registrations),
            "paymentRate": rate(payers, registrations),
            "excludedBots": int(row.get("excluded_bots") or 0),
            **cost_metrics(cost_cents=costs, revenue_cents=revenue, paying_users=payers),
        }

    def dimension_report(self, *, start_ms: int, end_ms: int, model: str, dimension: str) -> list[dict[str, Any]]:
        if model not in ATTRIBUTION_MODELS or dimension not in {"channel", "campaign", "link"}:
            raise ValueError("unsupported_promotion_report")
        id_expr = {"channel": "ch.channel_id", "campaign": "COALESCE(c.campaign_id,'unassigned')", "link": "l.link_id"}[dimension]
        name_expr = {"channel": "ch.name", "campaign": "COALESCE(c.name,'未归属活动')", "link": "l.content_name"}[dimension]
        observation_end = min(now_ms(), end_ms + self.settings.promotion_attribution_window_days * 86_400_000)
        rows = self._all(
            f"""WITH dimensions AS (
                  SELECT {id_expr} AS dimension_id,{name_expr} AS dimension_name,l.link_id
                  FROM promotion_links l JOIN promotion_channels ch ON ch.channel_id=l.channel_id
                  LEFT JOIN promotion_campaigns c ON c.campaign_id=l.campaign_id
                ), visits AS (
                  SELECT d.dimension_id,d.dimension_name,
                    COUNT(*) FILTER (WHERE t.event_type='qualified_visit' AND t.qualification_state='qualified') AS qualified_visits,
                    COUNT(DISTINCT t.visitor_hmac) FILTER (WHERE t.event_type='qualified_visit' AND t.qualification_state='qualified') AS unique_visitors
                  FROM dimensions d LEFT JOIN promotion_touchpoints t ON t.link_id=d.link_id AND t.occurred_at_ms >= %s AND t.occurred_at_ms < %s
                  GROUP BY d.dimension_id,d.dimension_name
                ), conversions AS (
                  SELECT d.dimension_id,
                    COUNT(*) FILTER (WHERE f.conversion_type='registration') AS registrations,
                    COUNT(*) FILTER (WHERE f.conversion_type='download') AS downloads,
                    COUNT(*) FILTER (WHERE f.conversion_type='use') AS activated_users,
                    COUNT(*) FILTER (WHERE f.conversion_type='order') AS orders,
                    COUNT(*) FILTER (WHERE f.conversion_type='payment') AS paid_orders,
                    COUNT(DISTINCT o.user_id) FILTER (WHERE f.conversion_type='payment') AS paying_users,
                    COALESCE(SUM(f.amount_cents) FILTER (WHERE f.conversion_type='payment'),0) AS revenue_cents
                  FROM dimensions d LEFT JOIN promotion_attribution_facts f ON f.link_id=d.link_id
                    AND f.attribution_model=%s AND f.model_version=%s AND f.occurred_at_ms >= %s AND f.occurred_at_ms < %s
                  LEFT JOIN billing_checkout_orders o ON o.order_id=f.source_record_id AND f.conversion_type='payment'
                  GROUP BY d.dimension_id
                ) SELECT v.*,COALESCE(c.registrations,0) AS registrations,COALESCE(c.downloads,0) AS downloads,COALESCE(c.activated_users,0) AS activated_users,
                    COALESCE(c.orders,0) AS orders,COALESCE(c.paid_orders,0) AS paid_orders,
                    COALESCE(c.paying_users,0) AS paying_users,COALESCE(c.revenue_cents,0) AS revenue_cents
                  FROM visits v LEFT JOIN conversions c ON c.dimension_id=v.dimension_id
                  ORDER BY v.unique_visitors DESC,v.dimension_name""",
            (start_ms, end_ms, model, self.settings.promotion_model_version, start_ms, observation_end),
        )
        start_date = self._date_for_ms(start_ms)
        end_date = self._date_for_ms(end_ms - 1) + timedelta(days=1)
        if dimension == "link":
            cost_rows = self._all(
                """SELECT link_id AS dimension_id,SUM(amount_cents) AS cost_cents,COUNT(*) FILTER (WHERE amount_cents>0) AS entries
                   FROM promotion_cost_entries WHERE link_id IS NOT NULL AND cost_date >= %s AND cost_date < %s GROUP BY link_id""",
                (start_date, end_date),
            )
        elif dimension == "campaign":
            cost_rows = self._all(
                """SELECT scope.campaign_id AS dimension_id,SUM(scope.amount_cents) AS cost_cents,
                          COUNT(*) FILTER (WHERE scope.amount_cents>0) AS entries
                   FROM (SELECT campaign_id,amount_cents FROM promotion_cost_entries WHERE campaign_id IS NOT NULL AND cost_date >= %s AND cost_date < %s
                         UNION ALL
                         SELECT l.campaign_id,cost.amount_cents FROM promotion_cost_entries cost
                         JOIN promotion_links l ON l.link_id=cost.link_id WHERE l.campaign_id IS NOT NULL AND cost.cost_date >= %s AND cost.cost_date < %s) scope
                   WHERE scope.campaign_id IS NOT NULL GROUP BY scope.campaign_id""",
                (start_date, end_date, start_date, end_date),
            )
        else:
            cost_rows = self._all(
                """SELECT scope.channel_id AS dimension_id,SUM(scope.amount_cents) AS cost_cents,
                          COUNT(*) FILTER (WHERE scope.amount_cents>0) AS entries
                   FROM (SELECT channel_id,amount_cents FROM promotion_cost_entries WHERE channel_id IS NOT NULL AND cost_date >= %s AND cost_date < %s
                         UNION ALL
                         SELECT l.channel_id,cost.amount_cents FROM promotion_cost_entries cost
                         JOIN promotion_links l ON l.link_id=cost.link_id WHERE cost.cost_date >= %s AND cost.cost_date < %s) scope
                   WHERE scope.channel_id IS NOT NULL GROUP BY scope.channel_id""",
                (start_date, end_date, start_date, end_date),
            )
        costs = {str(item["dimension_id"]): item for item in cost_rows}
        output = []
        for row in rows:
            visits = int(row["unique_visitors"] or 0)
            registrations = int(row["registrations"] or 0)
            activated = int(row["activated_users"] or 0)
            payers = int(row["paying_users"] or 0)
            revenue = int(row["revenue_cents"] or 0)
            cost_row = costs.get(str(row["dimension_id"]))
            entered_cost = int(cost_row["cost_cents"]) if cost_row and int(cost_row["entries"] or 0) else None
            output.append({
                **row,
                "qualified_visits": int(row["qualified_visits"] or 0),
                "unique_visitors": visits,
                "registration_rate": rate(registrations, visits),
                "activation_rate": rate(activated, registrations),
                "payment_rate": rate(payers, registrations),
                **cost_metrics(cost_cents=entered_cost, revenue_cents=revenue, paying_users=payers),
            })
        if dimension == "channel":
            bucket_metrics = {str(item["bucket"]): item for item in self.attribution_buckets(start_ms=start_ms, end_ms=observation_end, model=model)}
            for channel in self.list_channels(include_inactive=True):
                code = str(channel["code"])
                if not channel["is_system"] or code == "promoted":
                    continue
                item = bucket_metrics.get(code, {})
                registrations = int(item.get("registrations") or 0)
                paid_orders = int(item.get("paid_orders") or 0)
                output.append({
                    "dimension_id": channel["channel_id"],
                    "dimension_name": channel["name"],
                    "qualified_visits": 0,
                    "unique_visitors": 0,
                    "registrations": registrations,
                    "downloads": 0,
                    "activated_users": 0,
                    "orders": int(item.get("orders") or 0),
                    "paid_orders": paid_orders,
                    "paying_users": paid_orders,
                    "revenue_cents": int(item.get("revenue_cents") or 0),
                    "registration_rate": None,
                    "activation_rate": None,
                    "payment_rate": rate(paid_orders, registrations),
                    **cost_metrics(cost_cents=None, revenue_cents=int(item.get("revenue_cents") or 0), paying_users=paid_orders),
                })
        return output

    def attribution_buckets(self, *, start_ms: int, end_ms: int, model: str) -> list[dict[str, Any]]:
        if model not in ATTRIBUTION_MODELS:
            raise ValueError("unsupported_attribution_model")
        return self._all(
            """SELECT COALESCE(bucket_code,'promoted') AS bucket,
                      COUNT(*) FILTER (WHERE conversion_type='registration') AS registrations,
                      COUNT(*) FILTER (WHERE conversion_type='order') AS orders,
                      COUNT(*) FILTER (WHERE conversion_type='payment') AS paid_orders,
                      COALESCE(SUM(amount_cents) FILTER (WHERE conversion_type='payment'),0) AS revenue_cents
               FROM promotion_attribution_facts
               WHERE attribution_model=%s AND model_version=%s AND occurred_at_ms >= %s AND occurred_at_ms < %s
               GROUP BY COALESCE(bucket_code,'promoted') ORDER BY bucket""",
            (model, self.settings.promotion_model_version, start_ms, end_ms),
        )

    def funnel(self, *, start_ms: int, end_ms: int, model: str) -> dict[str, Any]:
        if model not in ATTRIBUTION_MODELS:
            raise ValueError("unsupported_attribution_model")
        link_field = "first_touch_link_id" if model == "first_touch" else "last_non_direct_link_id"
        mature_at = end_ms + self.settings.promotion_attribution_window_days * 86_400_000
        observation_end = min(now_ms(), mature_at)
        counts = self._one(
            f"""WITH cohort AS (
                  SELECT DISTINCT visitor_hmac FROM promotion_touchpoints
                  WHERE event_type='qualified_visit' AND qualification_state='qualified'
                    AND occurred_at_ms >= %s AND occurred_at_ms < %s AND visitor_hmac IS NOT NULL
                ), registered AS (
                  SELECT DISTINCT b.user_id,b.visitor_hmac FROM promotion_identity_bindings b
                  JOIN auth_users u ON u.user_id=b.user_id
                  WHERE b.deleted_at_ms IS NULL AND b.{link_field} IS NOT NULL AND b.visitor_hmac IN (SELECT visitor_hmac FROM cohort)
                    AND u.created_at_ms >= %s AND u.created_at_ms < %s
                ), downloaded AS (
                  SELECT DISTINCT r.user_id,r.visitor_hmac FROM registered r
                  WHERE EXISTS (SELECT 1 FROM promotion_conversion_events e WHERE e.conversion_type='download'
                    AND e.occurred_at_ms >= %s AND e.occurred_at_ms < %s
                    AND (e.user_id=r.user_id OR (e.user_id IS NULL AND e.visitor_hmac=r.visitor_hmac)))
                ), used AS (
                  SELECT DISTINCT d.user_id FROM downloaded d WHERE EXISTS (
                    SELECT 1 FROM interview_sessions i WHERE i.owner_user_id=d.user_id AND i.started_at_ms >= %s AND i.started_at_ms < %s)
                ), ordered AS (
                  SELECT DISTINCT u.user_id FROM used u WHERE EXISTS (
                    SELECT 1 FROM billing_checkout_orders o WHERE o.user_id=u.user_id AND o.created_at_ms >= %s AND o.created_at_ms < %s)
                ), paid AS (
                  SELECT DISTINCT o.user_id FROM ordered o WHERE EXISTS (
                    SELECT 1 FROM billing_checkout_orders p WHERE p.user_id=o.user_id AND p.status='paid' AND p.paid_at_ms >= %s AND p.paid_at_ms < %s)
                ) SELECT (SELECT COUNT(*) FROM cohort) AS visits,(SELECT COUNT(*) FROM registered) AS registrations,
                    (SELECT COUNT(*) FROM downloaded) AS downloads,(SELECT COUNT(*) FROM used) AS uses,
                    (SELECT COUNT(*) FROM ordered) AS orders,(SELECT COUNT(*) FROM paid) AS payments""",
            (start_ms, end_ms, start_ms, observation_end, start_ms, observation_end,
             start_ms, observation_end, start_ms, observation_end, start_ms, observation_end),
        ) or {}
        stages = [
            ("visit", "有效访问", counts.get("visits") or 0),
            ("registration", "注册", counts.get("registrations") or 0),
            ("download", "下载", counts.get("downloads") or 0),
            ("use", "首次使用", counts.get("uses") or 0),
            ("order", "下单", counts.get("orders") or 0),
            ("payment", "支付", counts.get("payments") or 0),
        ]
        base = int(stages[0][2])
        previous = base
        payload = []
        for key, label, count in stages:
            count = int(count)
            payload.append({
                "key": key, "label": label, "count": count,
                "stageRate": rate(count, previous), "cumulativeRate": rate(count, base),
                "dropOff": max(0, previous - count),
            })
            previous = count
        return {
            "stages": payload,
            "buckets": self.attribution_buckets(start_ms=start_ms, end_ms=min(now_ms(), mature_at), model=model),
            "cohortState": "mature" if now_ms() >= mature_at else "observing",
            "maturesAtMs": mature_at,
        }

    def list_costs(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self._all(
            """SELECT cost_entry_id,scope_type,channel_id,campaign_id,link_id,cost_date,amount_cents,currency,
                      reason,reversal_of_entry_id,created_at_ms
               FROM promotion_cost_entries ORDER BY cost_date DESC,created_at_ms DESC LIMIT %s OFFSET %s""",
            (limit, offset),
        )

    def snapshot_trend(self, *, start_ms: int, end_ms: int, model: str, dimension_type: str = "overview", dimension_id: str = "all") -> list[dict[str, Any]]:
        return self._all(
            """SELECT bucket_date,metrics_json,coverage_json,computed_at_ms
               FROM promotion_metric_snapshots
               WHERE attribution_model=%s AND model_version=%s AND dimension_type=%s AND dimension_id=%s
                 AND bucket_date >= %s AND bucket_date < %s
               ORDER BY bucket_date""",
            (model, self.settings.promotion_model_version, dimension_type, dimension_id, self._date_for_ms(start_ms), self._date_for_ms(end_ms - 1) + timedelta(days=1)),
        )

    def cleanup_user(self, user_id: str) -> None:
        with self.connect() as connection, connection.cursor() as cursor:
            current = now_ms()
            cursor.execute(
                """UPDATE promotion_identity_bindings SET user_id=NULL,visitor_hmac='deleted:' || identity_binding_id,
                   first_touchpoint_id=NULL,last_non_direct_touchpoint_id=NULL,first_touch_link_id=NULL,last_non_direct_link_id=NULL,
                   deleted_at_ms=%s,updated_at_ms=%s WHERE user_id=%s""",
                (current, current, user_id),
            )
            cursor.execute("UPDATE promotion_conversion_events SET user_id=NULL,visitor_hmac=NULL WHERE user_id=%s", (user_id,))
            connection.commit()

    def health(self) -> dict[str, Any]:
        row = self._one("SELECT status,completed_at_ms,mismatch_count,safe_error_code FROM promotion_analytics_runs ORDER BY started_at_ms DESC LIMIT 1", ())
        quality = self._one(
            """SELECT
                (SELECT MAX(computed_at_ms) FROM promotion_metric_snapshots) AS snapshot_fresh_at_ms,
                (SELECT COUNT(*) FROM promotion_identity_bindings WHERE user_id IS NOT NULL AND deleted_at_ms IS NULL) AS matched_identities,
                (SELECT COUNT(*) FROM promotion_identity_bindings WHERE first_touchpoint_id IS NULL AND last_non_direct_touchpoint_id IS NULL AND deleted_at_ms IS NULL) AS unmatched_identities,
                (SELECT COUNT(*) FROM promotion_attribution_facts WHERE bucket_code='unattributed') AS unattributed_facts""",
            (),
        ) or {}
        return {"latestRun": row, "collectionEnabled": self.settings.promotion_enabled, **quality}

    def _date_for_ms(self, value: int) -> date:
        return datetime.fromtimestamp(value / 1000, tz=ZoneInfo(self.settings.promotion_reporting_timezone)).date()


class PromotionEventQueue:
    """Best-effort bounded producer. It intentionally never raises into a product response."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        if self.settings.redis_url:
            import redis

            self._client = redis.Redis.from_url(
                self.settings.redis_url,
                socket_timeout=max(0.005, self.settings.promotion_queue_timeout_ms / 1000),
                socket_connect_timeout=max(0.005, self.settings.promotion_queue_timeout_ms / 1000),
                decode_responses=True,
            )

    def publish(self, payload: dict[str, Any]) -> bool:
        if not self.settings.redis_url:
            with _queue_counter_lock:
                _queue_counters["dropped"] = int(_queue_counters["dropped"] or 0) + 1
                _queue_counters["lastErrorCode"] = "redis_not_configured"
            return False
        try:
            assert self._client is not None
            self._client.xadd(
                self.settings.promotion_redis_stream,
                {"payload": json.dumps(payload, separators=(",", ":"), ensure_ascii=True)},
                maxlen=self.settings.promotion_redis_stream_maxlen,
                approximate=True,
            )
            with _queue_counter_lock:
                _queue_counters["accepted"] = int(_queue_counters["accepted"] or 0) + 1
                _queue_counters["lastErrorCode"] = None
            return True
        except Exception as exc:
            with _queue_counter_lock:
                _queue_counters["dropped"] = int(_queue_counters["dropped"] or 0) + 1
                _queue_counters["lastErrorCode"] = type(exc).__name__[:80]
            return False

    def health(self) -> dict[str, Any]:
        with _queue_counter_lock:
            counters = dict(_queue_counters)
        depth: int | None = None
        pending: int | None = None
        state = "disabled" if not self.settings.redis_url else "unavailable"
        if self._client is not None:
            try:
                depth = int(self._client.xlen(self.settings.promotion_redis_stream))
                try:
                    pending_info = self._client.xpending(self.settings.promotion_redis_stream, "offersteady-promotion-analytics")
                    pending = int(pending_info.get("pending", 0)) if isinstance(pending_info, dict) else None
                except Exception:
                    pending = 0
                state = "healthy"
            except Exception:
                pass
        return {"state": state, "depth": depth, "pending": pending, **counters}


def hmac_identifier(raw: str, settings: Settings) -> str:
    return hmac.new(settings.promotion_visitor_hmac_secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
