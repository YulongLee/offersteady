from __future__ import annotations

from base64 import b64encode
from json import dumps
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import Settings
from app.services.alipay_provider import AlipayPaymentProvider
from app.services.billing_service import BillingService


def alipay_fixture() -> tuple[AlipayPaymentProvider, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    settings = Settings(
        alipay_app_id="synthetic-app",
        alipay_app_private_key=private_pem,
        alipay_public_key=public_pem,
        alipay_seller_id="synthetic-seller",
        alipay_notify_url="https://example.test/alipay/notify",
        alipay_return_url="https://example.test/billing",
    )
    return AlipayPaymentProvider(settings), private_key


def signed_notification(provider: AlipayPaymentProvider, private_key: object, **overrides: str) -> dict[str, str]:
    params = {
        "app_id": "synthetic-app",
        "seller_id": "synthetic-seller",
        "out_trade_no": "official-order-synthetic",
        "trade_no": "alipay-trade-synthetic",
        "total_amount": "39.90",
        "trade_status": "TRADE_SUCCESS",
        **overrides,
    }
    signature = private_key.sign(
        provider._canonical(params).encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return {**params, "sign_type": "RSA2", "sign": b64encode(signature).decode()}


def test_alipay_checkout_uses_official_gateway_and_rsa2() -> None:
    provider, _ = alipay_fixture()
    payment_url = provider.payment_url(
        order_id="official-order-synthetic",
        product_name="300积分",
        amount_cents=3990,
        channel="alipay",
    )
    params = {key: values[0] for key, values in parse_qs(urlparse(payment_url).query).items()}
    assert params["method"] == "alipay.trade.page.pay"
    assert params["sign_type"] == "RSA2"
    assert provider.verify(params)


def test_alipay_notification_requires_signature_and_merchant_identity() -> None:
    provider, private_key = alipay_fixture()
    valid = provider.parse_notification(signed_notification(provider, private_key))
    assert valid.verified is True
    assert valid.paid is True
    assert valid.amount_cents == 3990

    wrong_seller = provider.parse_notification(
        signed_notification(provider, private_key, seller_id="another-seller")
    )
    assert wrong_seller.verified is False


def test_payment_callback_cannot_cross_order_provider() -> None:
    service = BillingService()
    order = service.create_checkout_order(
        user_id="synthetic-user",
        product_id="points-300",
        channel="alipay",
        provider="alipay",
        idempotency_key="synthetic-checkout",
        payment_url="#",
        expires_at_ms=9_999_999_999_999,
    )
    outcome = service.process_payment_notification(
        event_fingerprint="synthetic-event",
        order_id=order.id,
        provider_trade_no="synthetic-trade",
        amount_cents=order.amount_cents,
        verified=True,
        paid=True,
        provider="mzfpay",
    )
    assert outcome == "provider_mismatch"
    assert service.checkout_order_for_user(user_id="synthetic-user", order_id=order.id).status == "payment_pending"


def test_alipay_order_query_requires_signed_authoritative_response(monkeypatch) -> None:
    provider, private_key = alipay_fixture()
    payload = {
        "code": "10000",
        "out_trade_no": "official-order-synthetic",
        "trade_no": "alipay-trade-synthetic",
        "total_amount": "39.90",
        "trade_status": "TRADE_SUCCESS",
    }
    signature = private_key.sign(
        dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    class ResponseStub:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "alipay_trade_query_response": payload,
                "sign": b64encode(signature).decode(),
            }

    monkeypatch.setattr("app.services.alipay_provider.httpx.post", lambda *args, **kwargs: ResponseStub())
    result = provider.query_order(order_id="official-order-synthetic")
    assert result.verified is True
    assert result.paid is True
    assert result.amount_cents == 3990

    class UnsignedResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"alipay_trade_query_response": payload, "sign": "invalid"}

    monkeypatch.setattr("app.services.alipay_provider.httpx.post", lambda *args, **kwargs: UnsignedResponse())
    assert provider.query_order(order_id="official-order-synthetic").verified is False
