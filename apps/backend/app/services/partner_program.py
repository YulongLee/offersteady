from __future__ import annotations

import base64
import hashlib
import secrets
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import BoundedSemaphore
from time import time
from typing import Any, Iterator
from uuid import uuid4
from zoneinfo import ZoneInfo

import psycopg
from cryptography.fernet import Fernet, InvalidToken
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings
from app.services.postgres_migrations import apply_sql_migrations


def now_ms() -> int:
    return int(time() * 1000)


def commission_cents(gross_cents: int, rate_bps: int) -> int:
    if gross_cents < 0 or not 0 < rate_bps <= 10_000:
        raise ValueError("invalid_commission_basis")
    return gross_cents * rate_bps // 10_000


def mask_account_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("payout_account_name_required")
    return value[0] + "*" * max(1, len(value) - 1)


def mask_account_identifier(value: str) -> str:
    value = value.strip()
    if len(value) < 4:
        return "*" * len(value)
    return f"{'*' * min(8, len(value) - 4)}{value[-4:]}"


class PartnerPayoutCipher:
    """Dedicated envelope for payout PII; never reuse the admin-session secret."""

    def __init__(self, settings: Settings) -> None:
        raw = (settings.partner_payout_encryption_key or "").encode()
        if len(raw) < 32:
            raise RuntimeError("partner_payout_encryption_key_missing")
        key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.strip().encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("partner_payout_profile_decryption_failed") from exc


def refund_adjustment(
    *,
    original_gross_cents: int,
    original_commission_cents: int,
    refunded_gross_cents: int,
    reversed_commission_cents: int,
    requested_refund_cents: int,
    rate_bps: int,
) -> tuple[int, int]:
    """Return capped gross and negative commission for one append-only refund entry."""
    remaining_gross = original_gross_cents - refunded_gross_cents
    remaining_commission = original_commission_cents + reversed_commission_cents
    if remaining_gross <= 0 or remaining_commission <= 0:
        raise ValueError("partner_earning_already_fully_reversed")
    adjusted_gross = min(remaining_gross, requested_refund_cents)
    reversal = -remaining_commission if adjusted_gross == remaining_gross else -min(
        remaining_commission,
        commission_cents(adjusted_gross, rate_bps),
    )
    if reversal == 0:
        raise ValueError("refund_below_commission_precision")
    return adjusted_gross, reversal


