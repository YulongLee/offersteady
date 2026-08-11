from __future__ import annotations

import hashlib
import hmac
import re
from time import time
from typing import Mapping
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.core.config import REPO_ROOT, Settings
from app.services.postgres_migrations import apply_sql_migrations
from app.ports.points_redemption import (
    PersistedPointsLedgerEntry,
    PersistedPointsRedemption,
    PersistedRedemptionResult,
    PointsRedemptionRepository,
)


def _now_ms() -> int:
    return int(time() * 1000)


class PostgresPointsRedemptionRepository(PointsRedemptionRepository):
    def __init__(self, settings: Settings) -> None:
        if not settings.redemption_code_pepper:
            raise RuntimeError("OFFERSTEADY_REDEMPTION_CODE_PEPPER is required for persistent redemption codes")
        self.settings = settings
        self._pepper = settings.redemption_code_pepper.encode("utf8")
        self._ensure_tables()

    def sync_configured_codes(self, codes: Mapping[str, int]) -> None:
        now_ms = _now_ms()
        rows = [
            (self._digest(code), f"****-{code[-4:]}", int(points), now_ms, now_ms)
            for code, points in codes.items()
            if code and int(points) > 0
        ]
        if not rows:
            return
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO points_redemption_codes (
                  code_digest, public_hint, points, status, created_at_ms, updated_at_ms
                ) VALUES (%s,%s,%s,'active',%s,%s)
                ON CONFLICT (code_digest) DO UPDATE SET
                  public_hint = EXCLUDED.public_hint,
                  points = EXCLUDED.points,
                  updated_at_ms = EXCLUDED.updated_at_ms
                WHERE points_redemption_codes.status = 'active'
                """,
                rows,
            )
            connection.commit()

    def redeem(self, *, user_id: str, code: str, idempotency_key: str) -> PersistedRedemptionResult:
        digests = self._digests(code)
        digest = digests[0]
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"{user_id}:{idempotency_key}",))
            cursor.execute(
                "SELECT * FROM points_redemptions WHERE user_id = %s AND idempotency_key = %s",
                (user_id, idempotency_key),
            )
            replay = cursor.fetchone()
            if replay:
                return PersistedRedemptionResult(outcome="redeemed", redemption=self._redemption_from_row(cursor, replay))

            code_row = None
            for candidate_digest in digests:
                cursor.execute("SELECT * FROM points_redemption_codes WHERE code_digest = %s FOR UPDATE", (candidate_digest,))
                code_row = cursor.fetchone()
                if code_row is not None:
                    digest = candidate_digest
                    break
            if (
                not code_row
                or code_row["status"] != "active"
                or (
                    code_row.get("expires_at_ms") is not None
                    and int(code_row["expires_at_ms"]) <= _now_ms()
                )
            ):
                if code_row and code_row["redeemed_by_user_id"] == user_id:
                    cursor.execute("SELECT * FROM points_redemptions WHERE code_digest = %s", (digest,))
                    prior = cursor.fetchone()
                    if prior:
                        return PersistedRedemptionResult(
                            outcome="already-redeemed-by-you",
                            redemption=self._redemption_from_row(cursor, prior),
                        )
                return PersistedRedemptionResult(outcome="code-unavailable")

            redeemed_at_ms = _now_ms()
            redemption_id = f"redemption-{uuid4().hex}"
            ledger_entry_id = f"ledger-{uuid4().hex}"
            cursor.execute(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s",
                (user_id,),
            )
            persisted_balance = int(cursor.fetchone()["balance"]) + int(code_row["points"])
            reference_id = f"redemption:{redemption_id}"
            cursor.execute(
                """
                INSERT INTO points_redemption_ledger (
                  ledger_entry_id, user_id, kind, points, created_at_ms, reference_id, description
                ) VALUES (%s,%s,'redemption_credit',%s,%s,%s,%s)
                """,
                (ledger_entry_id, user_id, int(code_row["points"]), redeemed_at_ms, reference_id, "兑换码积分入账"),
            )
            cursor.execute(
                """
                INSERT INTO points_redemptions (
                  redemption_id, code_digest, user_id, idempotency_key, points,
                  persisted_balance, public_hint, redeemed_at_ms, ledger_entry_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING *
                """,
                (
                    redemption_id,
                    digest,
                    user_id,
                    idempotency_key,
                    int(code_row["points"]),
                    persisted_balance,
                    str(code_row["public_hint"]),
                    redeemed_at_ms,
                    ledger_entry_id,
                ),
            )
            redemption_row = cursor.fetchone()
            cursor.execute(
                """
                UPDATE points_redemption_codes
                SET status = 'redeemed', redeemed_by_user_id = %s, redeemed_at_ms = %s,
                    redemption_id = %s, updated_at_ms = %s
                WHERE code_digest = %s
                """,
                (user_id, redeemed_at_ms, redemption_id, redeemed_at_ms, digest),
            )
            connection.commit()
            return PersistedRedemptionResult(outcome="redeemed", redemption=self._redemption_from_row(cursor, redemption_row))

    def list_ledger(self, *, user_id: str) -> list[PersistedPointsLedgerEntry]:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM points_redemption_ledger WHERE user_id = %s ORDER BY created_at_ms DESC, ledger_entry_id DESC",
                (user_id,),
            )
            return [self._ledger_from_row(row) for row in cursor.fetchall()]

    def balance(self, *, user_id: str) -> int:
        with self._connect() as connection, connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(points), 0) AS balance FROM points_redemption_ledger WHERE user_id = %s",
                (user_id,),
            )
            return int(cursor.fetchone()["balance"])

    def _redemption_from_row(self, cursor, row) -> PersistedPointsRedemption:
        cursor.execute(
            "SELECT * FROM points_redemption_ledger WHERE ledger_entry_id = %s",
            (row["ledger_entry_id"],),
        )
        ledger_row = cursor.fetchone()
        if ledger_row is None:
            raise RuntimeError("persisted redemption ledger entry is missing")
        return PersistedPointsRedemption(
            redemption_id=str(row["redemption_id"]),
            points=int(row["points"]),
            persisted_balance=int(row["persisted_balance"]),
            public_hint=str(row["public_hint"]),
            redeemed_at_ms=int(row["redeemed_at_ms"]),
            ledger_entry=self._ledger_from_row(ledger_row),
        )

    @staticmethod
    def _ledger_from_row(row) -> PersistedPointsLedgerEntry:
        return PersistedPointsLedgerEntry(
            id=str(row["ledger_entry_id"]),
            user_id=str(row["user_id"]),
            kind=str(row["kind"]),
            points=int(row["points"]),
            created_at_ms=int(row["created_at_ms"]),
            reference_id=str(row["reference_id"]),
            description=str(row["description"]),
        )

    def _digest(self, code: str) -> str:
        return hmac.new(self._pepper, code.strip().upper().encode("utf8"), hashlib.sha256).hexdigest()

    def _digests(self, code: str) -> list[str]:
        normalized = code.strip().upper()
        compact = re.sub(r"[\s-]+", "", normalized)
        candidates = [normalized]
        if compact and compact not in candidates:
            candidates.append(compact)
        if len(compact) == 16:
            grouped = "-".join(compact[index:index + 4] for index in range(0, 16, 4))
            if grouped not in candidates:
                candidates.append(grouped)
        return [self._digest(candidate) for candidate in candidates]

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("database_url is required for points redemption persistence")
        return psycopg.connect(
            self.settings.database_url,
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name=f"{self.settings.database_application_name}-redemption",
        )

    def _ensure_tables(self) -> None:
        migrations = [
            REPO_ROOT / "apps" / "backend" / "migrations" / "versions" / "0008_persistent_points_redemption.sql",
            REPO_ROOT / "apps" / "backend" / "migrations" / "versions" / "0015_admin_redemption_batches.sql",
            REPO_ROOT / "apps" / "backend" / "migrations" / "versions" / "0022_referral_ledger_constraint_repair.sql",
        ]
        with self._connect() as connection, connection.cursor() as cursor:
            apply_sql_migrations(cursor, migrations)
            connection.commit()
