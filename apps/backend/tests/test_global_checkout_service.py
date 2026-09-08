from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.core.config import Settings
from app.ports.global_commerce import GlobalProductMapping
from app.ports.international_commerce_provider import ProviderCheckout
from app.services.global_checkout_service import GlobalCheckoutNotReady, GlobalCheckoutService, GlobalCheckoutValidationError
from app.services.global_commerce_repository import InMemoryGlobalCommerceRepository
from app.services.global_commerce_service import GlobalCommerceService


class FakeProvider:
    calls = 0

    def __init__(self) -> None:
        self.checkout_result = None
        self.subscription_result = None

    def create_checkout(self, **kwargs):
        self.calls += 1
        return ProviderCheckout(f"checkout_{self.calls}", f"https://checkout.creem.test/checkout_{self.calls}")

    def retrieve_checkout(self, checkout_id: str):
        assert self.checkout_result is not None
        return self.checkout_result

    def retrieve_subscription(self, subscription_id: str):
        assert self.subscription_result is not None
        return self.subscription_result


def setup(enabled: bool = True):
    settings = Settings(product_edition="global", global_commerce_enabled=enabled, global_commerce_provider_mode="test", creem_checkout_success_url="https://offersteady.com/billing/return")
    repository = InMemoryGlobalCommerceRepository()
    repository.save_provider_mapping(GlobalProductMapping("test", "global-pro-weekly", 2, "prod_weekly_test", "ready", 4999, "USD", "one_time"))
    repository.save_provider_mapping(GlobalProductMapping("test", "global-pro-monthly", 2, "prod_monthly_test", "ready", 9999, "USD", "recurring"))
    repository.set_provider_enabled(mode="test", enabled=True, validation_status="ready", validation_errors=[], updated_by_user_id="test-admin", updated_at_ms=1)
    entitlements = GlobalCommerceService(settings, repository)
    provider = FakeProvider()
    return GlobalCheckoutService(settings=settings, repository=repository, provider=provider, entitlements=entitlements), repository, provider


def test_failed_provider_event_can_retry_only_with_identical_payload() -> None:
    repository = InMemoryGlobalCommerceRepository()
    arguments = {"mode": "test", "event_id": "evt_retry", "event_type": "checkout.completed", "payload_sha256": "same-hash", "provider_created_at_ms": 1, "received_at_ms": 2, "order_id": "gorder_1"}
    assert repository.record_provider_event_once(**arguments) is True
    repository.mark_provider_event(mode="test", event_id="evt_retry", status="failed", processed_at_ms=3, error_code="temporary")
    assert repository.record_provider_event_once(**{**arguments, "received_at_ms": 4}) is True
    repository.mark_provider_event(mode="test", event_id="evt_retry", status="failed", processed_at_ms=5, error_code="temporary")
    assert repository.record_provider_event_once(**{**arguments, "payload_sha256": "different-hash", "received_at_ms": 6}) is False


def test_checkout_is_disabled_by_default() -> None:
    service, _, provider = setup(enabled=False)
    with pytest.raises(GlobalCheckoutNotReady, match="disabled"):
        service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="request-123")
    assert provider.calls == 0


def test_checkout_uses_server_catalogue_and_is_idempotent() -> None:
    service, _, provider = setup()
    first = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    second = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=2_000)
    assert first == second
    assert first.expected_amount_cents == 4999
    assert first.checkout_url == "https://checkout.creem.test/checkout_1"
    assert provider.calls == 1


def test_verified_matching_event_fulfills_once_and_redirect_never_grants() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    assert repository.entitlements_for_user("u1") == []
    payload = {"id": "evt_paid_1", "eventType": "checkout.completed", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 4999, "currency": "USD", "order_id": "creem_order_1"}}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    assert service.process_verified_event(payload, raw, now_ms=2_100) == {"accepted": True, "duplicate": False}
    assert service.process_verified_event(payload, raw, now_ms=2_200) == {"accepted": True, "duplicate": True}
    paid = [item for item in repository.entitlements_for_user("u1") if item.source_kind == "order"]
    assert len(paid) == 1
    assert paid[0].copilot_minutes_granted is None


