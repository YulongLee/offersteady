from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.api.admin import reconcile_authoritative_order
from app.core.config import Settings
from app.services.admin_repository import AdminRepository
from app.services.alipay_provider import AlipayOrderQuery


ORDER = {"order_id": "order-synthetic", "provider": "alipay", "status": "payment_pending", "amount_cents": 2990}


class BillingStub:
    def __init__(self) -> None:
        self.calls = 0

    def confirm_checkout_paid(self, **values):
        self.calls += 1
        assert values == {"order_id": "order-synthetic", "amount_cents": 2990, "provider_trade_no": "trade-safe"}
        return SimpleNamespace(status="paid")


def authority(**overrides) -> AlipayOrderQuery:
    values = {
        "order_id": "order-synthetic", "provider_trade_no": "trade-safe", "amount_cents": 2990,
        "provider_status": "TRADE_SUCCESS", "paid": True, "verified": True,
    }
    values.update(overrides)
    return AlipayOrderQuery(**values)


def test_authoritative_reconciliation_requires_every_financial_invariant() -> None:
    billing = BillingStub()
    result = reconcile_authoritative_order(order_id="order-synthetic", order=ORDER, authority=authority(), billing=billing)  # type: ignore[arg-type]
    assert result["status"] == "reconciled"
    assert billing.calls == 1

    for query, message in [
        (authority(verified=False), "payment_provider_response_not_verified"),
        (authority(order_id="other-order"), "payment_provider_order_mismatch"),
        (authority(amount_cents=3000), "payment_provider_amount_mismatch"),
    ]:
        with pytest.raises(PermissionError, match=message):
            reconcile_authoritative_order(order_id="order-synthetic", order=ORDER, authority=query, billing=billing)  # type: ignore[arg-type]
    assert billing.calls == 1


def test_authoritative_unpaid_result_never_grants_entitlement() -> None:
    billing = BillingStub()
    result = reconcile_authoritative_order(
        order_id="order-synthetic", order=ORDER,
        authority=authority(paid=False, provider_status="WAIT_BUYER_PAY"), billing=billing,  # type: ignore[arg-type]
    )
    assert result["status"] == "provider_reports_unpaid"
    assert billing.calls == 0


def test_payment_diagnostics_migration_is_backward_compatible_and_safe() -> None:
    migration = Path("apps/backend/migrations/versions/0020_admin_payment_diagnostics.sql").read_text()
    alipay_migration = Path("apps/backend/migrations/versions/0013_official_alipay_payments.sql").read_text()
    assert migration.count("ADD COLUMN IF NOT EXISTS") == 4
    assert "app_identity_verified BOOLEAN" in migration
    assert "seller_identity_verified BOOLEAN" in migration
    assert "seller_identity_mismatch" in alipay_migration
    assert "app_identity_mismatch" in alipay_migration
    assert "raw_payload" not in migration
    assert "private_key" not in migration.lower()


def test_payment_configuration_health_uses_a_bounded_parameterized_query(monkeypatch) -> None:
    repository = object.__new__(AdminRepository)
    repository.settings = Settings()
    captured = {}

    def one(sql, params):
        captured.update(sql=sql, params=params)
        return {"configured_channels": 2, "ready_channels": 1, "enabled_channels": 1}

    monkeypatch.setattr(repository, "_one", one)
    assert repository.payment_configuration_health() == {
        "configuredChannels": 2, "readyChannels": 1, "enabledChannels": 1,
    }
    assert captured["params"] == ()
    assert "billing_payment_channel_configs" in captured["sql"]
