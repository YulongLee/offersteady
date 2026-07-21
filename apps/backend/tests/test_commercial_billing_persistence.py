from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.billing_service import BillingService
from app.services.postgres_billing_repository import PostgresBillingRepository


DATABASE_URL = os.getenv("OFFERSTEADY_TEST_DATABASE_URL")


def service_for_test() -> BillingService:
    settings = Settings(_env_file=None, database_url=DATABASE_URL, environment="test")
    return BillingService(settings, billing_repository=PostgresBillingRepository(settings))


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_wallet_order_and_duplicate_callback_survive_restart() -> None:
    user_id = f"billing-test-{uuid4().hex}"
    service = service_for_test()
    assert service.state_for_user(user_id=user_id).balance == 200
    order = service.create_checkout_order(
        user_id=user_id, product_id="points-300", channel="alipay",
        idempotency_key="checkout-1", payment_url="#", expires_at_ms=9999999999999,
    )
    order = service.replace_checkout_action(order_id=order.id, payment_url="https://payment.example/order", expires_at_ms=9999999999999)
    service.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents, provider_trade_no=f"trade-{uuid4().hex}")
    service.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents, provider_trade_no=f"duplicate-{uuid4().hex}")

    restarted = service_for_test()
    state = restarted.state_for_user(user_id=user_id)
    assert state.balance == 500
    assert len([item for item in state.ledger if item.kind == "welcome_grant"]) == 1
    assert len([item for item in state.ledger if item.kind == "purchase_credit"]) == 1
    assert state.official_orders[0]["status"] == "paid"


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_concurrent_index_reservations_cannot_overspend() -> None:
    user_id = f"billing-reservation-{uuid4().hex}"
    service = service_for_test()
    service.state_for_user(user_id=user_id)
    quotes = [
        service.quote_knowledge_index(
            user_id=user_id, document_version_id=f"document-{index}", token_estimate=30_000,
            idempotency_key=f"quote-{index}",
        )
        for index in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        reservations = list(pool.map(
            lambda quote: service_for_test().reserve_knowledge_index(user_id=user_id, quote_id=quote.quote_id),
            quotes,
        ))
    assert sorted(item.status for item in reservations) == ["insufficient_balance", "reserved"]