def test_business_fact_mismatch_is_rejected_without_entitlement() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email=None, offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    payload = {"id": "evt_forged", "eventType": "checkout.completed", "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 99, "currency": "USD"}}
    raw = json.dumps(payload).encode()
    with pytest.raises(GlobalCheckoutValidationError, match="amount"):
        service.process_verified_event(payload, raw, now_ms=2_000)
    assert repository.entitlements_for_user("u1") == []


def test_monthly_paid_events_create_distinct_provider_period_entitlements() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="monthly-user", customer_email="user@example.com", offer_code="global-pro-monthly", idempotency_key="monthly-request", now_ms=1_000)
    for index, (start, end) in enumerate(((2_000, 3_000_000), (3_000_000, 6_000_000)), start=1):
        payload = {"id": f"evt_renewal_{index}", "eventType": "subscription.paid", "createdAt": start, "object": {"request_id": order.order_id, "product_id": "prod_monthly_test", "amount": 9999, "currency": "USD", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": start, "currentPeriodEnd": end}}
        service.process_verified_event(payload, json.dumps(payload).encode(), now_ms=start + 1)
    periods = [item for item in repository.entitlements_for_user("monthly-user") if item.source_kind == "subscription_period"]
    assert len(periods) == 2
    assert {item.ends_at_ms for item in periods} == {3_000_000, 6_000_000}
    subscription = repository.subscriptions_for_user("monthly-user")[0]
    assert subscription.status == "active"
    assert subscription.current_period_end_ms == 6_000_000


def test_reordered_subscription_event_does_not_regress_state() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="monthly-user", customer_email=None, offer_code="global-pro-monthly", idempotency_key="monthly-request", now_ms=1_000)
    paid = {"id": "evt_paid", "eventType": "subscription.paid", "createdAt": 3_000, "object": {"request_id": order.order_id, "product_id": "prod_monthly_test", "amount": 9999, "currency": "USD", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": 3_000, "currentPeriodEnd": 6_000_000}}
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=3_001)
    stale = {"id": "evt_stale", "eventType": "subscription.paused", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_monthly_test", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": 2_000, "currentPeriodEnd": 3_000_000}}
    service.process_verified_event(stale, json.dumps(stale).encode(), now_ms=3_002)
    subscription = repository.subscriptions_for_user("monthly-user")[0]
    assert subscription.status == "active"
    assert subscription.current_period_end_ms == 6_000_000


def test_refund_revokes_remaining_order_entitlement_without_negative_usage() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email=None, offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    paid = {"id": "evt_paid", "eventType": "checkout.completed", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 4999, "currency": "USD"}}
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=2_001)
    refund = {"id": "evt_refund", "eventType": "refund.created", "createdAt": 3_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test"}}
    service.process_verified_event(refund, json.dumps(refund).encode(), now_ms=3_001)
    entitlement = next(item for item in repository.entitlements_for_user("u1") if item.source_kind == "order")
    assert entitlement.status == "revoked"
    assert entitlement.copilot_minutes_used == 0
    assert repository.order(order.order_id).status == "refunded"


def test_cancel_keeps_paid_period_but_pause_revokes_it() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="monthly-user", customer_email=None, offer_code="global-pro-monthly", idempotency_key="monthly-request", now_ms=1_000)
    paid = {"id": "evt_paid", "eventType": "subscription.paid", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_monthly_test", "amount": 9999, "currency": "USD", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": 2_000, "currentPeriodEnd": 9_000}}
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=2_001)
    canceled = {"id": "evt_cancel", "eventType": "subscription.canceled", "createdAt": 3_000, "object": {"product_id": "prod_monthly_test", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": 2_000, "currentPeriodEnd": 9_000}}
    service.process_verified_event(canceled, json.dumps(canceled).encode(), now_ms=3_001)
    period = next(item for item in repository.entitlements_for_user("monthly-user") if item.source_kind == "subscription_period")
    assert period.status == "active"
    assert repository.subscriptions_for_user("monthly-user")[0].status == "canceled"
    paused = {"id": "evt_pause", "eventType": "subscription.paused", "createdAt": 4_000, "object": {"product_id": "prod_monthly_test", "subscription_id": "sub_1", "customer_id": "cus_1", "currentPeriodStart": 2_000, "currentPeriodEnd": 9_000}}
    service.process_verified_event(paused, json.dumps(paused).encode(), now_ms=4_001)
    period = next(item for item in repository.entitlements_for_user("monthly-user") if item.source_kind == "subscription_period")
    assert period.status == "revoked"
    assert repository.subscriptions_for_user("monthly-user")[0].status == "paused"


def test_paid_event_requires_provider_financial_facts() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email=None, offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    payload = {"id": "evt_missing_amount", "eventType": "checkout.completed", "object": {"request_id": order.order_id, "product_id": "prod_weekly_test"}}
    with pytest.raises(GlobalCheckoutValidationError, match="missing"):
        service.process_verified_event(payload, json.dumps(payload).encode(), now_ms=2_000)
    assert repository.entitlements_for_user("u1") == []


def test_webhook_business_mutations_roll_back_together(monkeypatch: pytest.MonkeyPatch) -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="atomic-user", customer_email=None, offer_code="global-pro-weekly", idempotency_key="atomic-request", now_ms=1_000)
    original_update = repository.update_order

    def fail_paid_update(updated):
        if updated.status == "paid":
            raise RuntimeError("synthetic write failure")
        return original_update(updated)

    monkeypatch.setattr(repository, "update_order", fail_paid_update)
    payload = {"id": "evt_atomic", "eventType": "checkout.completed", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 4999, "currency": "USD"}}
    with pytest.raises(RuntimeError, match="synthetic"):
        service.process_verified_event(payload, json.dumps(payload).encode(), now_ms=2_001)

    assert repository.entitlements_for_user("atomic-user") == []
    assert repository.order(order.order_id).status == "checkout_created"
    failed_event = repository.recent_provider_events(mode="test", limit=1)[0]
    assert (failed_event["provider_event_id"], failed_event["status"]) == ("evt_atomic", "failed")


