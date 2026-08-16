from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from time import time
from uuid import uuid4

import psycopg
import pytest

from app.core.config import Settings
from app.ports.authentication import UserRecord
from app.services.billing_service import BillingService, TimePassEntitlementRecord
from app.services.postgres_authentication_repository import PostgresAuthenticationRepository
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
        user_id=user_id, product_id="points-1000", channel="alipay",
        idempotency_key="checkout-1", payment_url="#", expires_at_ms=9999999999999,
    )
    order = service.replace_checkout_action(order_id=order.id, payment_url="https://payment.example/order", expires_at_ms=9999999999999)
    service.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents, provider_trade_no=f"trade-{uuid4().hex}")
    service.confirm_checkout_paid(order_id=order.id, amount_cents=order.amount_cents, provider_trade_no=f"duplicate-{uuid4().hex}")

    restarted = service_for_test()
    state = restarted.state_for_user(user_id=user_id)
    assert state.balance == 1200
    assert len([item for item in state.ledger if item.kind == "welcome_grant"]) == 1
    assert len([item for item in state.ledger if item.kind == "purchase_credit"]) == 1
    assert state.official_orders[0]["status"] == "paid"


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_paid_pass_stacks_after_active_admin_entitlement_and_remains_idempotent() -> None:
    settings = Settings(_env_file=None, database_url=DATABASE_URL, environment="test")
    user_id = f"billing-cross-source-pass-{uuid4().hex}"
    admin_reference = f"admin-pass-{uuid4().hex}"
    auth = PostgresAuthenticationRepository(settings)
    current_ms = int(time() * 1000)
    auth.save_user(UserRecord(
        user_id=user_id,
        login_id=f"{user_id}@example.invalid",
        password_hash="synthetic-not-a-real-password",
        display_name="Synthetic membership test user",
        avatar_url=None,
        last_login_provider="prototype",
        last_login_at_ms=current_ms,
        created_at_ms=current_ms,
        updated_at_ms=current_ms,
    ))
    admin_end_ms = current_ms + 6 * 86_400_000
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_time_entitlements (
              entitlement_id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              product_id TEXT NOT NULL DEFAULT 'admin-time-adjustment',
              starts_at_ms BIGINT NOT NULL,
              ends_at_ms BIGINT NOT NULL,
              reference_id TEXT NOT NULL UNIQUE,
              reason TEXT NOT NULL,
              created_by_user_id TEXT NOT NULL,
              created_at_ms BIGINT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO admin_time_entitlements (
              entitlement_id, user_id, starts_at_ms, ends_at_ms, reference_id,
              reason, created_by_user_id, created_at_ms
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                f"admin-entitlement-{uuid4().hex}", user_id, current_ms, admin_end_ms,
                admin_reference, "synthetic cross-source stacking test", "synthetic-admin", current_ms,
            ),
        )
        connection.commit()
    service = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    order = service.create_checkout_order(
        user_id=user_id,
        product_id="pass-1",
        channel="wechat",
        idempotency_key="cross-source-pass",
        payment_url="#",
        expires_at_ms=9_999_999_999_999,
    )
    first = service.confirm_checkout_paid(
        order_id=order.id,
        amount_cents=order.amount_cents,
        provider_trade_no=f"trade-{uuid4().hex}",
    )
    replay = service.confirm_checkout_paid(
        order_id=order.id,
        amount_cents=order.amount_cents,
        provider_trade_no=f"duplicate-{uuid4().hex}",
    )

    state = service_for_test().state_for_user(user_id=user_id)
    assert first.status == replay.status == "paid"
    assert state.active_pass is not None
    assert state.active_pass["orderId"] == admin_reference
    assert len(state.queued_passes) == 1
    paid_entitlement = state.queued_passes[0]
    assert paid_entitlement["orderId"] == order.id
    assert paid_entitlement["startsAtMs"] == admin_end_ms
    assert paid_entitlement["endsAtMs"] - paid_entitlement["startsAtMs"] == 86_400_000


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_rejected_provider_checkout_is_persisted_as_failed() -> None:
    user_id = f"billing-provider-failure-{uuid4().hex}"
    service = service_for_test()
    order = service.create_checkout_order(
        user_id=user_id,
        product_id="pass-1",
        channel="wechat",
        provider="wechat",
        idempotency_key="rejected-native-order",
        payment_url="#",
        expires_at_ms=9_999_999_999_999,
    )

    service.mark_checkout_failed(
        order_id=order.id,
        failure_reason="wechat_native_400_param_error",
    )

    restarted = service_for_test()
    persisted = restarted.checkout_order_for_user(user_id=user_id, order_id=order.id)
    assert persisted.status == "failed"
    assert persisted.action == {"kind": "unavailable"}


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


