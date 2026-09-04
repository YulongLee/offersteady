from __future__ import annotations

from json import dumps
from pathlib import Path
from typing import Mapping
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings
from app.services.postgres_migrations import apply_sql_migrations


class PostgresBillingRepository:
    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for persistent billing")
        self.settings = settings
        self._ensure_tables()

    def list_catalog_products(self) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT product_id AS id, catalog_version, kind, display_name, price_cents,
                       points, duration_days, knowledge_index_allowance, published
                FROM billing_catalog_products
                WHERE published = TRUE
                ORDER BY CASE kind WHEN 'time_pass' THEN 0 ELSE 1 END,
                         duration_days NULLS LAST, points NULLS LAST
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def ensure_welcome_grant(self, *, user_id: str, points: int, created_at_ms: int) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'welcome_grant',%s,%s,%s,%s)
                ON CONFLICT (reference_id) DO NOTHING
                """,
                (f"ledger-welcome-{uuid4().hex}", user_id, points, created_at_ms, f"welcome:{user_id}", "新用户赠送积分"),
            )
            connection.commit()

    def list_ledger(self, *, user_id: str) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM points_redemption_ledger WHERE user_id = %s ORDER BY created_at_ms DESC, ledger_entry_id DESC",
                (user_id,),
            )
            return [self._ledger(row) for row in cursor.fetchall()]

    def balance(self, *, user_id: str) -> int:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s", (user_id,))
            return int(cursor.fetchone()["balance"])

    def get_or_create_referral_code(self, *, user_id: str, candidate_code: str, created_at_ms: int) -> str:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO growth_referral_codes (user_id, referral_code, status, created_at_ms)
                VALUES (%s,%s,'active',%s)
                ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
                RETURNING referral_code
                """,
                (user_id, candidate_code, created_at_ms),
            )
            code = str(cursor.fetchone()["referral_code"])
            connection.commit()
            return code

    def resolve_referral_code(self, *, referral_code: str) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT c.referral_code, c.status, s.enabled, s.reward_points,
                       s.invitee_reward_points, s.config_version
                FROM growth_referral_codes c
                CROSS JOIN growth_referral_settings s
                WHERE c.referral_code = %s AND c.status = 'active' AND s.settings_id = 'default'
                """,
                (referral_code,),
            )
            row = cursor.fetchone()
            return dict(row) if row is not None else None

    def referral_status(self, *, user_id: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT referral_code FROM growth_referral_codes WHERE user_id = %s", (user_id,))
            code_row = cursor.fetchone()
            cursor.execute("SELECT * FROM growth_referral_settings WHERE settings_id = 'default'")
            settings = dict(cursor.fetchone())
            cursor.execute(
                """
                SELECT COUNT(*) AS invite_count, COALESCE(SUM(reward_points), 0) AS total_reward_points
                FROM growth_referral_activations WHERE inviter_user_id = %s
                """,
                (user_id,),
            )
            summary = dict(cursor.fetchone())
            cursor.execute(
                """
                SELECT activation_id, reward_points, invitee_reward_points, activated_at_ms
                FROM growth_referral_activations WHERE invitee_user_id = %s
                """,
                (user_id,),
            )
            activation = cursor.fetchone()
            return {
                "referralCode": None if code_row is None else str(code_row["referral_code"]),
                "enabled": bool(settings["enabled"]),
                "rewardPoints": int(settings["reward_points"]),
                "inviterRewardPoints": int(settings["reward_points"]),
                "inviteeRewardPoints": int(settings["invitee_reward_points"]),
                "configVersion": int(settings["config_version"]),
                "inviteCount": int(summary["invite_count"]),
                "totalRewardPoints": int(summary["total_reward_points"]),
                "hasActivatedReferral": activation is not None,
                "activatedReward": None if activation is None else {
                    "inviterRewardPoints": int(activation["reward_points"]),
                    "inviteeRewardPoints": int(activation["invitee_reward_points"]),
                    "activatedAtMs": int(activation["activated_at_ms"]),
                },
            }

    def activate_referral(
        self,
        *,
        invitee_user_id: str,
        referral_code: str,
        activated_at_ms: int,
        invitee_registered_at_ms: int | None,
        activation_deadline_ms: int | None,
    ) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT user_id, referral_code FROM growth_referral_codes WHERE referral_code = %s AND status = 'active'",
                (referral_code,),
            )
            code_row = cursor.fetchone()
            if code_row is None:
                return {"outcome": "invalid-code"}
            inviter_user_id = str(code_row["user_id"])
            if inviter_user_id == invitee_user_id:
                return {"outcome": "self-referral"}
            for locked_user_id in sorted((inviter_user_id, invitee_user_id)):
                cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"referral-user:{locked_user_id}",))
            cursor.execute(
                "SELECT * FROM growth_referral_activations WHERE invitee_user_id = %s FOR UPDATE",
                (invitee_user_id,),
            )
            existing = cursor.fetchone()
            if existing is not None:
                return {
                    "outcome": "activated" if str(existing["referral_code"]) == referral_code else "already-activated",
                    "replayed": str(existing["referral_code"]) == referral_code,
                    "rewardPoints": int(existing["reward_points"]),
                    "inviterRewardPoints": int(existing["reward_points"]),
                    "inviteeRewardPoints": int(existing["invitee_reward_points"]),
                    "activatedAtMs": int(existing["activated_at_ms"]),
                }
            if invitee_registered_at_ms is None or activation_deadline_ms is None:
                return {"outcome": "registration-time-unavailable"}
            if activated_at_ms > activation_deadline_ms:
                return {"outcome": "activation-window-expired", "activationDeadlineMs": activation_deadline_ms}
            cursor.execute("SELECT * FROM growth_referral_settings WHERE settings_id = 'default' FOR SHARE")
            settings = cursor.fetchone()
            if not bool(settings["enabled"]):
                return {"outcome": "disabled"}
            activation_id = f"referral-activation-{uuid4().hex}"
            ledger_reference_id = f"referral:{activation_id}:inviter"
            invitee_ledger_reference_id = f"referral:{activation_id}:invitee"
            reward_points = int(settings["reward_points"])
            invitee_reward_points = int(settings["invitee_reward_points"])
            if self.settings.partner_program_enabled:
                cursor.execute(
                    """INSERT INTO growth_acquisition_reward_claims
                       (acquired_user_id,reward_program,referral_activation_id,claimed_at_ms)
                       VALUES (%s,'points_referral',%s,%s)
                       ON CONFLICT (acquired_user_id) DO NOTHING""",
                    (invitee_user_id, activation_id, activated_at_ms),
                )
                cursor.execute(
                    "SELECT reward_program,referral_activation_id FROM growth_acquisition_reward_claims WHERE acquired_user_id=%s FOR UPDATE",
                    (invitee_user_id,),
                )
                reward_claim = cursor.fetchone()
                if not reward_claim or reward_claim["reward_program"] != "points_referral":
                    return {"outcome": "reward-program-conflict"}
            cursor.execute(
                """
                INSERT INTO growth_referral_activations (
                  activation_id, inviter_user_id, invitee_user_id, referral_code,
                  reward_points, invitee_reward_points, config_version,
                  ledger_reference_id, invitee_ledger_reference_id,
                  activation_deadline_ms, activated_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    activation_id, inviter_user_id, invitee_user_id, referral_code,
                    reward_points, invitee_reward_points, int(settings["config_version"]),
                    ledger_reference_id, invitee_ledger_reference_id,
                    activation_deadline_ms, activated_at_ms,
                ),
            )
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'referral_credit',%s,%s,%s,%s)
                """,
                (f"ledger-{uuid4().hex}", inviter_user_id, reward_points, activated_at_ms,
                 ledger_reference_id, "邀请好友奖励"),
            )
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'referral_invitee_credit',%s,%s,%s,%s)
                """,
                (
                    f"ledger-{uuid4().hex}", invitee_user_id, invitee_reward_points,
                    activated_at_ms, invitee_ledger_reference_id, "新用户邀请激活奖励",
                ),
            )
            cursor.execute(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s",
                (inviter_user_id,),
            )
            inviter_balance = int(cursor.fetchone()["balance"])
            cursor.execute(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s",
                (invitee_user_id,),
            )
            invitee_balance = int(cursor.fetchone()["balance"])
            connection.commit()
            return {
                "outcome": "activated",
                "replayed": False,
                "rewardPoints": reward_points,
                "inviterRewardPoints": reward_points,
                "inviteeRewardPoints": invitee_reward_points,
                "activatedAtMs": activated_at_ms,
                "inviterBalance": inviter_balance,
                "inviteeBalance": invitee_balance,
            }

    def growth_referral_settings(self) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM growth_referral_settings WHERE settings_id = 'default'")
            row = dict(cursor.fetchone())
            return {
                "enabled": bool(row["enabled"]),
                "rewardPoints": int(row["reward_points"]),
                "inviterRewardPoints": int(row["reward_points"]),
                "inviteeRewardPoints": int(row["invitee_reward_points"]),
                "activationWindowDays": 3,
                "configVersion": int(row["config_version"]),
                "updatedByUserId": row["updated_by_user_id"],
                "updatedAtMs": int(row["updated_at_ms"]),
            }

    def update_growth_referral_settings(self, *, enabled: bool, reward_points: int, invitee_reward_points: int, updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE growth_referral_settings
                SET enabled = %s, reward_points = %s, invitee_reward_points = %s,
                    config_version = config_version + 1,
                    updated_by_user_id = %s, updated_at_ms = %s
                WHERE settings_id = 'default'
                RETURNING *
                """,
                (enabled, reward_points, invitee_reward_points, updated_by_user_id, updated_at_ms),
            )
            row = dict(cursor.fetchone())
            connection.commit()
            return {
                "enabled": bool(row["enabled"]),
                "rewardPoints": int(row["reward_points"]),
                "inviterRewardPoints": int(row["reward_points"]),
                "inviteeRewardPoints": int(row["invitee_reward_points"]),
                "activationWindowDays": 3,
                "configVersion": int(row["config_version"]),
                "updatedByUserId": row["updated_by_user_id"],
                "updatedAtMs": int(row["updated_at_ms"]),
            }

    def list_payment_channel_configs(self) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_payment_channel_configs ORDER BY channel")
            return [dict(row) for row in cursor.fetchall()]

    def payment_channel_config(self, *, channel: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_payment_channel_configs WHERE channel = %s", (channel,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(channel)
            return dict(row)

    def payment_channel_acceptance(self, *, channel: str) -> dict[str, object]:
        provider = channel
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT outcome, signature_verified, app_identity_verified,
                       seller_identity_verified, last_received_at_ms
                FROM billing_payment_callback_events
                WHERE provider = %s
                ORDER BY last_received_at_ms DESC LIMIT 1
                """,
                (provider,),
            )
            callback = cursor.fetchone()
            try:
                cursor.execute(
                    """
                    SELECT result, safe_details_json, created_at_ms
                    FROM admin_audit_events
                    WHERE action = 'payments.reconcile'
                      AND safe_details_json->>'provider' = %s
                    ORDER BY created_at_ms DESC LIMIT 1
                    """,
                    (provider,),
                )
                query = cursor.fetchone()
            except psycopg.errors.UndefinedTable:
                connection.rollback()
                query = None
        return {
            "notification": None if callback is None else {
                "status": "passed" if callback["outcome"] == "paid" else "failed",
                "outcome": str(callback["outcome"]),
                "signatureVerified": callback["signature_verified"],
                "appIdentityVerified": callback["app_identity_verified"],
                "sellerIdentityVerified": callback["seller_identity_verified"],
                "atMs": int(callback["last_received_at_ms"]),
            },
            "authoritativeQuery": None if query is None else {
                "status": "passed" if query["result"] == "success" and dict(query["safe_details_json"]).get("status") in {"reconciled", "already_reconciled"} else "failed",
                "outcome": str(dict(query["safe_details_json"]).get("status", query["result"])),
                "atMs": int(query["created_at_ms"]),
            },
        }

    def save_payment_channel_config(
        self,
        *,
        channel: str,
        public_config: Mapping[str, object],
        secret_config_ciphertext: str | None,
        validation_status: str,
        validation_errors: list[str],
        updated_by_user_id: str,
        updated_at_ms: int,
    ) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE billing_payment_channel_configs
                SET public_config = %s::jsonb, secret_config_ciphertext = %s,
                    validation_status = %s, validation_errors = %s::jsonb,
                    config_version = config_version + 1, enabled = FALSE,
                    updated_by_user_id = %s, updated_at_ms = %s
                WHERE channel = %s RETURNING *
                """,
                (dumps(dict(public_config)), secret_config_ciphertext, validation_status,
                 dumps(validation_errors), updated_by_user_id, updated_at_ms, channel),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(channel)
            connection.commit()
            return dict(row)

    def set_payment_channel_enabled(self, *, channel: str, enabled: bool, updated_by_user_id: str, updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE billing_payment_channel_configs
                SET enabled = %s, updated_by_user_id = %s, updated_at_ms = %s
                WHERE channel = %s AND (%s = FALSE OR validation_status = 'ready')
                RETURNING *
                """,
                (enabled, updated_by_user_id, updated_at_ms, channel, enabled),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError("payment_channel_not_ready")
            connection.commit()
            return dict(row)

    def create_checkout_order(self, *, order: Mapping[str, object], idempotency_key: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"checkout:{order['user_id']}:{idempotency_key}",))
            cursor.execute(
                "SELECT * FROM billing_checkout_orders WHERE user_id = %s AND idempotency_key = %s",
                (order["user_id"], idempotency_key),
            )
            existing = cursor.fetchone()
            if existing:
                return self._order(existing)
            cursor.execute(
                """
                INSERT INTO billing_checkout_orders (
                  order_id, user_id, idempotency_key, product_snapshot, amount_cents,
                  currency, channel, provider, status, action, created_at_ms, updated_at_ms, expires_at_ms
                ) VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                RETURNING *
                """,
                (
                    order["id"], order["user_id"], idempotency_key, dumps(order["product"]),
                    order["amount_cents"], order["currency"], order["channel"], order["provider"], order["status"],
                    dumps(order["action"]), order["created_at_ms"], order["updated_at_ms"],
                    int(dict(order["action"]).get("expiresAtMs") or 0),
                ),
            )
            result = self._order(cursor.fetchone())
            connection.commit()
            return result

    def replace_checkout_action(self, *, order_id: str, action: Mapping[str, object], updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "UPDATE billing_checkout_orders SET action = %s::jsonb, expires_at_ms = %s, updated_at_ms = %s WHERE order_id = %s RETURNING *",
                (dumps(dict(action)), int(action.get("expiresAtMs") or 0), updated_at_ms, order_id),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(order_id)
            connection.commit()
            return self._order(row)

    def mark_checkout_failed(self, *, order_id: str, failure_reason: str, updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                UPDATE billing_checkout_orders
                SET status = 'failed', failure_reason = %s,
                    action = '{"kind":"unavailable"}'::jsonb, updated_at_ms = %s
                WHERE order_id = %s AND status = 'payment_pending'
                RETURNING *
                """,
                (failure_reason, updated_at_ms, order_id),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute("SELECT * FROM billing_checkout_orders WHERE order_id = %s", (order_id,))
                row = cursor.fetchone()
            if row is None:
                raise KeyError(order_id)
            connection.commit()
            return self._order(row)

    def checkout_order(self, *, order_id: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_checkout_orders WHERE order_id = %s", (order_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(order_id)
            return self._order(row)

    def list_checkout_orders(self, *, user_id: str) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_checkout_orders WHERE user_id = %s ORDER BY created_at_ms DESC", (user_id,))
            return [self._order(row) for row in cursor.fetchall()]

    def confirm_checkout_paid(self, *, order_id: str, amount_cents: int, provider_trade_no: str, paid_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_checkout_orders WHERE order_id = %s FOR UPDATE", (order_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(order_id)
            if row["status"] == "paid":
                return self._order(row)
            if int(row["amount_cents"]) != amount_cents:
                cursor.execute(
                    "UPDATE billing_checkout_orders SET status = 'failed', failure_reason = 'amount_mismatch', provider_trade_no = %s, last_callback_at_ms = %s, updated_at_ms = %s WHERE order_id = %s RETURNING *",
                    (provider_trade_no, paid_at_ms, paid_at_ms, order_id),
                )
                failed = self._order(cursor.fetchone())
                connection.commit()
                return failed

            product = dict(row["product_snapshot"])
            user_id = str(row["user_id"])
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"billing-user:{user_id}",))
            if product.get("kind") == "points_pack":
                cursor.execute(
                    """
                    INSERT INTO points_redemption_ledger (
                      ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                    ) VALUES (%s,%s,'purchase_credit',%s,%s,%s,%s)
                    ON CONFLICT (reference_id) DO NOTHING
                    """,
                    (
                        f"ledger-{uuid4().hex}", user_id, int(product.get("points") or 0), paid_at_ms,
                        f"checkout:{order_id}", f"购买{product.get('display_name', '')}到账",
                    ),
                )
            elif product.get("kind") == "time_pass":
                cursor.execute(
                    "SELECT COALESCE(MAX(ends_at_ms), %s) AS latest_end FROM billing_time_pass_entitlements WHERE user_id = %s AND ends_at_ms > %s",
                    (paid_at_ms, user_id, paid_at_ms),
                )
                latest_end_ms = max(paid_at_ms, int(cursor.fetchone()["latest_end"]))
                cursor.execute("SELECT to_regclass('admin_time_entitlements') IS NOT NULL AS available")
                if bool(cursor.fetchone()["available"]):
                    cursor.execute(
                        "SELECT COALESCE(MAX(ends_at_ms), %s) AS latest_end FROM admin_time_entitlements WHERE user_id = %s AND ends_at_ms > %s",
                        (paid_at_ms, user_id, paid_at_ms),
                    )
                    latest_end_ms = max(latest_end_ms, int(cursor.fetchone()["latest_end"]))
                starts_at_ms = latest_end_ms
                ends_at_ms = starts_at_ms + int(product.get("duration_days") or 0) * 86_400_000
                cursor.execute(
                    """
                    INSERT INTO billing_time_pass_entitlements (
                      entitlement_id, user_id, product_id, starts_at_ms, ends_at_ms, order_id,
                      knowledge_allowance_granted, knowledge_allowance_used, knowledge_allowance_locked
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,0,0)
                    ON CONFLICT (order_id) DO NOTHING
                    """,
                    (
                        f"entitlement-{uuid4().hex}", user_id, product["id"], starts_at_ms, ends_at_ms,
                        order_id, int(product.get("knowledge_index_allowance") or 0),
                    ),
                )
            cursor.execute(
                """
                UPDATE billing_checkout_orders
                SET status = 'paid', failure_reason = NULL, provider_trade_no = %s,
                    paid_at_ms = %s, last_callback_at_ms = %s, updated_at_ms = %s
                WHERE order_id = %s RETURNING *
                """,
                (provider_trade_no, paid_at_ms, paid_at_ms, paid_at_ms, order_id),
            )
            paid = self._order(cursor.fetchone())
            connection.commit()
            return paid

    def create_index_quote(self, *, quote: Mapping[str, object], idempotency_key: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"index-quote:{quote['user_id']}:{idempotency_key}",))
            cursor.execute(
                "SELECT * FROM billing_index_quotes WHERE user_id = %s AND idempotency_key = %s",
                (quote["user_id"], idempotency_key),
            )
            existing = cursor.fetchone()
            if existing:
                return self._quote(existing)
            cursor.execute(
                """
                INSERT INTO billing_index_quotes (
                  quote_id, user_id, idempotency_key, document_version_id, token_estimate,
                  catalog_version, tokenizer_version, points_required, projected_balance, created_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *
                """,
                (
                    quote["quote_id"], quote["user_id"], idempotency_key, quote["document_version_id"],
                    quote["token_estimate"], quote["catalog_version"], quote["tokenizer_version"],
                    quote["points_required"], quote["projected_balance"], quote["created_at_ms"],
                ),
            )
            result = self._quote(cursor.fetchone())
            connection.commit()
            return result

    def index_quote(self, *, quote_id: str) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_index_quotes WHERE quote_id = %s", (quote_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(quote_id)
            return self._quote(row)

    def reserve_index_quote(self, *, quote_id: str, created_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_index_quotes WHERE quote_id = %s", (quote_id,))
            quote = cursor.fetchone()
            if quote is None:
                raise KeyError(quote_id)
            user_id = str(quote["user_id"])
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"billing-user:{user_id}",))
            cursor.execute("SELECT * FROM billing_index_reservations WHERE quote_id = %s", (quote_id,))
            existing = cursor.fetchone()
            if existing:
                return self._reservation(existing)
            cursor.execute(
                """
                SELECT * FROM billing_time_pass_entitlements
                WHERE user_id = %s AND starts_at_ms <= %s AND ends_at_ms > %s
                  AND knowledge_allowance_granted - knowledge_allowance_used - knowledge_allowance_locked > 0
                ORDER BY ends_at_ms ASC LIMIT 1 FOR UPDATE
                """,
                (user_id, created_at_ms, created_at_ms),
            )
            entitlement = cursor.fetchone()
            if entitlement is not None:
                cursor.execute(
                    "UPDATE billing_time_pass_entitlements SET knowledge_allowance_locked = knowledge_allowance_locked + 1 WHERE entitlement_id = %s",
                    (entitlement["entitlement_id"],),
                )
                cursor.execute(
                    """
                    INSERT INTO billing_index_reservations (
                      reservation_id, quote_id, user_id, document_version_id, points_reserved, status,
                      created_at_ms, billing_source, entitlement_id, allowance_reserved
                    ) VALUES (%s,%s,%s,%s,0,'reserved',%s,'pass_allowance',%s,1) RETURNING *
                    """,
                    (f"index-reservation-{uuid4().hex}", quote_id, user_id, quote["document_version_id"], created_at_ms, entitlement["entitlement_id"]),
                )
                result = self._reservation(cursor.fetchone())
                connection.commit()
                return result
            cursor.execute("SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s", (user_id,))
            balance = int(cursor.fetchone()["balance"])
            cursor.execute(
                """
                SELECT
                  COALESCE((SELECT SUM(points_reserved) FROM billing_index_reservations WHERE user_id = %s AND status = 'reserved'), 0)
                  + COALESCE((SELECT SUM(points_reserved) FROM billing_usage_reservations WHERE user_id = %s AND status = 'reserved'), 0)
                  AS reserved
                """,
                (user_id, user_id),
            )
            available = balance - int(cursor.fetchone()["reserved"])
            if available < int(quote["points_required"]):
                return {
                    "reservation_id": f"index-reservation-{uuid4().hex}", "quote_id": quote_id,
                    "user_id": user_id, "document_version_id": str(quote["document_version_id"]),
                    "points_reserved": int(quote["points_required"]), "status": "insufficient_balance",
                    "created_at_ms": created_at_ms, "settled_at_ms": None, "released_at_ms": None,
                    "billing_source": "points", "entitlement_id": None, "allowance_reserved": 0,
                }
            cursor.execute(
                """
                INSERT INTO billing_index_reservations (
                  reservation_id, quote_id, user_id, document_version_id, points_reserved, status, created_at_ms
                ) VALUES (%s,%s,%s,%s,%s,'reserved',%s) RETURNING *
                """,
                (
                    f"index-reservation-{uuid4().hex}", quote_id, user_id, quote["document_version_id"],
                    quote["points_required"], created_at_ms,
                ),
            )
            result = self._reservation(cursor.fetchone())
            connection.commit()
            return result

    def settle_index_quote(self, *, quote_id: str, reference_id: str, settled_at_ms: int) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_index_reservations WHERE quote_id = %s FOR UPDATE", (quote_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            if row["status"] != "reserved":
                return self._reservation(row)
            if row["billing_source"] == "pass_allowance" and row["entitlement_id"] is not None:
                cursor.execute(
                    "UPDATE billing_time_pass_entitlements SET knowledge_allowance_locked = GREATEST(0, knowledge_allowance_locked - %s), knowledge_allowance_used = knowledge_allowance_used + %s WHERE entitlement_id = %s",
                    (row["allowance_reserved"], row["allowance_reserved"], row["entitlement_id"]),
                )
            elif int(row["points_reserved"]) > 0:
                cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'knowledge_index_settlement',%s,%s,%s,%s)
                ON CONFLICT (reference_id) DO NOTHING
                """,
                (
                    f"ledger-{uuid4().hex}", row["user_id"], -int(row["points_reserved"]),
                    settled_at_ms, reference_id, "知识资料索引结算",
                ),
                )
            cursor.execute(
                "UPDATE billing_index_reservations SET status = 'settled', settled_at_ms = %s WHERE quote_id = %s RETURNING *",
                (settled_at_ms, quote_id),
            )
            result = self._reservation(cursor.fetchone())
            connection.commit()
            return result

    def release_index_quote(self, *, quote_id: str, released_at_ms: int) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_index_reservations WHERE quote_id = %s FOR UPDATE", (quote_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            if row["status"] != "reserved":
                return self._reservation(row)
            if row["billing_source"] == "pass_allowance" and row["entitlement_id"] is not None:
                cursor.execute(
                    "UPDATE billing_time_pass_entitlements SET knowledge_allowance_locked = GREATEST(0, knowledge_allowance_locked - %s) WHERE entitlement_id = %s",
                    (row["allowance_reserved"], row["entitlement_id"]),
                )
            cursor.execute(
                "UPDATE billing_index_reservations SET status = 'released', released_at_ms = %s WHERE quote_id = %s RETURNING *",
                (released_at_ms, quote_id),
            )
            result = self._reservation(cursor.fetchone())
            connection.commit()
            return result

    def reserved_index_quote_for_document(self, *, user_id: str, document_version_id: str) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM billing_index_reservations WHERE user_id = %s AND document_version_id = %s ORDER BY created_at_ms DESC, reservation_id DESC LIMIT 1",
                (user_id, document_version_id),
            )
            row = cursor.fetchone()
            return self._reservation(row) if row is not None else None

    def reserve_usage(self, *, usage: Mapping[str, object], created_at_ms: int) -> dict[str, object]:
        user_id = str(usage["user_id"])
        usage_id = str(usage["usage_id"])
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"billing-user:{user_id}",))
            cursor.execute("SELECT * FROM billing_usage_reservations WHERE usage_id = %s", (usage_id,))
            existing = cursor.fetchone()
            if existing:
                if str(existing["user_id"]) != user_id or str(existing["usage_kind"]) != str(usage["usage_kind"]):
                    raise PermissionError("Billing usage id belongs to a different operation.")
                return self._usage_reservation(existing)
            cursor.execute(
                """
                SELECT 1 FROM billing_time_pass_entitlements
                WHERE user_id = %s AND starts_at_ms <= %s AND ends_at_ms > %s
                LIMIT 1
                """,
                (user_id, created_at_ms, created_at_ms),
            )
            has_active_pass = cursor.fetchone() is not None and not bool(usage.get("wallet_only", False))
            points_reserved = 0 if has_active_pass else int(usage["points_reserved"])
            if points_reserved:
                cursor.execute("SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s", (user_id,))
                balance = int(cursor.fetchone()["balance"])
                cursor.execute(
                    """
                    SELECT
                      COALESCE((SELECT SUM(points_reserved) FROM billing_index_reservations WHERE user_id = %s AND status = 'reserved'), 0)
                      + COALESCE((SELECT SUM(points_reserved) FROM billing_usage_reservations WHERE user_id = %s AND status = 'reserved'), 0)
                      AS reserved
                    """,
                    (user_id, user_id),
                )
                if balance - int(cursor.fetchone()["reserved"]) < points_reserved:
                    return {
                        **dict(usage), "billing_source": "points", "status": "insufficient_balance",
                        "created_at_ms": created_at_ms, "settled_at_ms": None, "released_at_ms": None,
                    }
            cursor.execute(
                """
                INSERT INTO billing_usage_reservations (
                  reservation_id, usage_id, user_id, usage_kind, points_reserved,
                  billing_source, status, created_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,'reserved',%s)
                RETURNING *
                """,
                (
                    usage["reservation_id"], usage_id, user_id, usage["usage_kind"], points_reserved,
                    "time_pass" if has_active_pass else "points", created_at_ms,
                ),
            )
            result = self._usage_reservation(cursor.fetchone())
            connection.commit()
            return result

    def settle_usage(self, *, usage_id: str, settled_at_ms: int) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_usage_reservations WHERE usage_id = %s FOR UPDATE", (usage_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            if row["status"] != "reserved":
                return self._usage_reservation(row)
            ledger_kind = "pass_usage" if row["billing_source"] == "time_pass" else f"{row['usage_kind']}_settlement"
            description = (
                "会员权益实时面试使用"
                if row["billing_source"] == "time_pass" and row["usage_kind"] == "realtime_minute"
                else "会员权益回答使用"
                if row["billing_source"] == "time_pass"
                else "实时面试分钟积分结算"
                if row["usage_kind"] == "realtime_minute"
                else "截图回答积分结算"
                if row["usage_kind"] == "screenshot_answer"
                else "笔试模式入场积分结算"
                if row["usage_kind"] == "written_exam_entry"
                else "面试回答积分结算"
            )
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (reference_id) DO NOTHING
                """,
                (
                    f"ledger-{uuid4().hex}", row["user_id"], ledger_kind, -int(row["points_reserved"]),
                    settled_at_ms, f"usage:{usage_id}", description,
                ),
            )
            cursor.execute(
                "UPDATE billing_usage_reservations SET status = 'settled', settled_at_ms = %s WHERE usage_id = %s RETURNING *",
                (settled_at_ms, usage_id),
            )
            result = self._usage_reservation(cursor.fetchone())
            connection.commit()
            return result

    def release_usage(self, *, usage_id: str, released_at_ms: int) -> dict[str, object] | None:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_usage_reservations WHERE usage_id = %s FOR UPDATE", (usage_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            if row["status"] != "reserved":
                return self._usage_reservation(row)
            cursor.execute(
                "UPDATE billing_usage_reservations SET status = 'released', released_at_ms = %s WHERE usage_id = %s RETURNING *",
                (released_at_ms, usage_id),
            )
            result = self._usage_reservation(cursor.fetchone())
            connection.commit()
            return result

    def release_stale_usage_reservations(
        self,
        *,
        stale_before_ms: int,
        released_at_ms: int,
        user_id: str | None = None,
    ) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE billing_usage_reservations
                SET status = 'released', released_at_ms = %s
                WHERE status = 'reserved'
                  AND created_at_ms < %s
                  AND (%s::TEXT IS NULL OR user_id = %s)
                """,
                (released_at_ms, stale_before_ms, user_id, user_id),
            )
            released = int(cursor.rowcount)
            connection.commit()
            return released

    def list_entitlements(self, *, user_id: str) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            try:
                cursor.execute(
                    """
                    SELECT entitlement_id, user_id, product_id, starts_at_ms, ends_at_ms,
                           order_id, knowledge_allowance_granted, knowledge_allowance_used,
                           knowledge_allowance_locked
                    FROM billing_time_pass_entitlements
                    WHERE user_id = %s
                    UNION ALL
                    SELECT entitlement_id, user_id, product_id, starts_at_ms, ends_at_ms,
                           reference_id AS order_id, 0, 0, 0
                    FROM admin_time_entitlements
                    WHERE user_id = %s
                    ORDER BY starts_at_ms
                    """,
                    (user_id, user_id),
                )
            except psycopg.errors.UndefinedTable:
                connection.rollback()
                cursor.execute(
                    "SELECT * FROM billing_time_pass_entitlements WHERE user_id = %s ORDER BY starts_at_ms",
                    (user_id,),
                )
            return [self._entitlement(row) for row in cursor.fetchall()]

    def expire_checkout_orders(self, *, now_ms: int, user_id: str | None = None, order_id: str | None = None) -> int:
        clauses = ["status = 'payment_pending'", "expires_at_ms <= %s"]
        params: list[object] = [now_ms]
        if user_id is not None:
            clauses.append("user_id = %s")
            params.append(user_id)
        if order_id is not None:
            clauses.append("order_id = %s")
            params.append(order_id)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE billing_checkout_orders SET status = 'expired', failure_reason = 'checkout_expired', updated_at_ms = %s WHERE {' AND '.join(clauses)}",
                (now_ms, *params),
            )
            count = cursor.rowcount
            connection.commit()
            return count

    def record_payment_callback(self, *, event: Mapping[str, object]) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO billing_payment_callback_events (
                  event_fingerprint, provider, order_id, provider_trade_no, amount_cents,
                  signature_verified, app_identity_verified, seller_identity_verified,
                  paid, outcome, first_received_at_ms, last_received_at_ms
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'received',%s,%s)
                ON CONFLICT (event_fingerprint) DO UPDATE SET
                  delivery_count = billing_payment_callback_events.delivery_count + 1,
                  last_received_at_ms = EXCLUDED.last_received_at_ms
                RETURNING *
                """,
                (
                    event["event_fingerprint"], event["provider"], event["order_id"], event["provider_trade_no"],
                    event["amount_cents"], event["signature_verified"], event.get("app_identity_verified"),
                    event.get("seller_identity_verified"), event["paid"],
                    event["received_at_ms"], event["received_at_ms"],
                ),
            )
            row = dict(cursor.fetchone())
            connection.commit()
            return row

    def complete_payment_callback(self, *, event_fingerprint: str, outcome: str, completed_at_ms: int, order_known: bool | None = None, amount_matches: bool | None = None) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE billing_payment_callback_events SET outcome = %s, completed_at_ms = %s, order_known = %s, amount_matches = %s WHERE event_fingerprint = %s",
                (outcome, completed_at_ms, order_known, amount_matches, event_fingerprint),
            )
            connection.commit()

    def create_reconciliation_issue(self, *, issue_type: str, event_fingerprint: str, order_id: str, detected_at_ms: int) -> None:
        safe_reference = order_id[-12:] if order_id else "missing-order"
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO billing_reconciliation_issues (
                  issue_id, issue_type, event_fingerprint, order_id, safe_reference, status, detected_at_ms
                ) VALUES (%s,%s,%s,%s,%s,'open',%s)
                ON CONFLICT (issue_type, event_fingerprint) DO NOTHING
                """,
                (f"reconciliation-{uuid4().hex}", issue_type, event_fingerprint, order_id, safe_reference, detected_at_ms),
            )
            connection.commit()

    def reconciliation_summary(self, *, now_ms: int) -> dict[str, object]:
        self.expire_checkout_orders(now_ms=now_ms)
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT status, COUNT(*) AS count FROM billing_checkout_orders GROUP BY status")
            orders = {str(row["status"]): int(row["count"]) for row in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) AS count FROM billing_payment_callback_events")
            callback_events = int(cursor.fetchone()["count"])
            cursor.execute("SELECT COUNT(*) AS count FROM billing_payment_callback_events WHERE outcome NOT IN ('paid', 'ignored_not_paid')")
            callback_failures = int(cursor.fetchone()["count"])
            cursor.execute(
                "SELECT issue_type, safe_reference, detected_at_ms FROM billing_reconciliation_issues WHERE status = 'open' ORDER BY detected_at_ms DESC LIMIT 50"
            )
            issues = [
                {
                    "issueType": str(row["issue_type"]), "safeReference": str(row["safe_reference"]),
                    "detectedAtMs": int(row["detected_at_ms"]),
                }
                for row in cursor.fetchall()
            ]
            return {
                "generatedAtMs": now_ms,
                "orders": {
                    "paymentPending": orders.get("payment_pending", 0), "expired": orders.get("expired", 0),
                    "paid": orders.get("paid", 0), "failed": orders.get("failed", 0),
                },
                "callbackEvents": callback_events,
                "callbackFailures": callback_failures,
                "openIssues": len(issues),
                "issues": issues,
            }

    @staticmethod
    def _ledger(row) -> dict[str, object]:
        return {
            "id": str(row["ledger_entry_id"]), "user_id": str(row["user_id"]), "kind": str(row["kind"]),
            "points": int(row["points"]), "created_at_ms": int(row["created_at_ms"]),
            "reference_id": str(row["reference_id"]), "description": str(row["description"]),
        }

    @staticmethod
    def _order(row) -> dict[str, object]:
        return {
            "id": str(row["order_id"]), "user_id": str(row["user_id"]), "product": dict(row["product_snapshot"]),
            "amount_cents": int(row["amount_cents"]), "currency": str(row["currency"]), "channel": str(row["channel"]),
            "provider": str(row["provider"]),
            "status": str(row["status"]), "action": dict(row["action"]), "created_at_ms": int(row["created_at_ms"]),
            "updated_at_ms": int(row["updated_at_ms"]), "provider_trade_no": row["provider_trade_no"],
            "paid_at_ms": int(row["paid_at_ms"]) if row["paid_at_ms"] is not None else None,
        }

    @staticmethod
    def _quote(row) -> dict[str, object]:
        return {
            "quote_id": str(row["quote_id"]), "user_id": str(row["user_id"]),
            "document_version_id": str(row["document_version_id"]), "token_estimate": int(row["token_estimate"]),
            "catalog_version": int(row["catalog_version"]), "tokenizer_version": str(row["tokenizer_version"]),
            "points_required": int(row["points_required"]), "projected_balance": int(row["projected_balance"]),
            "created_at_ms": int(row["created_at_ms"]),
        }

    @staticmethod
    def _reservation(row) -> dict[str, object]:
        return {
            "reservation_id": str(row["reservation_id"]), "quote_id": str(row["quote_id"]),
            "user_id": str(row["user_id"]), "document_version_id": str(row["document_version_id"]),
            "points_reserved": int(row["points_reserved"]), "status": str(row["status"]),
            "created_at_ms": int(row["created_at_ms"]),
            "settled_at_ms": int(row["settled_at_ms"]) if row["settled_at_ms"] is not None else None,
            "released_at_ms": int(row["released_at_ms"]) if row["released_at_ms"] is not None else None,
            "billing_source": str(row.get("billing_source") or "points"),
            "entitlement_id": str(row["entitlement_id"]) if row.get("entitlement_id") is not None else None,
            "allowance_reserved": int(row.get("allowance_reserved") or 0),
        }

    @staticmethod
    def _usage_reservation(row) -> dict[str, object]:
        return {
            "reservation_id": str(row["reservation_id"]), "usage_id": str(row["usage_id"]),
            "user_id": str(row["user_id"]), "usage_kind": str(row["usage_kind"]),
            "points_reserved": int(row["points_reserved"]), "billing_source": str(row["billing_source"]),
            "status": str(row["status"]), "created_at_ms": int(row["created_at_ms"]),
            "settled_at_ms": int(row["settled_at_ms"]) if row["settled_at_ms"] is not None else None,
            "released_at_ms": int(row["released_at_ms"]) if row["released_at_ms"] is not None else None,
        }

    @staticmethod
    def _entitlement(row) -> dict[str, object]:
        return {
            "id": str(row["entitlement_id"]), "user_id": str(row["user_id"]), "product_id": str(row["product_id"]),
            "starts_at_ms": int(row["starts_at_ms"]), "ends_at_ms": int(row["ends_at_ms"]),
            "order_id": str(row["order_id"]), "knowledge_allowance_granted": int(row["knowledge_allowance_granted"]),
            "knowledge_allowance_used": int(row["knowledge_allowance_used"]),
            "knowledge_allowance_locked": int(row["knowledge_allowance_locked"]),
        }

    def _connect(self):
        return psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-billing",
        )

    def _ensure_tables(self) -> None:
        migrations = [
            Path(REPO_ROOT / "apps/backend/migrations/versions/0008_persistent_points_redemption.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0009_commercial_billing_persistence.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0010_payment_recovery_reconciliation.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0012_billable_interview_usage.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0013_official_alipay_payments.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0018_admin_managed_billing_catalog.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0019_admin_payment_channels.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0020_admin_payment_diagnostics.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0021_referral_rewards.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0022_referral_ledger_constraint_repair.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0023_stale_usage_reservation_recovery.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0025_referral_ledger_constraint_repair_v2.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0027_knowledge_index_billing_sources.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0029_early_referral_mutual_rewards.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0032_realtime_minute_billing.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0037_written_exam_billing_constraints.sql"),
        ]
        if self.settings.partner_program_enabled:
            migrations.extend((
                Path(REPO_ROOT / "apps/backend/migrations/versions/0038_promotion_center.sql"),
                Path(REPO_ROOT / "apps/backend/migrations/versions/0039_partner_program.sql"),
            ))
        with self._connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, migrations)
            connection.commit()