@pytest.mark.parametrize("event_type, expected_status", [
    ("subscription.trialing", "trialing"),
    ("subscription.past_due", "past_due"),
    ("subscription.unpaid", "unpaid"),
])
def test_current_creem_non_paid_subscription_states_are_recorded_without_new_grant(event_type: str, expected_status: str) -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="lifecycle-user", customer_email=None, offer_code="global-pro-monthly", idempotency_key="lifecycle-request", now_ms=1_000)
    repository.update_order(replace(order, provider_subscription_id="sub_lifecycle", provider_customer_id="cus_lifecycle"))
    payload = {
        "id": f"evt_{expected_status}",
        "eventType": event_type,
        "created_at": "2026-09-06T10:00:00Z",
        "object": {
            "id": "sub_lifecycle",
            "status": expected_status,
            "mode": "test",
            "product": {"id": "prod_monthly_test"},
            "customer": {"id": "cus_lifecycle"},
            "current_period_start_date": "2026-09-06T10:00:00Z",
            "current_period_end_date": "2026-10-06T10:00:00Z",
        },
    }
    service.process_verified_event(payload, json.dumps(payload).encode(), now_ms=2_000)
    assert repository.subscriptions_for_user("lifecycle-user")[0].status == expected_status
    assert repository.entitlements_for_user("lifecycle-user") == []


