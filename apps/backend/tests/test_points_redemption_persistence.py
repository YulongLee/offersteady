from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.services.postgres_points_redemption_repository import PostgresPointsRedemptionRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_configured_code_is_private_atomic_and_survives_repository_restart() -> None:
    code = f"TEST-{uuid4().hex.upper()}"
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
            ("redemption-user-a", "redemption-user-b"),
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

    loser = "redemption-user-b" if winner_user == "redemption-user-a" else "redemption-user-a"
    assert restarted.redeem(user_id=loser, code=code, idempotency_key="retry").outcome == "code-unavailable"

    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM points_redemption_codes WHERE code_digest = %s", (code,))
        assert cursor.fetchone()[0] == 0