class PartnerProgramRepository:
    """PostgreSQL control-plane repository; never called by interview or payment hot paths."""

    def __init__(self, settings: Settings, *, migrate: bool = True) -> None:
        self.settings = settings
        if not settings.database_url:
            raise RuntimeError("partner_database_required")
        if settings.partner_payout_profile_enabled:
            PartnerPayoutCipher(settings)
        self._query_budget = BoundedSemaphore(max(1, settings.admin_max_concurrent_queries))
        if migrate:
            self.ensure_schema()

    @contextmanager
    def connect(self, *, readonly: bool = False) -> Iterator[psycopg.Connection]:
        acquired = self._query_budget.acquire(timeout=max(0.05, self.settings.admin_query_timeout_ms / 1000))
        if not acquired:
            raise TimeoutError("partner_database_budget_exhausted")
        try:
            with psycopg.connect(
                self.settings.database_url,
                connect_timeout=self.settings.database_connect_timeout_seconds,
                application_name=f"{self.settings.database_application_name}-partner",
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
        migrations = [
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0038_promotion_center.sql",
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0039_partner_program.sql",
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0040_partner_payout_operations.sql",
            Path(REPO_ROOT) / "apps/backend/migrations/versions/0042_partner_program_activity_settings.sql",
        ]
        with self.connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, migrations)
            connection.commit()

    def activity_settings(self) -> dict[str, Any]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT enabled,config_version,updated_by_user_id,updated_at_ms
                   FROM partner_program_settings WHERE settings_id='default'"""
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("partner_program_settings_missing")
            return dict(row)

    def update_activity_settings(
        self,
        *,
        enabled: bool,
        updated_by_user_id: str,
        updated_at_ms: int | None = None,
    ) -> dict[str, Any]:
        current = updated_at_ms or now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """UPDATE partner_program_settings
                   SET enabled=%s,config_version=config_version+1,updated_by_user_id=%s,updated_at_ms=%s
                   WHERE settings_id='default'
                   RETURNING enabled,config_version,updated_by_user_id,updated_at_ms""",
                (enabled, updated_by_user_id, current),
            )
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("partner_program_settings_missing")
            connection.commit()
            return dict(row)

    def payout_profile(self, *, user_id: str) -> dict[str, Any] | None:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT payout_profile_id,version,payout_method,masked_account_name,masked_account_identifier,
                          key_version,status,created_at_ms,updated_at_ms
                   FROM partner_payout_profiles WHERE partner_user_id=%s AND status='current'""",
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_payout_profile(self, *, user_id: str, payout_method: str, account_name: str,
                            account_identifier: str, saved_at_ms: int | None = None) -> dict[str, Any]:
        if not self.settings.partner_payout_profile_enabled:
            raise RuntimeError("partner_payout_profile_disabled")
        if payout_method not in {"alipay", "wechat"}:
            raise ValueError("invalid_payout_method")
        name = account_name.strip()
        identifier = account_identifier.strip()
        if not 2 <= len(name) <= 80 or not 4 <= len(identifier) <= 160:
            raise ValueError("invalid_payout_profile")
        cipher = PartnerPayoutCipher(self.settings)
        current = saved_at_ms or now_ms()
        retention_until = current + self.settings.partner_payout_retention_days * 86_400_000
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"partner-payout-profile:{user_id}",))
            cursor.execute("SELECT status FROM partner_profiles WHERE user_id=%s FOR SHARE", (user_id,))
            partner = cursor.fetchone()
            if not partner or partner["status"] != "active":
                raise PermissionError("partner_not_active")
            cursor.execute("SELECT COALESCE(MAX(version),0)+1 AS version FROM partner_payout_profiles WHERE partner_user_id=%s", (user_id,))
            version = int(cursor.fetchone()["version"])
            cursor.execute("UPDATE partner_payout_profiles SET status='superseded',updated_at_ms=%s WHERE partner_user_id=%s AND status='current'", (current, user_id))
            profile_id = f"partner-payout-profile-{uuid4().hex}"
            cursor.execute(
                """INSERT INTO partner_payout_profiles
                   (payout_profile_id,partner_user_id,version,payout_method,account_name_ciphertext,
                    account_identifier_ciphertext,masked_account_name,masked_account_identifier,key_version,status,
                    retention_until_ms,created_at_ms,updated_at_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'current',%s,%s,%s)
                   RETURNING payout_profile_id,version,payout_method,masked_account_name,masked_account_identifier,
                             key_version,status,created_at_ms,updated_at_ms""",
                (profile_id, user_id, version, payout_method, cipher.encrypt(name), cipher.encrypt(identifier),
                 mask_account_name(name), mask_account_identifier(identifier), self.settings.partner_payout_key_version,
                 retention_until, current, current),
            )
            row = dict(cursor.fetchone())
            connection.commit()
            return row

    def reveal_payout_profile(self, *, payout_request_id: str) -> dict[str, Any]:
        cipher = PartnerPayoutCipher(self.settings)
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT r.payout_request_id,r.status,p.payout_method,p.account_name_ciphertext,
                          p.account_identifier_ciphertext,p.version,p.key_version
                   FROM partner_payout_requests r JOIN partner_payout_profiles p ON p.payout_profile_id=r.payout_profile_id
                   WHERE r.payout_request_id=%s""",
                (payout_request_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise LookupError("partner_payout_profile_not_found")
            return {
                "payout_request_id": row["payout_request_id"], "status": row["status"],
                "payout_method": row["payout_method"], "account_name": cipher.decrypt(row["account_name_ciphertext"]),
                "account_identifier": cipher.decrypt(row["account_identifier_ciphertext"]),
                "profile_version": row["version"], "key_version": row["key_version"],
            }

    def _slug(self) -> str:
        return secrets.token_urlsafe(12).replace("-", "").replace("_", "")[:16]

    def join(self, *, user_id: str, agreement_version: str, joined_at_ms: int | None = None) -> dict[str, Any]:
        current = joined_at_ms or now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT enabled FROM partner_program_settings WHERE settings_id='default' FOR SHARE")
            activity = cursor.fetchone()
            if not activity or not bool(activity["enabled"]):
                raise RuntimeError("partner_program_disabled")
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"partner:{user_id}",))
            cursor.execute(
                """SELECT p.*,l.slug FROM partner_profiles p JOIN promotion_links l ON l.link_id=p.promotion_link_id
                   WHERE p.user_id=%s""",
                (user_id,),
            )
            existing = cursor.fetchone()
            if existing:
                return dict(existing)
            cursor.execute("SELECT 1 FROM auth_users WHERE user_id=%s", (user_id,))
            if not cursor.fetchone():
                raise LookupError("partner_user_not_found")
            link_id = f"promotion-link-{uuid4().hex}"
            for _ in range(5):
                try:
                    slug = self._slug()
                    cursor.execute(
                        """INSERT INTO promotion_links
                           (link_id,slug,content_name,channel_id,campaign_id,destination_path,status,starts_at_ms,ends_at_ms,
                            cloned_from_link_id,created_by_user_id,created_at_ms,updated_at_ms,link_kind,owner_user_id)
                           VALUES (%s,%s,%s,'promotion-channel-partner',NULL,'/','active',NULL,NULL,NULL,%s,%s,%s,'partner',%s)""",
                        (link_id, slug, "合作伙伴专属链接", user_id, current, current, user_id),
                    )
                    break
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
                    cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"partner:{user_id}",))
            else:
                raise RuntimeError("partner_slug_generation_failed")
            profile_id = f"partner-profile-{uuid4().hex}"
            cursor.execute(
                """INSERT INTO partner_profiles
                   (profile_id,user_id,promotion_link_id,status,agreement_version,joined_at_ms,updated_at_ms)
                   VALUES (%s,%s,%s,'active',%s,%s,%s) RETURNING *""",
                (profile_id, user_id, link_id, agreement_version, current, current),
            )
            profile = dict(cursor.fetchone())
            profile["slug"] = slug
            connection.commit()
            return profile

    def profile(self, *, user_id: str) -> dict[str, Any] | None:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT p.*,l.slug FROM partner_profiles p JOIN promotion_links l ON l.link_id=p.promotion_link_id
                   WHERE p.user_id=%s""",
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def dashboard(self, *, user_id: str, at_ms: int | None = None) -> dict[str, Any]:
        current = at_ms or now_ms()
        profile = self.profile(user_id=user_id)
        if not profile:
            raise LookupError("partner_not_joined")
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                     (SELECT COUNT(DISTINCT visitor_hmac) FROM promotion_touchpoints
                       WHERE link_id=%s AND event_type='qualified_visit' AND qualification_state='qualified') AS valid_visitors,
                     (SELECT COUNT(*) FROM growth_acquisition_reward_claims
                       WHERE partner_user_id=%s AND reward_program='cash_partner') AS registrations,
                     (SELECT COUNT(DISTINCT o.user_id) FROM billing_checkout_orders o
                       JOIN growth_acquisition_reward_claims c ON c.acquired_user_id=o.user_id
                       WHERE c.partner_user_id=%s AND c.reward_program='cash_partner' AND o.status='paid') AS paying_users,
                     (SELECT COALESCE(SUM(CASE WHEN entry_type='earning' THEN gross_amount_cents ELSE -gross_amount_cents END),0)
                       FROM partner_commission_ledger WHERE partner_user_id=%s AND entry_type IN ('earning','refund_reversal')) AS attributed_receipts_cents""",
                (profile["promotion_link_id"], user_id, user_id, user_id),
            )
            metrics = dict(cursor.fetchone())
            cursor.execute(
                """SELECT
                     COUNT(*) FILTER (WHERE entry_type='earning' AND eligible_at_ms<=%s) AS eligible_order_count,
                     COUNT(*) FILTER (WHERE entry_type='earning' AND eligible_at_ms>%s) AS pending_order_count,
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('earning','refund_reversal') AND eligible_at_ms>%s),0) AS pending_cents,
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('earning','refund_reversal') AND eligible_at_ms<=%s),0)
                       + COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('payout_reserve','payout_release')),0) AS available_cents,
                     COALESCE(-SUM(amount_cents) FILTER (WHERE entry_type='payout_reserve'),0)
                       - COALESCE(SUM(amount_cents) FILTER (WHERE entry_type='payout_release'),0)
                       - COALESCE(SUM(amount_cents) FILTER (WHERE entry_type='payout_paid'),0) AS reserved_cents,
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type='payout_paid'),0) AS settled_cents,
                     MAX(created_at_ms) AS refreshed_at_ms
                   FROM partner_commission_ledger WHERE partner_user_id=%s""",
                (current, current, user_id),
            )
            balances = dict(cursor.fetchone())
            cursor.execute(
                """SELECT payout_request_id,period_key,amount_cents,status,requested_at_ms,paid_at_ms,updated_at_ms
                   FROM partner_payout_requests WHERE partner_user_id=%s ORDER BY requested_at_ms DESC LIMIT 24""",
                (user_id,),
            )
            payouts = [dict(row) for row in cursor.fetchall()]
        return {
            "profile": profile,
            "payout_profile": self.payout_profile(user_id=user_id) if self.settings.partner_payout_profile_enabled else None,
            "metrics": metrics,
            "balances": balances,
            "payouts": payouts,
        }

    def project_paid_orders(self, *, limit: int | None = None, projected_at_ms: int | None = None) -> dict[str, int]:
        current = projected_at_ms or now_ms()
        batch = min(max(1, limit or self.settings.partner_projection_batch_size), 1000)
        eligible_window_ms = self.settings.partner_eligible_order_days * 86_400_000
        hold_ms = self.settings.partner_refund_hold_days * 86_400_000
        inserted = conflicts = 0
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT o.order_id,o.user_id,o.amount_cents,o.paid_at_ms,u.created_at_ms,l.owner_user_id,l.link_id
                   FROM billing_checkout_orders o
                   JOIN auth_users u ON u.user_id=o.user_id
                   JOIN promotion_identity_bindings b ON b.user_id=o.user_id AND b.deleted_at_ms IS NULL
                   JOIN promotion_links l ON l.link_id=b.last_non_direct_link_id AND l.link_kind='partner'
                   JOIN partner_profiles p ON p.user_id=l.owner_user_id AND p.status='active'
                   WHERE o.status='paid' AND o.paid_at_ms IS NOT NULL
                     AND o.paid_at_ms<=u.created_at_ms+%s AND o.user_id<>l.owner_user_id
                     AND NOT EXISTS (
                       SELECT 1 FROM growth_acquisition_reward_claims x
                       WHERE x.acquired_user_id=o.user_id AND x.reward_program<>'cash_partner'
                     )
                     AND NOT EXISTS (SELECT 1 FROM partner_commission_ledger e WHERE e.entry_type='earning' AND e.source_type='paid_order' AND e.source_id=o.order_id AND e.rule_version=%s)
                   ORDER BY o.paid_at_ms LIMIT %s FOR UPDATE OF o SKIP LOCKED""",
                (eligible_window_ms, self.settings.partner_commission_rule_version, batch),
            )
            rows = cursor.fetchall()
            for row in rows:
                cursor.execute(
                    """INSERT INTO growth_acquisition_reward_claims
                       (acquired_user_id,reward_program,partner_user_id,source_link_id,claimed_at_ms)
                       VALUES (%s,'cash_partner',%s,%s,%s) ON CONFLICT (acquired_user_id) DO NOTHING""",
                    (row["user_id"], row["owner_user_id"], row["link_id"], current),
                )
                cursor.execute(
                    "SELECT reward_program,partner_user_id FROM growth_acquisition_reward_claims WHERE acquired_user_id=%s FOR UPDATE",
                    (row["user_id"],),
                )
                claim = cursor.fetchone()
                if not claim or claim["reward_program"] != "cash_partner" or claim["partner_user_id"] != row["owner_user_id"]:
                    conflicts += 1
                    continue
                amount = commission_cents(int(row["amount_cents"]), self.settings.partner_commission_rate_bps)
                if amount <= 0:
                    continue
                cursor.execute(
                    """INSERT INTO partner_commission_ledger
                       (ledger_entry_id,partner_user_id,entry_type,source_type,source_id,rule_version,amount_cents,
                        gross_amount_cents,commission_rate_bps,hold_days,eligible_at_ms,occurred_at_ms,created_at_ms,metadata_json)
                       VALUES (%s,%s,'earning','paid_order',%s,%s,%s,%s,%s,%s,%s,%s,%s,'{}'::jsonb)
                       ON CONFLICT (entry_type,source_type,source_id,rule_version) DO NOTHING""",
                    (f"partner-ledger-{uuid4().hex}", row["owner_user_id"], row["order_id"],
                     self.settings.partner_commission_rule_version, amount, row["amount_cents"],
                     self.settings.partner_commission_rate_bps, self.settings.partner_refund_hold_days,
                     int(row["paid_at_ms"]) + hold_ms, row["paid_at_ms"], current),
                )
                inserted += cursor.rowcount
            connection.commit()
        return {"scanned": len(rows), "inserted": inserted, "rewardConflicts": conflicts}

    def record_refund(self, *, order_id: str, refund_reference: str, refunded_cents: int, actor_user_id: str, occurred_at_ms: int | None = None) -> dict[str, Any]:
        if refunded_cents <= 0 or not refund_reference.strip():
            raise ValueError("invalid_refund_adjustment")
        current = occurred_at_ms or now_ms()
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM partner_commission_ledger WHERE entry_type='earning' AND source_type='paid_order'
                   AND source_id=%s ORDER BY rule_version DESC LIMIT 1 FOR UPDATE""",
                (order_id,),
            )
            earning = cursor.fetchone()
            if not earning:
                raise LookupError("partner_earning_not_found")
            cursor.execute(
                """SELECT * FROM partner_commission_ledger WHERE entry_type='refund_reversal' AND source_type='refund'
                   AND source_id=%s AND rule_version=%s""",
                (refund_reference, earning["rule_version"]),
            )
            existing = cursor.fetchone()
            if existing:
                if existing["metadata_json"].get("orderId") != order_id:
                    raise ValueError("refund_reference_conflict")
                return dict(existing)
            cursor.execute(
                """SELECT COALESCE(SUM(amount_cents),0) AS reversed_cents,
                          COALESCE(SUM(gross_amount_cents),0) AS refunded_gross_cents
                   FROM partner_commission_ledger
                   WHERE entry_type='refund_reversal' AND metadata_json->>'orderId'=%s AND rule_version=%s""",
                (order_id, earning["rule_version"]),
            )
            reversal_totals = cursor.fetchone()
            adjusted_refund_gross, reversal = refund_adjustment(
                original_gross_cents=int(earning["gross_amount_cents"]),
                original_commission_cents=int(earning["amount_cents"]),
                refunded_gross_cents=int(reversal_totals["refunded_gross_cents"]),
                reversed_commission_cents=int(reversal_totals["reversed_cents"]),
                requested_refund_cents=refunded_cents,
                rate_bps=int(earning["commission_rate_bps"]),
            )
            cursor.execute(
                """INSERT INTO partner_commission_ledger
                   (ledger_entry_id,partner_user_id,entry_type,source_type,source_id,rule_version,amount_cents,
                    gross_amount_cents,commission_rate_bps,hold_days,eligible_at_ms,occurred_at_ms,created_at_ms,metadata_json)
                   VALUES (%s,%s,'refund_reversal','refund',%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           jsonb_build_object('orderId',%s,'actorUserId',%s))
                   ON CONFLICT (entry_type,source_type,source_id,rule_version) DO NOTHING RETURNING *""",
                (f"partner-ledger-{uuid4().hex}", earning["partner_user_id"], refund_reference,
                 earning["rule_version"], reversal, adjusted_refund_gross, earning["commission_rate_bps"],
                 earning["hold_days"], earning["eligible_at_ms"], current, current, order_id, actor_user_id),
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    """SELECT * FROM partner_commission_ledger WHERE entry_type='refund_reversal' AND source_type='refund'
                       AND source_id=%s AND rule_version=%s""",
                    (refund_reference, earning["rule_version"]),
                )
                row = cursor.fetchone()
            connection.commit()
            return dict(row)

    def request_payout(self, *, user_id: str, requested_at_ms: int | None = None) -> dict[str, Any]:
        current = requested_at_ms or now_ms()
        period = datetime.fromtimestamp(current / 1000, ZoneInfo(self.settings.promotion_reporting_timezone)).strftime("%Y-%m")
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"partner-payout:{user_id}",))
            cursor.execute("SELECT status FROM partner_profiles WHERE user_id=%s FOR SHARE", (user_id,))
            profile = cursor.fetchone()
            if not profile or profile["status"] != "active":
                raise PermissionError("partner_not_active")
            payout_profile_id = None
            if self.settings.partner_payout_profile_enabled:
                cursor.execute(
                    "SELECT payout_profile_id FROM partner_payout_profiles WHERE partner_user_id=%s AND status='current' FOR SHARE",
                    (user_id,),
                )
                payout_profile = cursor.fetchone()
                if not payout_profile:
                    raise ValueError("partner_payout_profile_required")
                payout_profile_id = payout_profile["payout_profile_id"]
            cursor.execute("SELECT 1 FROM partner_payout_requests WHERE partner_user_id=%s AND period_key=%s", (user_id, period))
            if cursor.fetchone():
                raise ValueError("partner_monthly_payout_already_requested")
            cursor.execute(
                """SELECT COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('earning','refund_reversal') AND eligible_at_ms<=%s),0)
                          + COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('payout_reserve','payout_release')),0) AS available
                   FROM partner_commission_ledger WHERE partner_user_id=%s""",
                (current, user_id),
            )
            available = int(cursor.fetchone()["available"])
            if available < self.settings.partner_minimum_payout_cents:
                raise ValueError("partner_minimum_payout_not_reached")
            payout_id = f"partner-payout-{uuid4().hex}"
            cursor.execute(
                """INSERT INTO partner_payout_requests
                   (payout_request_id,partner_user_id,period_key,amount_cents,status,payout_profile_id,requested_at_ms,updated_at_ms)
                   VALUES (%s,%s,%s,%s,'requested',%s,%s,%s) RETURNING *""",
                (payout_id, user_id, period, available, payout_profile_id, current, current),
            )
            payout = dict(cursor.fetchone())
            cursor.execute(
                """INSERT INTO partner_commission_ledger
                   (ledger_entry_id,partner_user_id,entry_type,source_type,source_id,rule_version,amount_cents,eligible_at_ms,occurred_at_ms,created_at_ms)
                   VALUES (%s,%s,'payout_reserve','payout',%s,%s,%s,%s,%s,%s)""",
                (f"partner-ledger-{uuid4().hex}", user_id, payout_id,
                 self.settings.partner_commission_rule_version, -available, current, current, current),
            )
            connection.commit()
            return payout

    def list_partners(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT p.profile_id,p.status,p.agreement_version,p.joined_at_ms,p.updated_at_ms,l.slug,
                          COALESCE(SUM(e.amount_cents) FILTER (WHERE e.entry_type IN ('earning','refund_reversal')),0) AS total_commission_cents
                   FROM partner_profiles p JOIN promotion_links l ON l.link_id=p.promotion_link_id
                   LEFT JOIN partner_commission_ledger e ON e.partner_user_id=p.user_id
                   GROUP BY p.profile_id,l.slug ORDER BY p.joined_at_ms DESC LIMIT %s""",
                (min(max(1, limit), 500),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_payouts(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT r.payout_request_id,p.profile_id,l.slug,r.period_key,r.amount_cents,r.status,r.requested_at_ms,
                          r.reviewed_at_ms,r.paid_at_ms,r.payment_reference,r.decision_reason,r.updated_at_ms,
                          pp.payout_method,pp.masked_account_name,pp.masked_account_identifier,pp.version AS payout_profile_version,
                          COALESCE((SELECT -SUM(e.amount_cents) FROM partner_commission_ledger e
                                    WHERE e.source_type='payout' AND e.source_id=r.payout_request_id
                                      AND e.entry_type='payout_reserve'),0) AS reserved_ledger_cents,
                          COALESCE((SELECT SUM(e.amount_cents) FROM partner_commission_ledger e
                                    WHERE e.source_type='payout' AND e.source_id=r.payout_request_id
                                      AND e.entry_type='payout_paid'),0) AS paid_ledger_cents
                   FROM partner_payout_requests r
                   LEFT JOIN partner_profiles p ON p.user_id=r.partner_user_id
                   LEFT JOIN promotion_links l ON l.link_id=p.promotion_link_id
                   LEFT JOIN partner_payout_profiles pp ON pp.payout_profile_id=r.payout_profile_id
                   WHERE (%s::text IS NULL OR r.status=%s::text)
                   ORDER BY r.requested_at_ms DESC LIMIT %s""",
                (status, status, min(max(1, limit), 500)),
            )
            return [dict(row) for row in cursor.fetchall()]

    def reconciliation_summary(self) -> dict[str, int]:
        current = now_ms()
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('earning','refund_reversal') AND eligible_at_ms>%s),0) AS pending_cents,
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('earning','refund_reversal') AND eligible_at_ms<=%s),0) AS eligible_cents,
                     COALESCE(-SUM(amount_cents) FILTER (WHERE entry_type='payout_reserve'),0)
                       - COALESCE(SUM(amount_cents) FILTER (WHERE entry_type IN ('payout_release','payout_paid')),0) AS reserved_cents,
                     COALESCE(SUM(amount_cents) FILTER (WHERE entry_type='payout_paid'),0) AS paid_cents,
                     COALESCE(-SUM(amount_cents) FILTER (WHERE entry_type='refund_reversal'),0) AS reversed_cents
                   FROM partner_commission_ledger""",
                (current, current, current, current),
            )
            result = dict(cursor.fetchone())
            result["available_cents"] = max(0, int(result["eligible_cents"]) - int(result["reserved_cents"]) - int(result["paid_cents"]))
            result["negative_carry_cents"] = max(0, -(int(result["eligible_cents"]) - int(result["reserved_cents"]) - int(result["paid_cents"])))
            return result

    def list_commission_orders(self, *, state: str | None = None, start_ms: int | None = None,
                               end_ms: int | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        current = now_ms()
        bounded_limit = min(max(1, limit), 200)
        bounded_offset = min(max(0, offset), 10_000)
        if state not in {None, "pending", "eligible", "reversed"}:
            raise ValueError("invalid_partner_commission_state")
        with self.connect(readonly=True) as connection, connection.cursor() as cursor:
            cursor.execute(
                """SELECT e.ledger_entry_id,e.source_id AS order_id,l.slug AS partner_slug,e.gross_amount_cents,
                          e.gross_amount_cents-COALESCE((SELECT SUM(r.gross_amount_cents) FROM partner_commission_ledger r
                                    WHERE r.entry_type='refund_reversal' AND r.metadata_json->>'orderId'=e.source_id),0) AS net_receipt_cents,
                          e.amount_cents,e.amount_cents-COALESCE((SELECT -SUM(r.amount_cents) FROM partner_commission_ledger r
                                    WHERE r.entry_type='refund_reversal' AND r.metadata_json->>'orderId'=e.source_id),0) AS net_commission_cents,
                          e.commission_rate_bps,e.hold_days,e.eligible_at_ms,e.occurred_at_ms,
                          COALESCE((SELECT -SUM(r.amount_cents) FROM partner_commission_ledger r
                                    WHERE r.entry_type='refund_reversal' AND r.metadata_json->>'orderId'=e.source_id),0) AS reversed_cents,
                          CASE WHEN EXISTS (SELECT 1 FROM partner_commission_ledger r WHERE r.entry_type='refund_reversal'
                                             AND r.metadata_json->>'orderId'=e.source_id) THEN 'reversed'
                               WHEN e.eligible_at_ms>%s THEN 'pending' ELSE 'eligible' END AS state
                   FROM partner_commission_ledger e
                   LEFT JOIN partner_profiles p ON p.user_id=e.partner_user_id
                   LEFT JOIN promotion_links l ON l.link_id=p.promotion_link_id
                   WHERE e.entry_type='earning' AND e.source_type='paid_order'
                     AND (%s::bigint IS NULL OR e.occurred_at_ms >= %s::bigint)
                     AND (%s::bigint IS NULL OR e.occurred_at_ms < %s::bigint)
                     AND (%s::text IS NULL OR (%s='pending' AND e.eligible_at_ms>%s)
                          OR (%s='eligible' AND e.eligible_at_ms<=%s)
                          OR (%s='reversed' AND EXISTS (SELECT 1 FROM partner_commission_ledger r
                              WHERE r.entry_type='refund_reversal' AND r.metadata_json->>'orderId'=e.source_id)))
                   ORDER BY e.occurred_at_ms DESC LIMIT %s OFFSET %s""",
                (current, start_ms, start_ms, end_ms, end_ms, state, state, current, state, current, state,
                 bounded_limit, bounded_offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def transition_payout(self, *, payout_request_id: str, target_status: str, actor_user_id: str, reason: str, payment_reference: str | None = None, transitioned_at_ms: int | None = None) -> dict[str, Any]:
        current = transitioned_at_ms or now_ms()
        allowed = {"requested": {"approved", "rejected"}, "approved": {"paid", "rejected"}}
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM partner_payout_requests WHERE payout_request_id=%s FOR UPDATE", (payout_request_id,))
            payout = cursor.fetchone()
            if not payout:
                raise LookupError("partner_payout_not_found")
            if target_status not in allowed.get(str(payout["status"]), set()):
                raise ValueError("invalid_partner_payout_transition")
            if target_status == "paid" and not (payment_reference or "").strip():
                raise ValueError("payment_reference_required")
            cursor.execute(
                """UPDATE partner_payout_requests SET status=%s,reviewed_at_ms=%s,reviewed_by_user_id=%s,
                   paid_at_ms=CASE WHEN %s='paid' THEN %s ELSE paid_at_ms END,payment_reference=COALESCE(%s,payment_reference),
                   decision_reason=%s,updated_at_ms=%s WHERE payout_request_id=%s RETURNING *""",
                (target_status, current, actor_user_id, target_status, current, payment_reference, reason, current, payout_request_id),
            )
            updated = dict(cursor.fetchone())
            updated["previous_status"] = str(payout["status"])
            if target_status in {"rejected", "paid"}:
                entry_type = "payout_release" if target_status == "rejected" else "payout_paid"
                cursor.execute(
                    """INSERT INTO partner_commission_ledger
                       (ledger_entry_id,partner_user_id,entry_type,source_type,source_id,rule_version,amount_cents,eligible_at_ms,occurred_at_ms,created_at_ms)
                       VALUES (%s,%s,%s,'payout',%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (entry_type,source_type,source_id,rule_version) DO NOTHING""",
                    (f"partner-ledger-{uuid4().hex}", payout["partner_user_id"], entry_type, payout_request_id,
                     self.settings.partner_commission_rule_version, payout["amount_cents"], current, current, current),
                )
            connection.commit()
            return updated