def test_recurring_checkout_completion_waits_for_paid_period() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="monthly-user", customer_email=None, offer_code="global-pro-monthly", idempotency_key="monthly-request", now_ms=1_000)
    completed = {"id": "evt_checkout", "eventType": "checkout.completed", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_monthly_test", "amount": 9999, "currency": "USD", "subscription_id": "sub_1", "customer_id": "cus_1"}}
    service.process_verified_event(completed, json.dumps(completed).encode(), now_ms=2_001)
    assert repository.order(order.order_id).status == "confirming"
    assert repository.entitlements_for_user("monthly-user") == []


def test_terminal_order_does_not_regrant_on_reordered_paid_event() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email=None, offer_code="global-pro-weekly", idempotency_key="request-123", now_ms=1_000)
    paid = {"id": "evt_paid", "eventType": "checkout.completed", "createdAt": 2_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 4999, "currency": "USD"}}
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=2_001)
    dispute = {"id": "evt_dispute", "eventType": "dispute.created", "createdAt": 4_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test"}}
    service.process_verified_event(dispute, json.dumps(dispute).encode(), now_ms=4_001)
    stale = {"id": "evt_stale_paid", "eventType": "checkout.completed", "createdAt": 3_000, "object": {"request_id": order.order_id, "product_id": "prod_weekly_test", "amount": 4999, "currency": "USD"}}
    service.process_verified_event(stale, json.dumps(stale).encode(), now_ms=5_000)
    assert repository.order(order.order_id).status == "disputed"
    assert next(item for item in repository.entitlements_for_user("u1") if item.source_kind == "order").status == "revoked"


def test_current_creem_checkout_shape_fulfills_one_time_purchase() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="current-checkout", now_ms=1_000)
    payload = {
        "id": "evt_current_checkout",
        "eventType": "checkout.completed",
        "created_at": "2026-09-06T10:00:00Z",
        "object": {
            "id": "ch_current",
            "request_id": order.order_id,
            "status": "completed",
            "mode": "test",
            "product": {"id": "prod_weekly_test", "price": 4999, "currency": "USD"},
            "order": {"id": "ord_current", "product": "prod_weekly_test", "amount": 4999, "currency": "USD", "status": "paid", "mode": "test"},
            "customer": {"id": "cus_current", "email": "user@example.com"},
        },
    }
    service.process_verified_event(payload, json.dumps(payload).encode(), now_ms=2_000)
    stored = repository.order(order.order_id)
    assert stored is not None
    assert (stored.status, stored.provider_order_id, stored.provider_customer_id) == ("paid", "ord_current", "cus_current")
    assert len([item for item in repository.entitlements_for_user("u1") if item.source_kind == "order"]) == 1


def test_current_creem_subscription_shapes_grant_and_schedule_cancel() -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="monthly-user", customer_email="user@example.com", offer_code="global-pro-monthly", idempotency_key="current-monthly", now_ms=1_000)
    checkout = {
        "id": "evt_current_monthly_checkout",
        "eventType": "checkout.completed",
        "created_at": "2026-09-06T10:00:00Z",
        "object": {
            "request_id": order.order_id,
            "status": "completed",
            "mode": "test",
            "product": {"id": "prod_monthly_test", "price": 9999, "currency": "USD"},
            "order": {"id": "ord_monthly", "amount": 9999, "currency": "USD", "status": "paid", "mode": "test"},
            "customer": {"id": "cus_1"},
            "subscription": {"id": "sub_1"},
        },
    }
    service.process_verified_event(checkout, json.dumps(checkout).encode(), now_ms=2_000)
    paid = {
        "id": "evt_current_monthly_paid",
        "eventType": "subscription.paid",
        "created_at": "2026-09-06T10:00:01Z",
        "object": {
            "id": "sub_1",
            "status": "active",
            "mode": "test",
            "product": {"id": "prod_monthly_test", "price": 9999, "currency": "USD"},
            "customer": {"id": "cus_1"},
            "current_period_start_date": "2026-09-06T10:00:00Z",
            "current_period_end_date": "2026-10-06T10:00:00Z",
            "last_transaction_id": "tran_1",
        },
    }
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=3_000)
    subscription = repository.subscriptions_for_user("monthly-user")[0]
    assert subscription.status == "active"
    assert subscription.current_period_end_ms == 1_791_280_800_000
    scheduled = {
        "id": "evt_current_monthly_cancel",
        "eventType": "subscription.scheduled_cancel",
        "created_at": "2026-09-07T10:00:00Z",
        "object": {**paid["object"], "status": "scheduled_cancel"},
    }
    service.process_verified_event(scheduled, json.dumps(scheduled).encode(), now_ms=4_000)
    assert repository.subscriptions_for_user("monthly-user")[0].status == "canceling"
    entitlement = next(item for item in repository.entitlements_for_user("monthly-user") if item.source_kind == "subscription_period")
    assert entitlement.status == "active"


