from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from time import time

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings
from app.ports.global_commerce import FairUseDecision, GlobalEntitlement, GlobalOrder, GlobalPlan, GlobalProductMapping, GlobalSubscription, UsageKind, UsageReservation
from app.services.postgres_migrations import apply_sql_migrations


class PostgresGlobalCommerceRepository:
    def __init__(self, settings: Settings) -> None:
        if settings.product_edition != "global":
            raise RuntimeError("Global commerce repository is disabled outside the Global edition")
        if not settings.database_url:
            raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for persistent Global commerce")
        self.settings = settings
        self._transaction_connection: ContextVar[psycopg.Connection | None] = ContextVar("global_commerce_transaction", default=None)
        self._ensure_tables()

    @contextmanager
    def transaction(self):
        if self._transaction_connection.get() is not None:
            yield
            return
        with psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-global-commerce-transaction") as connection:
            token = self._transaction_connection.set(connection)
            try:
                yield
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                self._transaction_connection.reset(token)

    def active_plans(self) -> list[GlobalPlan]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_plan_versions WHERE status='active' ORDER BY display_order, offer_code")
            return [self._plan(row) for row in cursor.fetchall()]

    def plan(self, offer_code: str, version: int | None = None) -> GlobalPlan | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            if version is None:
                cursor.execute("SELECT * FROM global_commerce_plan_versions WHERE offer_code=%s AND status='active'", (offer_code,))
            else:
                cursor.execute("SELECT * FROM global_commerce_plan_versions WHERE offer_code=%s AND plan_version=%s", (offer_code, version))
            row = cursor.fetchone()
            return self._plan(row) if row else None

    def save_draft(self, plan: GlobalPlan) -> GlobalPlan:
        if plan.status != "draft":
            raise ValueError("new plan versions must begin as draft")
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    """INSERT INTO global_commerce_plan_versions (
                      offer_code,plan_version,display_name,description,currency,price_cents,billing_mode,duration_days,
                      copilot_minutes,screen_assist_uses,knowledge_tokens,resume_jd_enabled,knowledge_base_enabled,written_exam_enabled,
                      full_product_enabled,status,featured,display_order,created_at_ms
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'draft',%s,%s,%s)""",
                    (plan.offer_code, plan.version, plan.display_name, plan.description, plan.currency, plan.price_cents,
                     plan.billing_mode, plan.duration_days, plan.copilot_minutes, plan.screen_assist_uses, plan.knowledge_tokens,
                     plan.resume_jd_enabled, plan.knowledge_base_enabled, plan.written_exam_enabled,
                     plan.full_product_enabled, plan.featured, plan.display_order, plan.created_at_ms),
                )
                connection.commit()
            except psycopg.IntegrityError as exc:
                raise ValueError("plan version already exists or is invalid") from exc
        return plan

    def publish(self, offer_code: str, version: int) -> GlobalPlan:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_plan_versions WHERE offer_code=%s AND plan_version=%s FOR UPDATE", (offer_code, version))
            row = cursor.fetchone()
            if not row or row["status"] != "draft":
                raise ValueError("publish target must be an existing draft")
            cursor.execute("UPDATE global_commerce_plan_versions SET status='retired' WHERE offer_code=%s AND status='active'", (offer_code,))
            cursor.execute("UPDATE global_commerce_plan_versions SET status='active' WHERE offer_code=%s AND plan_version=%s RETURNING *", (offer_code, version))
            published = self._plan(cursor.fetchone())
            connection.commit()
            return published

    def entitlements_for_user(self, user_id: str) -> list[GlobalEntitlement]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_entitlements WHERE user_id=%s ORDER BY starts_at_ms DESC", (user_id,))
            return [self._entitlement(row) for row in cursor.fetchall()]

    def grant_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """INSERT INTO global_commerce_entitlements (
                  entitlement_id,user_id,offer_code,plan_version,source_kind,source_id,status,starts_at_ms,ends_at_ms,
                  copilot_minutes_granted,copilot_minutes_used,copilot_minutes_locked,screen_assist_uses_granted,
                  screen_assist_uses_used,screen_assist_uses_locked,resume_jd_enabled,knowledge_base_enabled,
                  written_exam_enabled,full_product_enabled,knowledge_tokens_granted,knowledge_tokens_used,knowledge_tokens_locked,created_at_ms,updated_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source_kind,source_id) DO UPDATE SET source_id=EXCLUDED.source_id RETURNING *""",
                self._entitlement_values(entitlement),
            )
            stored = self._entitlement(cursor.fetchone())
            connection.commit()
            return stored

    def initial_free_grant(self, user_id: str) -> GlobalEntitlement | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""SELECT e.* FROM global_commerce_free_grants g JOIN global_commerce_entitlements e ON e.entitlement_id=g.entitlement_id WHERE g.user_id=%s AND g.grant_kind='initial'""", (user_id,))
            row = cursor.fetchone()
            return self._entitlement(row) if row else None

    def record_initial_free_grant(self, user_id: str, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"global-free:{user_id}",))
            cursor.execute("""SELECT e.* FROM global_commerce_free_grants g JOIN global_commerce_entitlements e ON e.entitlement_id=g.entitlement_id WHERE g.user_id=%s AND g.grant_kind='initial'""", (user_id,))
            existing = cursor.fetchone()
            if existing:
                connection.commit()
                return self._entitlement(existing)
            cursor.execute(
                """INSERT INTO global_commerce_entitlements (
                  entitlement_id,user_id,offer_code,plan_version,source_kind,source_id,status,starts_at_ms,ends_at_ms,
                  copilot_minutes_granted,copilot_minutes_used,copilot_minutes_locked,screen_assist_uses_granted,
                  screen_assist_uses_used,screen_assist_uses_locked,resume_jd_enabled,knowledge_base_enabled,
                  written_exam_enabled,full_product_enabled,knowledge_tokens_granted,knowledge_tokens_used,knowledge_tokens_locked,created_at_ms,updated_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                self._entitlement_values(entitlement),
            )
            stored = self._entitlement(cursor.fetchone())
            cursor.execute("INSERT INTO global_commerce_free_grants(user_id,grant_kind,entitlement_id,granted_at_ms) VALUES (%s,'initial',%s,%s)", (user_id, stored.entitlement_id, stored.starts_at_ms))
            connection.commit()
            return stored

    def reservation(self, operation_id: str) -> UsageReservation | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_usage_reservations WHERE operation_id=%s", (operation_id,))
            row = cursor.fetchone()
            return self._reservation(row) if row else None

    def reserve_usage(self, reservation: UsageReservation) -> UsageReservation:
        return self.reserve_usage_atomic(user_id=reservation.user_id, usage_kind=reservation.usage_kind, amount=reservation.amount, operation_id=reservation.operation_id, created_at_ms=reservation.created_at_ms)

    def reserve_usage_atomic(self, *, user_id: str, usage_kind: UsageKind, amount: int, operation_id: str, created_at_ms: int) -> UsageReservation:
        if usage_kind == "copilot_minute":
            limit_column, used_column, locked_column = "copilot_minutes_granted", "copilot_minutes_used", "copilot_minutes_locked"
        elif usage_kind == "screen_assist":
            limit_column, used_column, locked_column = "screen_assist_uses_granted", "screen_assist_uses_used", "screen_assist_uses_locked"
        else:
            limit_column, used_column, locked_column = "knowledge_tokens_granted", "knowledge_tokens_used", "knowledge_tokens_locked"
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_usage_reservations WHERE operation_id=%s FOR UPDATE", (operation_id,))
            existing = cursor.fetchone()
            if existing:
                result = self._reservation(existing)
                if result.user_id != user_id or result.usage_kind != usage_kind or result.amount != amount:
                    raise ValueError("idempotency key was reused with different usage")
                return result
            cursor.execute(
                f"""SELECT * FROM global_commerce_entitlements
                    WHERE user_id=%s AND status='active' AND starts_at_ms<=%s AND (ends_at_ms IS NULL OR ends_at_ms>%s)
                      AND ({limit_column} IS NULL OR {limit_column}-{used_column}-{locked_column}>=%s)
                    ORDER BY ends_at_ms ASC NULLS LAST, starts_at_ms DESC LIMIT 1 FOR UPDATE SKIP LOCKED""",
                (user_id, created_at_ms, created_at_ms, amount),
            )
            entitlement = cursor.fetchone()
            if not entitlement:
                raise LookupError(f"insufficient {usage_kind} entitlement")
            cursor.execute(f"UPDATE global_commerce_entitlements SET {locked_column}={locked_column}+%s,updated_at_ms=%s WHERE entitlement_id=%s", (amount, created_at_ms, entitlement["entitlement_id"]))
            cursor.execute("""INSERT INTO global_commerce_usage_reservations(operation_id,user_id,entitlement_id,usage_kind,amount,status,created_at_ms) VALUES (%s,%s,%s,%s,%s,'reserved',%s) RETURNING *""", (operation_id, user_id, entitlement["entitlement_id"], usage_kind, amount, created_at_ms))
            reservation = self._reservation(cursor.fetchone())
            connection.commit()
            return reservation

    def update_reservation(self, reservation: UsageReservation) -> UsageReservation:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("UPDATE global_commerce_usage_reservations SET status=%s,settled_at_ms=CASE WHEN %s='settled' THEN %s ELSE settled_at_ms END,released_at_ms=CASE WHEN %s='released' THEN %s ELSE released_at_ms END WHERE operation_id=%s RETURNING *", (reservation.status, reservation.status, reservation.created_at_ms, reservation.status, reservation.created_at_ms, reservation.operation_id))
            row = cursor.fetchone()
            if not row:
                raise KeyError(reservation.operation_id)
            connection.commit()
            return self._reservation(row)

    def finalize_usage_atomic(self, *, operation_id: str, outcome: str, actual_amount: int | None = None, finalized_at_ms: int) -> UsageReservation:
        if outcome not in {"settled", "released"}:
            raise ValueError("invalid usage outcome")
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_usage_reservations WHERE operation_id=%s FOR UPDATE", (operation_id,))
            row = cursor.fetchone()
            if not row: raise KeyError(operation_id)
            reservation = self._reservation(row)
            if reservation.status != "reserved": return reservation
            if reservation.usage_kind == "copilot_minute":
                locked_column, used_column = "copilot_minutes_locked", "copilot_minutes_used"
            elif reservation.usage_kind == "screen_assist":
                locked_column, used_column = "screen_assist_uses_locked", "screen_assist_uses_used"
            else:
                locked_column, used_column = "knowledge_tokens_locked", "knowledge_tokens_used"
            used = reservation.amount if actual_amount is None else max(0, actual_amount)
            used_delta = used if outcome == "settled" else 0
            cursor.execute(f"UPDATE global_commerce_entitlements SET {locked_column}=GREATEST(0,{locked_column}-%s),{used_column}={used_column}+%s,updated_at_ms=%s WHERE entitlement_id=%s", (reservation.amount,used_delta,finalized_at_ms,reservation.entitlement_id))
            cursor.execute("UPDATE global_commerce_usage_reservations SET status=%s,settled_at_ms=CASE WHEN %s='settled' THEN %s ELSE NULL END,released_at_ms=CASE WHEN %s='released' THEN %s ELSE NULL END WHERE operation_id=%s RETURNING *", (outcome,outcome,finalized_at_ms,outcome,finalized_at_ms,operation_id))
            finalized = self._reservation(cursor.fetchone())
            connection.commit()
            return finalized

    def update_entitlement(self, entitlement: GlobalEntitlement) -> GlobalEntitlement:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""UPDATE global_commerce_entitlements SET status=%s,copilot_minutes_used=%s,copilot_minutes_locked=%s,screen_assist_uses_used=%s,screen_assist_uses_locked=%s,knowledge_tokens_used=%s,knowledge_tokens_locked=%s,updated_at_ms=%s WHERE entitlement_id=%s RETURNING *""", (entitlement.status, entitlement.copilot_minutes_used, entitlement.copilot_minutes_locked, entitlement.screen_assist_uses_used, entitlement.screen_assist_uses_locked, entitlement.knowledge_tokens_used, entitlement.knowledge_tokens_locked, max(entitlement.starts_at_ms, entitlement.ends_at_ms or 0), entitlement.entitlement_id))
            row = cursor.fetchone()
            if not row:
                raise KeyError(entitlement.entitlement_id)
            connection.commit()
            return self._entitlement(row)

    def provider_mapping(self, mode: str, offer_code: str) -> GlobalProductMapping | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_product_mappings WHERE mode=%s AND offer_code=%s", (mode, offer_code))
            row = cursor.fetchone()
            return self._mapping(row) if row else None

    def save_provider_mapping(self, mapping: GlobalProductMapping) -> GlobalProductMapping:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""INSERT INTO global_commerce_product_mappings(mode,offer_code,plan_version,provider_product_id,validation_status,validated_amount_cents,validated_currency,validated_billing_mode,updated_at_ms)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0)
                ON CONFLICT(mode,offer_code) DO UPDATE SET plan_version=EXCLUDED.plan_version,provider_product_id=EXCLUDED.provider_product_id,validation_status=EXCLUDED.validation_status,validated_amount_cents=EXCLUDED.validated_amount_cents,validated_currency=EXCLUDED.validated_currency,validated_billing_mode=EXCLUDED.validated_billing_mode RETURNING *""",
                (mapping.mode,mapping.offer_code,mapping.plan_version,mapping.provider_product_id,mapping.validation_status,mapping.validated_amount_cents,mapping.validated_currency,mapping.validated_billing_mode))
            stored = self._mapping(cursor.fetchone())
            cursor.execute("UPDATE global_commerce_provider_configs SET enabled=FALSE,validation_status='draft',updated_at_ms=0 WHERE mode=%s", (mapping.mode,))
            connection.commit()
            return stored

    def order_for_idempotency(self, user_id: str, idempotency_key: str) -> GlobalOrder | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders WHERE user_id=%s AND idempotency_key=%s", (user_id,idempotency_key))
            row = cursor.fetchone()
            return self._order(row) if row else None

    def order(self, order_id: str) -> GlobalOrder | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders WHERE order_id=%s", (order_id,))
            row = cursor.fetchone()
            return self._order(row) if row else None

    def order_by_provider_order(self, *, mode: str, provider_order_id: str) -> GlobalOrder | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders WHERE mode=%s AND provider_order_id=%s ORDER BY created_at_ms DESC LIMIT 1", (mode, provider_order_id))
            row = cursor.fetchone()
            return self._order(row) if row else None

    def order_by_provider_subscription(self, *, mode: str, provider_subscription_id: str) -> GlobalOrder | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders WHERE mode=%s AND provider_subscription_id=%s ORDER BY created_at_ms DESC LIMIT 1", (mode, provider_subscription_id))
            row = cursor.fetchone()
            return self._order(row) if row else None

    def save_order(self, order: GlobalOrder) -> GlobalOrder:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""INSERT INTO global_commerce_orders(order_id,user_id,offer_code,plan_version,mode,provider,expected_amount_cents,expected_currency,status,idempotency_key,created_at_ms,updated_at_ms)
                VALUES (%s,%s,%s,%s,%s,'creem',%s,%s,%s,%s,%s,%s)
                ON CONFLICT(user_id,idempotency_key) DO UPDATE SET idempotency_key=EXCLUDED.idempotency_key RETURNING *""",
                (order.order_id,order.user_id,order.offer_code,order.plan_version,order.mode,order.expected_amount_cents,order.expected_currency,order.status,order.idempotency_key,order.created_at_ms,order.updated_at_ms))
            stored = self._order(cursor.fetchone())
            connection.commit()
            return stored

    def update_order(self, order: GlobalOrder) -> GlobalOrder:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""UPDATE global_commerce_orders SET status=%s,checkout_url=%s,provider_checkout_id=%s,provider_order_id=%s,provider_subscription_id=%s,provider_customer_id=%s,failure_code=%s,updated_at_ms=%s,paid_at_ms=CASE WHEN %s='paid' THEN %s ELSE paid_at_ms END,refunded_at_ms=CASE WHEN %s='refunded' THEN %s ELSE refunded_at_ms END,disputed_at_ms=CASE WHEN %s='disputed' THEN %s ELSE disputed_at_ms END WHERE order_id=%s RETURNING *""",
                (order.status,order.checkout_url,order.provider_checkout_id,order.provider_order_id,order.provider_subscription_id,order.provider_customer_id,order.failure_code,order.updated_at_ms,order.status,order.updated_at_ms,order.status,order.updated_at_ms,order.status,order.updated_at_ms,order.order_id))
            row = cursor.fetchone()
            if not row: raise KeyError(order.order_id)
            connection.commit()
            return self._order(row)

    def orders_for_user(self, user_id: str) -> list[GlobalOrder]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders WHERE user_id=%s ORDER BY created_at_ms DESC LIMIT 100", (user_id,))
            return [self._order(row) for row in cursor.fetchall()]

    def recent_orders(self, *, limit: int = 100) -> list[GlobalOrder]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_orders ORDER BY created_at_ms DESC LIMIT %s", (max(1, min(limit, 500)),))
            return [self._order(row) for row in cursor.fetchall()]

    def subscription_by_provider_id(self, *, mode: str, provider_subscription_id: str) -> GlobalSubscription | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_subscriptions WHERE mode=%s AND provider_subscription_id=%s", (mode, provider_subscription_id))
            row = cursor.fetchone()
            return self._subscription(row) if row else None

    def subscriptions_for_user(self, user_id: str) -> list[GlobalSubscription]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_subscriptions WHERE user_id=%s ORDER BY updated_at_ms DESC", (user_id,))
            return [self._subscription(row) for row in cursor.fetchall()]

    def recent_subscriptions(self, *, limit: int = 100) -> list[GlobalSubscription]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_subscriptions ORDER BY updated_at_ms DESC LIMIT %s", (max(1, min(limit, 500)),))
            return [self._subscription(row) for row in cursor.fetchall()]

    def upsert_subscription(self, subscription: GlobalSubscription) -> GlobalSubscription:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """INSERT INTO global_commerce_subscriptions(
                  subscription_id,user_id,offer_code,plan_version,mode,provider_subscription_id,provider_customer_id,
                  status,current_period_start_ms,current_period_end_ms,canceled_at_ms,provider_updated_at_ms,created_at_ms,updated_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(mode,provider_subscription_id) DO UPDATE SET
                  status=CASE WHEN EXCLUDED.provider_updated_at_ms >= global_commerce_subscriptions.provider_updated_at_ms THEN EXCLUDED.status ELSE global_commerce_subscriptions.status END,
                  current_period_start_ms=GREATEST(global_commerce_subscriptions.current_period_start_ms,EXCLUDED.current_period_start_ms),
                  current_period_end_ms=GREATEST(global_commerce_subscriptions.current_period_end_ms,EXCLUDED.current_period_end_ms),
                  canceled_at_ms=CASE WHEN EXCLUDED.provider_updated_at_ms >= global_commerce_subscriptions.provider_updated_at_ms THEN EXCLUDED.canceled_at_ms ELSE global_commerce_subscriptions.canceled_at_ms END,
                  provider_customer_id=CASE WHEN EXCLUDED.provider_updated_at_ms >= global_commerce_subscriptions.provider_updated_at_ms THEN EXCLUDED.provider_customer_id ELSE global_commerce_subscriptions.provider_customer_id END,
                  provider_updated_at_ms=GREATEST(global_commerce_subscriptions.provider_updated_at_ms,EXCLUDED.provider_updated_at_ms),
                  updated_at_ms=GREATEST(global_commerce_subscriptions.updated_at_ms,EXCLUDED.updated_at_ms)
                RETURNING *""",
                (subscription.subscription_id,subscription.user_id,subscription.offer_code,subscription.plan_version,subscription.mode,
                 subscription.provider_subscription_id,subscription.provider_customer_id,subscription.status,
                 subscription.current_period_start_ms,subscription.current_period_end_ms,subscription.canceled_at_ms,
                 subscription.provider_updated_at_ms,subscription.created_at_ms,subscription.updated_at_ms),
            )
            stored = self._subscription(cursor.fetchone())
            connection.commit()
            return stored

    def revoke_entitlements_for_source(self, *, source_kind: str, source_id_prefix: str) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE global_commerce_entitlements SET status='revoked',updated_at_ms=%s WHERE source_kind=%s AND source_id LIKE %s AND status<>'revoked'", (int(time() * 1000), source_kind, f"{source_id_prefix}%"))
            changed = cursor.rowcount
            connection.commit()
            return changed

    def record_provider_event_once(self, *, mode: str, event_id: str, event_type: str, payload_sha256: str, provider_created_at_ms: int, received_at_ms: int, order_id: str | None) -> bool:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("""INSERT INTO global_commerce_provider_events(mode,provider_event_id,event_type,provider_created_at_ms,payload_sha256,status,order_id,received_at_ms)
                VALUES (%s,%s,%s,%s,%s,'processing',%s,%s)
                ON CONFLICT(mode,provider_event_id) DO UPDATE SET
                  status='processing',received_at_ms=EXCLUDED.received_at_ms,error_code=NULL,processed_at_ms=NULL
                WHERE global_commerce_provider_events.status='failed'
                  AND global_commerce_provider_events.payload_sha256=EXCLUDED.payload_sha256""",
                (mode,event_id,event_type,provider_created_at_ms,payload_sha256,order_id,received_at_ms))
            inserted = cursor.rowcount == 1
            connection.commit()
            return inserted

    def mark_provider_event(self, *, mode: str, event_id: str, status: str, processed_at_ms: int, error_code: str | None = None) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE global_commerce_provider_events SET status=%s,processed_at_ms=%s,error_code=%s WHERE mode=%s AND provider_event_id=%s", (status,processed_at_ms,error_code,mode,event_id))
            connection.commit()

    def recent_provider_events(self, *, mode: str, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT mode,provider_event_id,event_type,status,order_id,error_code,provider_created_at_ms,received_at_ms,processed_at_ms FROM global_commerce_provider_events WHERE mode=%s ORDER BY received_at_ms DESC LIMIT %s", (mode, max(1, min(limit, 500))))
            return [dict(row) for row in cursor.fetchall()]

    def provider_config(self, mode: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_provider_configs WHERE mode=%s", (mode,))
            row = cursor.fetchone()
            if not row: raise KeyError(mode)
            return dict(row)

    def save_provider_credentials(self, *, mode: str, credential_ciphertext: str, api_key_fingerprint: str, webhook_secret_fingerprint: str, updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""UPDATE global_commerce_provider_configs
                SET credential_ciphertext=%s,api_key_fingerprint=%s,webhook_secret_fingerprint=%s,
                    enabled=FALSE,validation_status='draft',validation_errors='[]'::jsonb,
                    connection_checked_at_ms=NULL,updated_by_user_id=%s,updated_at_ms=%s,
                    config_version=config_version+1
                WHERE mode=%s RETURNING *""",
                (credential_ciphertext,api_key_fingerprint,webhook_secret_fingerprint,updated_by_user_id,updated_at_ms,mode))
            row = cursor.fetchone()
            if not row: raise KeyError(mode)
            connection.commit()
            return dict(row)

    def mark_provider_connection_checked(self, *, mode: str, checked_at_ms: int, validation_status: str, validation_errors: list[str]) -> dict[str, object]:
        from json import dumps
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""UPDATE global_commerce_provider_configs
                SET connection_checked_at_ms=%s,validation_status=%s,validation_errors=%s::jsonb
                WHERE mode=%s RETURNING *""", (checked_at_ms,validation_status,dumps(validation_errors),mode))
            row = cursor.fetchone()
            if not row: raise KeyError(mode)
            connection.commit()
            return dict(row)

    def set_provider_enabled(self, *, mode: str, enabled: bool, validation_status: str, validation_errors: list[str], updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        from json import dumps
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""UPDATE global_commerce_provider_configs SET enabled=%s,validation_status=%s,validation_errors=%s::jsonb,updated_by_user_id=%s,updated_at_ms=%s,config_version=config_version+1 WHERE mode=%s RETURNING *""", (enabled,validation_status,dumps(validation_errors),updated_by_user_id,updated_at_ms,mode))
            row = cursor.fetchone()
            if not row: raise KeyError(mode)
            connection.commit()
            return dict(row)

    def active_fair_use_decision(self, user_id: str, now_ms: int) -> FairUseDecision | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""SELECT * FROM global_commerce_fair_use_decisions WHERE user_id=%s AND status IN ('review','restricted') AND effective_at_ms<=%s AND (expires_at_ms IS NULL OR expires_at_ms>%s) ORDER BY effective_at_ms DESC LIMIT 1""", (user_id,now_ms,now_ms))
            row = cursor.fetchone()
            return self._fair_use_decision(row) if row else None

    def save_fair_use_decision(self, decision: FairUseDecision) -> FairUseDecision:
        from json import dumps
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("""INSERT INTO global_commerce_fair_use_decisions(decision_id,user_id,status,reason_code,evidence,restrict_new_sessions,effective_at_ms,expires_at_ms,created_at_ms,updated_at_ms) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) ON CONFLICT(decision_id) DO UPDATE SET status=EXCLUDED.status,reason_code=EXCLUDED.reason_code,evidence=EXCLUDED.evidence,restrict_new_sessions=EXCLUDED.restrict_new_sessions,expires_at_ms=EXCLUDED.expires_at_ms,updated_at_ms=EXCLUDED.updated_at_ms RETURNING *""", (decision.decision_id,decision.user_id,decision.status,decision.reason_code,dumps(decision.evidence),decision.restrict_new_sessions,decision.effective_at_ms,decision.expires_at_ms,decision.effective_at_ms,decision.effective_at_ms))
            stored = self._fair_use_decision(cursor.fetchone())
            connection.commit()
            return stored

    def recent_fair_use_decisions(self, *, limit: int = 100) -> list[FairUseDecision]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM global_commerce_fair_use_decisions ORDER BY effective_at_ms DESC LIMIT %s", (max(1, min(limit, 500)),))
            return [self._fair_use_decision(row) for row in cursor.fetchall()]

    def _connect(self):
        active = self._transaction_connection.get()
        if active is not None:
            return _BorrowedConnection(active)
        return psycopg.connect(self.settings.database_url, connect_timeout=self.settings.database_connect_timeout_seconds, application_name=f"{self.settings.database_application_name}-global-commerce")

    def _ensure_tables(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, (
                Path(REPO_ROOT / "apps/backend/migrations/versions/0040_global_creem_commerce.sql"),
                Path(REPO_ROOT / "apps/backend/migrations/versions/0042_global_creem_lifecycle_hardening.sql"),
                Path(REPO_ROOT / "apps/backend/migrations/versions/0043_global_creem_admin_configuration.sql"),
                Path(REPO_ROOT / "apps/backend/migrations/versions/0045_global_commerce_catalog_v2.sql"),
                Path(REPO_ROOT / "apps/backend/migrations/versions/0046_global_knowledge_token_entitlements.sql"),
            ))
            connection.commit()

    @staticmethod
    def _plan(row) -> GlobalPlan:
        return GlobalPlan(row["offer_code"], int(row["plan_version"]), row["display_name"], row["description"], int(row["price_cents"]), row["billing_mode"], row["duration_days"], row["copilot_minutes"], row["screen_assist_uses"], bool(row["resume_jd_enabled"]), bool(row["knowledge_base_enabled"]), bool(row["written_exam_enabled"]), bool(row["full_product_enabled"]), row["status"], bool(row["featured"]), int(row["display_order"]), row["currency"], int(row["created_at_ms"]), int(row.get("knowledge_tokens", 0)))

    @staticmethod
    def _entitlement(row) -> GlobalEntitlement:
        return GlobalEntitlement(row["entitlement_id"], row["user_id"], row["offer_code"], int(row["plan_version"]), row["source_kind"], row["source_id"], int(row["starts_at_ms"]), row["ends_at_ms"], row["copilot_minutes_granted"], row["screen_assist_uses_granted"], bool(row["resume_jd_enabled"]), bool(row["knowledge_base_enabled"]), bool(row["written_exam_enabled"]), bool(row["full_product_enabled"]), row["status"], int(row["copilot_minutes_used"]), int(row["copilot_minutes_locked"]), int(row["screen_assist_uses_used"]), int(row["screen_assist_uses_locked"]), int(row.get("knowledge_tokens_granted", 0)), int(row.get("knowledge_tokens_used", 0)), int(row.get("knowledge_tokens_locked", 0)))

    @staticmethod
    def _entitlement_values(item: GlobalEntitlement) -> tuple[object, ...]:
        return (item.entitlement_id,item.user_id,item.offer_code,item.plan_version,item.source_kind,item.source_id,item.status,item.starts_at_ms,item.ends_at_ms,item.copilot_minutes_granted,item.copilot_minutes_used,item.copilot_minutes_locked,item.screen_assist_uses_granted,item.screen_assist_uses_used,item.screen_assist_uses_locked,item.resume_jd_enabled,item.knowledge_base_enabled,item.written_exam_enabled,item.full_product_enabled,item.knowledge_tokens_granted,item.knowledge_tokens_used,item.knowledge_tokens_locked,item.starts_at_ms,item.starts_at_ms)

    @staticmethod
    def _reservation(row) -> UsageReservation:
        return UsageReservation(row["operation_id"], row["user_id"], row["entitlement_id"], row["usage_kind"], int(row["amount"]), row["status"], int(row["created_at_ms"]))

    @staticmethod
    def _mapping(row) -> GlobalProductMapping:
        return GlobalProductMapping(row["mode"],row["offer_code"],int(row["plan_version"]),row["provider_product_id"],row["validation_status"],row["validated_amount_cents"],row["validated_currency"],row["validated_billing_mode"])

    @staticmethod
    def _order(row) -> GlobalOrder:
        return GlobalOrder(row["order_id"],row["user_id"],row["offer_code"],int(row["plan_version"]),row["mode"],int(row["expected_amount_cents"]),row["expected_currency"],row["status"],row["idempotency_key"],int(row["created_at_ms"]),int(row["updated_at_ms"]),row["checkout_url"],row["provider_checkout_id"],row["provider_order_id"],row["provider_subscription_id"],row["provider_customer_id"],row["failure_code"])

    @staticmethod
    def _subscription(row) -> GlobalSubscription:
        return GlobalSubscription(row["subscription_id"],row["user_id"],row["offer_code"],int(row["plan_version"]),row["mode"],row["provider_subscription_id"],row["provider_customer_id"],row["status"],int(row["current_period_start_ms"]),int(row["current_period_end_ms"]),int(row["provider_updated_at_ms"]),int(row["created_at_ms"]),int(row["updated_at_ms"]),row["canceled_at_ms"])

    @staticmethod
    def _fair_use_decision(row) -> FairUseDecision:
        evidence = row["evidence"] if isinstance(row["evidence"], dict) else {}
        return FairUseDecision(row["decision_id"],row["user_id"],row["status"],row["reason_code"],evidence,bool(row["restrict_new_sessions"]),int(row["effective_at_ms"]),row["expires_at_ms"])


class _BorrowedConnection:
    """Prevent nested repository calls from committing or closing an outer transaction."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self._connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self, *args, **kwargs):
        return self._connection.cursor(*args, **kwargs)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None
