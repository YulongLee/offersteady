from __future__ import annotations

from json import dumps
from pathlib import Path
from typing import Mapping
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings


class PostgresBillingRepository:
    def __init__(self, settings: Settings) -> None:
        if not settings.database_url:
            raise RuntimeError("OFFERSTEADY_DATABASE_URL is required for persistent billing")
        self.settings = settings
        self._ensure_tables()

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
                  currency, channel, status, action, created_at_ms, updated_at_ms
                ) VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s::jsonb,%s,%s)
                RETURNING *
                """,
                (
                    order["id"], order["user_id"], idempotency_key, dumps(order["product"]),
                    order["amount_cents"], order["currency"], order["channel"], order["status"],
                    dumps(order["action"]), order["created_at_ms"], order["updated_at_ms"],
                ),
            )
            result = self._order(cursor.fetchone())
            connection.commit()
            return result

    def replace_checkout_action(self, *, order_id: str, action: Mapping[str, object], updated_at_ms: int) -> dict[str, object]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "UPDATE billing_checkout_orders SET action = %s::jsonb, updated_at_ms = %s WHERE order_id = %s RETURNING *",
                (dumps(dict(action)), updated_at_ms, order_id),
            )
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
                    "UPDATE billing_checkout_orders SET status = 'failed', provider_trade_no = %s, updated_at_ms = %s WHERE order_id = %s RETURNING *",
                    (provider_trade_no, paid_at_ms, order_id),
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
                starts_at_ms = max(paid_at_ms, int(cursor.fetchone()["latest_end"]))
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
                SET status = 'paid', provider_trade_no = %s, paid_at_ms = %s, updated_at_ms = %s
                WHERE order_id = %s RETURNING *
                """,
                (provider_trade_no, paid_at_ms, paid_at_ms, order_id),
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
            cursor.execute("SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s", (user_id,))
            balance = int(cursor.fetchone()["balance"])
            cursor.execute(
                "SELECT COALESCE(SUM(points_reserved), 0) AS reserved FROM billing_index_reservations WHERE user_id = %s AND status = 'reserved'",
                (user_id,),
            )
            available = balance - int(cursor.fetchone()["reserved"])
            if available < int(quote["points_required"]):
                return {
                    "reservation_id": f"index-reservation-{uuid4().hex}", "quote_id": quote_id,
                    "user_id": user_id, "document_version_id": str(quote["document_version_id"]),
                    "points_reserved": int(quote["points_required"]), "status": "insufficient_balance",
                    "created_at_ms": created_at_ms, "settled_at_ms": None, "released_at_ms": None,
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
            cursor.execute(
                "UPDATE billing_index_reservations SET status = 'released', released_at_ms = %s WHERE quote_id = %s RETURNING *",
                (released_at_ms, quote_id),
            )
            result = self._reservation(cursor.fetchone())
            connection.commit()
            return result

    def list_entitlements(self, *, user_id: str) -> list[dict[str, object]]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM billing_time_pass_entitlements WHERE user_id = %s ORDER BY starts_at_ms", (user_id,))
            return [self._entitlement(row) for row in cursor.fetchall()]

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
        migrations = (
            Path(REPO_ROOT / "apps/backend/migrations/versions/0008_persistent_points_redemption.sql"),
            Path(REPO_ROOT / "apps/backend/migrations/versions/0009_commercial_billing_persistence.sql"),
        )
        with self._connect() as connection, connection.cursor() as cursor:
            for migration in migrations:
                cursor.execute(migration.read_text(encoding="utf8"))
            connection.commit()

