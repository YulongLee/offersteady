from __future__ import annotations

import os
from time import time
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.services.billing_service import BillingService
from app.services.postgres_billing_repository import PostgresBillingRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="Isolated test PostgreSQL is not configured")


def make_service():
    settings = Settings(_env_file=None, environment="test", database_url=DATABASE_URL)
    return BillingService(settings, billing_repository=PostgresBillingRepository(settings))


@pytest.mark.parametrize("kind,minimum_days,product,expected", [
    ("answer", None, None, "insufficient_balance"),
    ("screenshot_answer", None, None, "insufficient_balance"),
    ("web_answer", 7, None, "insufficient_balance"),
    ("web_answer", 7, "pass-3", "insufficient_balance"),
    ("answer", None, "pass-3", "reserved"),
    ("web_answer", 7, "pass-7", "reserved"),
])
def test_real_postgres_zero_wallet_and_pass_policy(kind, minimum_days, product, expected):
    service = make_service()
    user_id = f"synthetic-failure-contract-{uuid4().hex}"
    usage_id = f"synthetic-usage-{uuid4().hex}"
    assert service.state_for_user(user_id=user_id).balance == 200
    if product:
        order = service.create_checkout_order(
            user_id=user_id, product_id=product, channel="alipay", idempotency_key="synthetic-checkout",
            payment_url="https://synthetic.invalid", expires_at_ms=9_999_999_999_999,
        )
        service.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents,
                                      provider_trade_no=f"synthetic-trade-{uuid4().hex}")
    with psycopg.connect(DATABASE_URL) as connection:
        connection.execute(
            """INSERT INTO points_redemption_ledger
               (ledger_entry_id,user_id,kind,points,created_at_ms,reference_id,description)
               VALUES (%s,%s,'admin_adjustment',-200,%s,%s,'Synthetic zero-wallet fixture')""",
            (f"synthetic-ledger-{uuid4().hex}", user_id, int(time() * 1000), f"synthetic:{user_id}"),
        )
    reservation = service.reserve_usage(user_id=user_id, usage_id=usage_id, usage_kind=kind,
                                        minimum_pass_duration_days=minimum_days)
    assert reservation.status == expected
    if expected == "reserved":
        assert reservation.billing_source == "time_pass"
        assert reservation.points_reserved == 0
        replay = service.reserve_usage(user_id=user_id, usage_id=usage_id, usage_kind=kind,
                                       minimum_pass_duration_days=minimum_days)
        assert replay.reservation_id == reservation.reservation_id
        service.settle_usage(usage_id=usage_id)
        service.settle_usage(usage_id=usage_id)
    else:
        with psycopg.connect(DATABASE_URL) as connection:
            assert connection.execute("SELECT count(*) FROM billing_usage_reservations WHERE usage_id=%s",
                                      (usage_id,)).fetchone()[0] == 0
    assert service.state_for_user(user_id=user_id).balance == 0


def test_real_postgres_success_settles_once_and_failed_usage_releases_points():
    service = make_service()
    user_id = f"synthetic-success-contract-{uuid4().hex}"
    answer_id = f"synthetic-answer-{uuid4().hex}"
    first = service.reserve_usage(user_id=user_id, usage_id=answer_id, usage_kind="answer")
    assert first.status == "reserved"
    replay = service.reserve_usage(user_id=user_id, usage_id=answer_id, usage_kind="answer")
    assert replay.reservation_id == first.reservation_id
    service.settle_usage(usage_id=answer_id)
    service.settle_usage(usage_id=answer_id)
    assert service.state_for_user(user_id=user_id).balance == 195
    for kind, minimum_days in [("web_answer", 7), ("screenshot_answer", None)]:
        usage_id = f"synthetic-release-{uuid4().hex}"
        reservation = service.reserve_usage(user_id=user_id, usage_id=usage_id, usage_kind=kind,
                                            minimum_pass_duration_days=minimum_days)
        assert reservation.status == "reserved"
        assert service.release_usage(usage_id=usage_id).status == "released"
        assert service.release_usage(usage_id=usage_id).status == "released"
        assert service.settle_usage(usage_id=usage_id).status == "released"
        assert service.state_for_user(user_id=user_id).balance == 195