@pytest.mark.parametrize(("event_type", "terminal_status"), (("refund.created", "refunded"), ("dispute.created", "disputed")))
def test_current_creem_reversal_shapes_find_order_and_revoke(event_type: str, terminal_status: str) -> None:
    service, repository, _ = setup()
    order = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key=f"reverse-{terminal_status}", now_ms=1_000)
    paid = {
        "id": f"evt_paid_{terminal_status}",
        "eventType": "checkout.completed",
        "created_at": 2_000,
        "object": {
            "request_id": order.order_id,
            "mode": "test",
            "product": {"id": "prod_weekly_test", "price": 4999, "currency": "USD"},
            "order": {"id": f"ord_{terminal_status}", "product": "prod_weekly_test", "amount": 4999, "currency": "USD", "status": "paid", "mode": "test"},
            "customer": {"id": "cus_1"},
        },
    }
    service.process_verified_event(paid, json.dumps(paid).encode(), now_ms=2_001)
    reversal = {
        "id": f"evt_{terminal_status}",
        "eventType": event_type,
        "created_at": 3_000,
        "object": {
            "id": f"obj_{terminal_status}",
            "status": "succeeded" if terminal_status == "refunded" else "open",
            "mode": "local",
            "checkout": {"request_id": order.order_id},
            "order": {"id": f"ord_{terminal_status}", "product": "prod_weekly_test", "amount": 4999, "currency": "USD", "status": "paid", "mode": "local"},
            "customer": {"id": "cus_1"},
        },
    }
    service.process_verified_event(reversal, json.dumps(reversal).encode(), now_ms=3_001)
    assert repository.order(order.order_id).status == terminal_status
    entitlement = next(item for item in repository.entitlements_for_user("u1") if item.source_kind == "order")
    assert entitlement.status == "revoked"


def test_single_order_reconciliation_recovers_missed_one_time_webhook() -> None:
    service, repository, provider = setup()
    order = service.create_checkout(user_id="u1", customer_email="user@example.com", offer_code="global-pro-weekly", idempotency_key="missed-webhook", now_ms=1_000)
    provider.checkout_result = {
        "id": order.provider_checkout_id,
        "request_id": order.order_id,
        "status": "completed",
        "mode": "test",
        "product": "prod_weekly_test",
        "order": {"id": "ord_reconciled", "product": "prod_weekly_test", "amount": 4999, "currency": "USD", "status": "paid", "mode": "test"},
        "customer": "cus_reconciled",
        "updated_at": "2026-09-06T12:00:00Z",
    }
    reconciled = service.reconcile_order(order.order_id, now_ms=2_000)
    assert (reconciled.status, reconciled.provider_order_id, reconciled.provider_customer_id) == ("paid", "ord_reconciled", "cus_reconciled")
    assert len([item for item in repository.entitlements_for_user("u1") if item.source_kind == "order"]) == 1
    assert service.reconcile_order(order.order_id, now_ms=3_000).status == "paid"
    assert len([item for item in repository.entitlements_for_user("u1") if item.source_kind == "order"]) == 1