def test_member_knowledge_allowance_is_locked_settled_and_released_without_points() -> None:
    service = BillingService(Settings(_env_file=None, environment="test"))
    user_id = f"member-index-{uuid4().hex}"
    now_ms = int(time() * 1000)
    service.pass_entitlements_by_user[user_id] = [TimePassEntitlementRecord(
        id="member-index-entitlement",
        user_id=user_id,
        product_id="pass-15",
        starts_at_ms=now_ms - 1_000,
        ends_at_ms=now_ms + 86_400_000,
        order_id="member-index-order",
        knowledge_allowance_granted=2,
    )]
    balance_before = service.state_for_user(user_id=user_id).balance

    first_quote = service.quote_knowledge_index(
        user_id=user_id, document_version_id="version-member-1", token_estimate=1_000,
        idempotency_key="member-index-1",
    )
    first = service.reserve_knowledge_index(user_id=user_id, quote_id=first_quote.quote_id)
    assert first.billing_source == "pass_allowance"
    assert service.state_for_user(user_id=user_id).active_pass["knowledgeAllowanceLocked"] == 1
    service.settle_knowledge_index(quote_id=first_quote.quote_id, reference_id="knowledge-index:version-member-1")
    active = service.state_for_user(user_id=user_id).active_pass
    assert active["knowledgeAllowanceLocked"] == 0
    assert active["knowledgeAllowanceUsed"] == 1
    assert service.state_for_user(user_id=user_id).balance == balance_before

    second_quote = service.quote_knowledge_index(
        user_id=user_id, document_version_id="version-member-2", token_estimate=1_000,
        idempotency_key="member-index-2",
    )
    second = service.reserve_knowledge_index(user_id=user_id, quote_id=second_quote.quote_id)
    assert second.billing_source == "pass_allowance"
    service.release_knowledge_index(quote_id=second_quote.quote_id)
    active = service.state_for_user(user_id=user_id).active_pass
    assert active["knowledgeAllowanceLocked"] == 0
    assert active["knowledgeAllowanceUsed"] == 1


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_postgres_abandoned_usage_reservation_is_released_and_cannot_settle(monkeypatch) -> None:
    current_ms = 2_000_000
    monkeypatch.setattr("app.services.billing_service._now_ms", lambda: current_ms)
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        environment="test",
        billing_usage_reservation_ttl_seconds=60,
    )
    service = BillingService(settings, billing_repository=PostgresBillingRepository(settings))
    user_id = f"billing-stale-usage-{uuid4().hex}"
    reservation = service.reserve_usage(user_id=user_id, usage_id=f"usage-{uuid4().hex}", usage_kind="answer")
    assert reservation.status == "reserved"

    current_ms += 60_001
    service.state_for_user(user_id=user_id)
    late = service.settle_usage(usage_id=reservation.usage_id)

    assert late is not None
    assert late.status == "released"
    assert service.state_for_user(user_id=user_id).balance == 200


@pytest.mark.skipif(not DATABASE_URL, reason="OFFERSTEADY_TEST_DATABASE_URL is not configured")
def test_payment_expiry_callback_audit_and_reconciliation() -> None:
    user_id = f"billing-callback-{uuid4().hex}"
    service = service_for_test()
    service.state_for_user(user_id=user_id)
    order = service.create_checkout_order(
        user_id=user_id, product_id="points-1000", channel="alipay",
        idempotency_key="expiring-order", payment_url="#", expires_at_ms=1,
    )
    expired = service.checkout_order_for_user(user_id=user_id, order_id=order.id)
    assert expired.status == "expired"

    fingerprint = uuid4().hex
    assert service.process_payment_notification(
        event_fingerprint=fingerprint, order_id=order.id, provider_trade_no=f"trade-{uuid4().hex}",
        amount_cents=order.amount_cents, verified=True, paid=True,
    ) == "paid"
    assert service.process_payment_notification(
        event_fingerprint=fingerprint, order_id=order.id, provider_trade_no=f"trade-{uuid4().hex}",
        amount_cents=order.amount_cents, verified=True, paid=True,
    ) == "paid"
    restarted = service_for_test()
    assert restarted.state_for_user(user_id=user_id).balance == 1200
    assert len([item for item in restarted.state_for_user(user_id=user_id).ledger if item.kind == "purchase_credit"]) == 1

    assert service.process_payment_notification(
        event_fingerprint=uuid4().hex, order_id="unknown-order", provider_trade_no="unknown-trade",
        amount_cents=100, verified=True, paid=True,
    ) == "unknown_order"
    mismatch_order = service.create_checkout_order(
        user_id=user_id, product_id="points-3000", channel="alipay",
        idempotency_key="mismatch-order", payment_url="#", expires_at_ms=9999999999999,
    )
    assert service.process_payment_notification(
        event_fingerprint=uuid4().hex, order_id=mismatch_order.id, provider_trade_no=f"mismatch-{uuid4().hex}",
        amount_cents=mismatch_order.amount_cents - 1, verified=True, paid=True,
    ) == "amount_mismatch"
    assert service.process_payment_notification(
        event_fingerprint=uuid4().hex, order_id=order.id, provider_trade_no="invalid-signature",
        amount_cents=order.amount_cents, verified=False, paid=True,
    ) == "invalid_signature"
    report = restarted.reconciliation_summary()
    assert report["callbackEvents"] >= 3
    assert report["openIssues"] >= 1
    assert any(item["issueType"] == "unknown_order" for item in report["issues"])
    assert any(item["issueType"] == "amount_mismatch" for item in report["issues"])
