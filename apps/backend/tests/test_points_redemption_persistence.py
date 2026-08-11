from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.ports.points_redemption import (
    PersistedPointsLedgerEntry,
    PersistedPointsRedemption,
    PersistedRedemptionResult,
)
from app.services.billing_service import BillingService
from app.services.postgres_points_redemption_repository import PostgresPointsRedemptionRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


def test_database_generated_code_bypasses_static_configuration() -> None:
    ledger_entry = PersistedPointsLedgerEntry(
        id="ledger-generated-code",
        user_id="generated-code-user",
        kind="redemption_credit",
        points=2000,
        created_at_ms=1_800_000_000_000,
        reference_id="redemption:generated-code",
        description="兑换码积分入账",
    )

    class RedemptionRepositoryStub:
        def sync_configured_codes(self, codes) -> None:
            pass

        def redeem(self, *, user_id: str, code: str, idempotency_key: str) -> PersistedRedemptionResult:
            assert code == "ABCD-EFGH-JKLM-NPQR"
            return PersistedRedemptionResult(
                outcome="redeemed",
                redemption=PersistedPointsRedemption(
                    redemption_id="generated-code",
                    points=2000,
                    persisted_balance=2000,
                    public_hint="****-NPQR",
                    redeemed_at_ms=1_800_000_000_000,
                    ledger_entry=ledger_entry,
                ),
            )

        def list_ledger(self, *, user_id: str):
            return [ledger_entry]

        def balance(self, *, user_id: str) -> int:
            return 2000

    service = BillingService(Settings(environment="production"), redemption_repository=RedemptionRepositoryStub())
    result = service.redeem_points(
        user_id="generated-code-user",
        code="ABCD-EFGH-JKLM-NPQR",
        idempotency_key="generated-code-request",
    )

    assert result["outcome"] == "redeemed"
    assert result["data"]["points"] == 2000
    assert result["data"]["newBalance"] == 2000


def test_redemption_digest_candidates_accept_grouped_compact_and_spaced_input() -> None:
    repository = object.__new__(PostgresPointsRedemptionRepository)
    repository._pepper = b"synthetic-pepper"

    grouped = repository._digests("ABCD-EFGH-JKLM-NPQR")
    compact = repository._digests("ABCDEFGHJKLMNPQR")
    spaced = repository._digests("ABCD EFGH JKLM NPQR")

    assert grouped[0] in compact
    assert grouped[0] in spaced


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_configured_code_is_private_atomic_and_survives_repository_restart() -> None:
    code = f"TEST-{uuid4().hex.upper()}"
    test_run_id = uuid4().hex
    users = (f"redemption-user-a-{test_run_id}", f"redemption-user-b-{test_run_id}")
    settings = Settings(
        database_url=DATABASE_URL,
        redemption_code_pepper=f"pepper-{uuid4().hex}",
        redemption_code_points={code: 2000},
    )
    repository = PostgresPointsRedemptionRepository(settings)
    repository.sync_configured_codes(settings.redemption_code_points)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(
            lambda user: repository.redeem(user_id=user, code=code, idempotency_key=f"request-{user}"),
            users,
        ))
    assert sorted(item.outcome for item in outcomes) == ["code-unavailable", "redeemed"]
    winner = next(item for item in outcomes if item.outcome == "redeemed")
    assert winner.redemption is not None
    winner_user = winner.redemption.ledger_entry.user_id

    restarted = PostgresPointsRedemptionRepository(settings)
    replay = restarted.redeem(user_id=winner_user, code=code, idempotency_key=f"request-{winner_user}")
    assert replay.outcome == "redeemed"
    assert restarted.balance(user_id=winner_user) == 2000
    assert len(restarted.list_ledger(user_id=winner_user)) == 1

    loser = users[1] if winner_user == users[0] else users[0]
    assert restarted.redeem(user_id=loser, code=code, idempotency_key="retry").outcome == "code-unavailable"

    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM points_redemption_codes WHERE code_digest = %s", (code,))
        assert cursor.fetchone()[0] == 0
